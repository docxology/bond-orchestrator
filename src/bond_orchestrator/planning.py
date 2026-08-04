"""Parallel-stage planning over the film DAG (pure core).

A *stage* is a set of packages that may run concurrently without violating
dependency order: every package in stage ``k`` has all of its dependencies in
stages ``< k``.  Stage planning is the deterministic wavefront decomposition
of the DAG (classic level-by-level scheduling of directed task graphs
[@kwok1999]).  It does NOT change how the runner executes — execution stays
sequential by design — it is the scheduling artifact that makes a later
parallel executor safe, and it exposes the achievable parallelism and the
critical path length of a mission.
"""

from __future__ import annotations

from dataclasses import dataclass

from .graph import CycleError, FilmGraph, build_film_graph
from .protocol import Mission


@dataclass(frozen=True)
class Stage:
    """One parallel-execution stage: packages with all deps already staged.

    Attributes:
        index: 1-based stage number (stage 1 = dependency-free roots).
        packages: Package ids in this stage, sorted for determinism.
    """

    index: int
    packages: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization of the stage."""
        return {"index": self.index, "packages": list(self.packages)}


@dataclass(frozen=True)
class StagePlan:
    """The full wavefront plan for a mission.

    Attributes:
        mission_name: Name of the planned mission.
        stages: Stages in execution order (1-based indices).
    """

    mission_name: str
    stages: tuple[Stage, ...]

    def max_parallelism(self) -> int:
        """Width of the widest stage — the achievable concurrency."""
        return max((len(stage.packages) for stage in self.stages), default=0)

    def critical_path_length(self) -> int:
        """Number of stages — the length of the longest dependency chain."""
        return len(self.stages)

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization of the plan."""
        return {
            "mission_name": self.mission_name,
            "stages": [stage.as_dict() for stage in self.stages],
            "max_parallelism": self.max_parallelism(),
            "critical_path_length": self.critical_path_length(),
        }

    def render(self) -> str:
        """Human-readable plan (used by the ``plan`` CLI command)."""
        lines = [f"{self.mission_name} stage plan"]
        for stage in self.stages:
            lines.append(f"  stage {stage.index}: {' | '.join(stage.packages)}")
        lines.append(f"max parallelism: {self.max_parallelism()} | critical path: {self.critical_path_length()} stages")
        return "\n".join(lines)


def plan_stages(graph: FilmGraph) -> tuple[Stage, ...]:
    """Deterministic wavefront decomposition of ``graph`` into stages.

    Stage ``k`` contains every not-yet-staged node whose dependencies are all
    already staged; within a stage, package ids are sorted so the plan is
    canonical for a given graph.

    Raises:
        CycleError: The graph contains a dependency cycle (no valid stages).
    """
    remaining = set(graph.nodes)
    stages: list[Stage] = []
    stage_index = 0
    while remaining:
        ready = sorted(node for node in remaining if all(dep not in remaining for dep in graph.dependencies(node)))
        if not ready:
            cycle = graph.find_cycle()
            raise CycleError(
                f"cannot plan stages: dependency cycle detected: {' → '.join(cycle)}",
                cycle=cycle,
            )
        stage_index += 1
        stages.append(Stage(index=stage_index, packages=tuple(ready)))
        remaining.difference_update(ready)
    return tuple(stages)


def build_stage_plan(mission: Mission) -> StagePlan:
    """Build and validate the film DAG for ``mission``, then plan its stages.

    Raises:
        UnknownNodeError / GraphError / CycleError: The mission's dependency
            graph is invalid (see :func:`bond_orchestrator.graph.build_film_graph`).
    """
    graph = build_film_graph(mission.packages)
    return StagePlan(mission_name=mission.name, stages=plan_stages(graph))

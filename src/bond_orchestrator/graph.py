"""Film-package DAG construction and deterministic topological ordering (pure core).

A mission's packages form a directed acyclic graph: a directed edge
``(upstream, downstream)`` exists exactly when ``downstream.depends_on``
contains ``upstream`` — i.e. when one film's recon outputs feed another film's
recon.  Execution order is the deterministic topological order of that graph.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .protocol import MissionPackage


class GraphError(ValueError):
    """Base error for invalid film graphs."""


class CycleError(GraphError):
    """Raised when package dependencies contain a cycle.

    Attributes:
        cycle: The ordered cycle path (e.g. ``("goldfinger", "goldeneye",
            "goldfinger")``) — the package sequence that closes the cycle,
            ending where it began.  Empty when the error was constructed
            without a path (backward-compatible).
    """

    def __init__(self, message: str, cycle: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.cycle = cycle


class UnknownNodeError(GraphError):
    """Raised when a package depends on a package that is not in the mission."""


@dataclass(frozen=True)
class FilmGraph:
    """A validated dependency DAG over package ids.

    Attributes:
        nodes: Package ids in declaration order (deduplicated).
        edges: Deduplicated, sorted ``(upstream, downstream)`` edges.
    """

    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]

    def dependencies(self, node: str) -> tuple[str, ...]:
        """Direct upstream packages whose outputs feed ``node``."""
        return tuple(a for a, b in self.edges if b == node)

    def dependents(self, node: str) -> tuple[str, ...]:
        """Direct downstream packages that consume ``node``'s outputs."""
        return tuple(b for a, b in self.edges if a == node)

    def find_cycle(self) -> tuple[str, ...]:
        """Return one dependency cycle as an ordered path, or ``()``.

        Depth-first search with a gray/black coloring over sorted node ids
        (and sorted adjacency), so the returned path is canonical for a given
        graph.  The path is a closed walk, e.g. ``("a", "b", "c", "a")`` for
        edges a→b→c→a.
        """
        white, gray, black = 0, 1, 2
        color = {node: white for node in self.nodes}
        parent: dict[str, str | None] = {node: None for node in self.nodes}

        def visit(node: str) -> tuple[str, ...] | None:
            color[node] = gray
            for downstream in sorted(self.dependents(node)):
                if color[downstream] == gray:
                    # back edge node -> downstream closes a cycle
                    cycle: list[str] = [downstream]
                    current: str | None = node
                    while current is not None and current != downstream:
                        cycle.append(current)
                        current = parent[current]
                    cycle.append(downstream)
                    return tuple(reversed(cycle))
                if color[downstream] == white:
                    parent[downstream] = node
                    found = visit(downstream)
                    if found is not None:
                        return found
            color[node] = black
            return None

        for node in sorted(self.nodes):
            if color[node] == white:
                found = visit(node)
                if found is not None:
                    return found
        return ()

    def topological_order(self) -> tuple[str, ...]:
        """Deterministic topological order (Kahn's algorithm, id tie-break).

        The worklist is kept sorted by package id so the result is canonical
        for a given set of packages regardless of declaration order.
        """
        indegree = {node: 0 for node in self.nodes}
        adjacency: dict[str, list[str]] = {node: [] for node in self.nodes}
        for upstream, downstream in self.edges:
            indegree[downstream] += 1
            adjacency[upstream].append(downstream)

        ready = sorted(node for node in self.nodes if indegree[node] == 0)
        order: list[str] = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for downstream in sorted(adjacency[node]):
                indegree[downstream] -= 1
                if indegree[downstream] == 0:
                    ready.append(downstream)
                    ready.sort()

        if len(order) != len(self.nodes):
            cycle = self.find_cycle()
            raise CycleError(
                f"dependency cycle detected: {' → '.join(cycle)}",
                cycle=cycle,
            )
        return tuple(order)

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization of the graph."""
        return {
            "nodes": list(self.nodes),
            "edges": [[a, b] for a, b in self.edges],
            "topological_order": list(self.topological_order()),
        }


def build_film_graph(packages: Sequence[MissionPackage]) -> FilmGraph:
    """Build and validate the dependency DAG for ``packages``.

    Raises:
        UnknownNodeError: A package depends on a package outside the mission.
        GraphError: A package depends on itself.
        CycleError: The dependency graph contains a cycle.
    """
    nodes: list[str] = []
    for pkg in packages:
        if pkg.id not in nodes:
            nodes.append(pkg.id)
    node_set = set(nodes)

    edge_set: set[tuple[str, str]] = set()
    for pkg in packages:
        for dep in pkg.depends_on:
            if dep == pkg.id:
                raise GraphError(f"package {pkg.id!r} depends on itself")
            if dep not in node_set:
                raise UnknownNodeError(f"package {pkg.id!r} depends on unknown package {dep!r}")
            edge_set.add((dep, pkg.id))

    graph = FilmGraph(nodes=tuple(nodes), edges=tuple(sorted(edge_set)))
    graph.topological_order()  # validates acyclicity
    return graph

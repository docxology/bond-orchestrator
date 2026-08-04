"""Deterministic mission runner with checkpoint/resume (pure core).

Execution model
---------------
Phase-major, package-minor: for each phase in ``PHASES`` (brief, recon, plan,
execute, debrief) every package runs in deterministic topological order.  The
accumulated :class:`~bond_orchestrator.protocol.MissionContext` is shared
across phases, so a downstream package's ``recon`` can consume its
dependencies' outputs, and ``plan``/``execute``/``debrief`` see the full recon
picture.  Execution is sequential; the DAG order is what makes a later
parallel implementation safe.

Checkpoint / resume
-------------------
When a ``checkpoint_dir`` is given, every completed (phase, package) step is
persisted as ``<checkpoint_dir>/<mission>/<phase>_<package>.json`` and the
completed step ids are tracked in ``manifest.json``.  Re-running the same
mission with the same checkpoint dir skips completed steps and replays their
records (recon reports are restored into the context so downstream steps see
identical inputs), then continues from the last completed step.  A full run
also persists ``report.json``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .graph import build_film_graph
from .protocol import (
    BriefRecord,
    Debrief,
    ExecutionResult,
    Mission,
    MissionContext,
    MissionProvider,
    Plan,
    PlanStep,
    ReconReport,
)

PHASES = ("brief", "recon", "plan", "execute", "debrief")

MANIFEST_FILENAME = "manifest.json"
REPORT_FILENAME = "report.json"


class MissionError(RuntimeError):
    """Base error for mission execution."""


class ProviderNotFoundError(MissionError):
    """Raised when no provider is registered for a package."""


@dataclass(frozen=True)
class MissionReport:
    """Full consolidated result of one mission run.

    All tuples are in topological execution order.  ``consolidated_debrief``
    renders the single debrief text that the spec requires OPERATION OMNIBUS
    to produce.
    """

    mission: Mission
    order: tuple[str, ...]
    briefs: tuple[BriefRecord, ...] = ()
    recon: tuple[ReconReport, ...] = ()
    plans: tuple[Plan, ...] = ()
    executions: tuple[ExecutionResult, ...] = ()
    debriefs: tuple[Debrief, ...] = ()

    def all_verdicts_pass(self) -> bool:
        """True when every package debriefed with verdict ``"pass"``."""
        return all(debrief.verdict == "pass" for debrief in self.debriefs)

    def total_steps(self) -> int:
        """Total executed plan steps across all packages."""
        return len(self.executions)

    def consolidated_debrief(self) -> str:
        """Render the single consolidated debrief for the mission."""
        lines = [
            f"{self.mission.name} — consolidated debrief",
            f"execution order: {' → '.join(self.order)}",
            "",
        ]
        for debrief in self.debriefs:
            lines.append(f"* {debrief.package_id}: {debrief.verdict.upper()} — {debrief.assessment}")
            if debrief.metrics:
                metrics = ", ".join(f"{key}={value:g}" for key, value in sorted(debrief.metrics.items()))
                lines.append(f"  metrics: {metrics}")
        return "\n".join(lines)

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization of the full report."""
        return {
            "mission": self.mission.as_dict(),
            "order": list(self.order),
            "briefs": [b.as_dict() for b in self.briefs],
            "recon": [r.as_dict() for r in self.recon],
            "plans": [p.as_dict() for p in self.plans],
            "executions": [e.as_dict() for e in self.executions],
            "debriefs": [d.as_dict() for d in self.debriefs],
            "consolidated_debrief": self.consolidated_debrief(),
        }


class MissionRunner:
    """Executes a mission across N providers, sequentially and deterministically.

    Args:
        providers: Mapping of package id -> provider implementing
            :class:`~bond_orchestrator.protocol.MissionProvider`.
        checkpoint_dir: Optional state dir for checkpoint/resume.  When set,
            completed steps are persisted and skipped on subsequent runs.
    """

    def __init__(
        self,
        providers: Mapping[str, MissionProvider],
        checkpoint_dir: Path | None = None,
    ) -> None:
        self._providers = dict(providers)
        self._checkpoint_dir = checkpoint_dir

    def run(self, mission: Mission) -> MissionReport:
        """Execute ``mission`` end-to-end and return the consolidated report."""
        graph = build_film_graph(mission.packages)
        order = graph.topological_order()
        state = _RunState(
            mission=mission,
            order=order,
            providers=self._providers,
            checkpoint_dir=self._checkpoint_dir,
        )
        for phase in PHASES:
            for package_id in order:
                state.run_step(phase, package_id)
        return state.report()


class _RunState:
    """Mutable per-run state; encapsulates step execution + checkpointing."""

    def __init__(
        self,
        mission: Mission,
        order: tuple[str, ...],
        providers: Mapping[str, MissionProvider],
        checkpoint_dir: Path | None,
    ) -> None:
        self._mission = mission
        self._order = order
        self._providers = providers
        self._context = MissionContext()
        self._briefs: list[BriefRecord] = []
        self._recon: list[ReconReport] = []
        self._plans: list[Plan] = []
        self._executions: list[ExecutionResult] = []
        self._debriefs: list[Debrief] = []
        self._step_dir: Path | None = Path(checkpoint_dir) / mission.name if checkpoint_dir is not None else None
        self._manifest: set[str] = set()
        if self._step_dir is not None:
            self._step_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = self._step_dir / MANIFEST_FILENAME
            if manifest_path.exists():
                manifest = _read_json(manifest_path)
                self._manifest = set(cast("list[str]", manifest.get("steps", [])))

    def run_step(self, phase: str, package_id: str) -> None:
        """Execute (or replay from checkpoint) one (phase, package) step."""
        step_id = f"{phase}:{package_id}"
        if self._is_completed(step_id):
            self._load_step(phase, package_id)
            return
        provider = self._providers.get(package_id)
        if provider is None:
            raise ProviderNotFoundError(f"no provider registered for package {package_id!r}")
        package = self._mission.package(package_id)
        payload: object
        if phase == "brief":
            payload = BriefRecord(provider.name, package_id, provider.brief(package))
            self._briefs.append(payload)
        elif phase == "recon":
            payload = provider.recon(package, self._context)
            self._context.recon_reports[package_id] = payload
            self._recon.append(payload)
        elif phase == "plan":
            payload = provider.plan(package, self._context)
            self._plans.append(payload)
        elif phase == "execute":
            plan = self._plan_for(package_id)
            results = provider.execute(package, plan, self._context)
            payload = results
            self._executions.extend(results)
        elif phase == "debrief":
            plan = self._plan_for(package_id)
            results = self._results_for(package_id)
            payload = provider.debrief(package, self._context, plan, results)
            self._debriefs.append(payload)
        else:  # pragma: no cover - guarded by PHASES loop; kept for exhaustiveness
            raise MissionError(f"unknown phase {phase!r}")
        self._checkpoint_step(step_id, phase, package_id, payload)

    def report(self) -> MissionReport:
        """Assemble the frozen consolidated report from accumulated state."""
        report = MissionReport(
            mission=self._mission,
            order=self._order,
            briefs=tuple(self._briefs),
            recon=tuple(self._recon),
            plans=tuple(self._plans),
            executions=tuple(self._executions),
            debriefs=tuple(self._debriefs),
        )
        if self._step_dir is not None:
            (self._step_dir / REPORT_FILENAME).write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n")
        return report

    # -- internals ---------------------------------------------------------

    def _is_completed(self, step_id: str) -> bool:
        if self._step_dir is None or step_id not in self._manifest:
            return False
        return (self._step_dir / _step_filename(step_id)).exists()

    def _checkpoint_step(self, step_id: str, phase: str, package_id: str, payload: object) -> None:
        if self._step_dir is None:
            return
        record = {
            "step": step_id,
            "phase": phase,
            "package": package_id,
            "payload": _payload_as_dict(payload),
        }
        (self._step_dir / _step_filename(step_id)).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        self._manifest.add(step_id)
        (self._step_dir / MANIFEST_FILENAME).write_text(
            json.dumps({"mission": self._mission.name, "steps": sorted(self._manifest)}, indent=2) + "\n"
        )

    def _load_step(self, phase: str, package_id: str) -> None:
        if self._step_dir is None:
            return
        record = _read_json(self._step_dir / _step_filename(f"{phase}:{package_id}"))
        payload = record["payload"]
        if phase == "brief":
            self._briefs.append(_brief_from_dict(cast("dict[str, object]", payload)))
        elif phase == "recon":
            report = _recon_from_dict(cast("dict[str, object]", payload))
            self._context.recon_reports[package_id] = report
            self._recon.append(report)
        elif phase == "plan":
            self._plans.append(_plan_from_dict(cast("dict[str, object]", payload)))
        elif phase == "execute":
            items = cast("list[dict[str, object]]", payload)
            self._executions.extend(_execution_from_dict(item) for item in items)
        elif phase == "debrief":
            self._debriefs.append(_debrief_from_dict(cast("dict[str, object]", payload)))

    def _plan_for(self, package_id: str) -> Plan:
        for plan in self._plans:
            if plan.package_id == package_id:
                return plan
        raise MissionError(f"no plan recorded for package {package_id!r}")

    def _results_for(self, package_id: str) -> tuple[ExecutionResult, ...]:
        return tuple(r for r in self._executions if r.package_id == package_id)


def _step_filename(step_id: str) -> str:
    return step_id.replace(":", "_") + ".json"


def _read_json(path: Path) -> dict[str, object]:
    return cast("dict[str, object]", json.loads(path.read_text()))


def _payload_as_dict(payload: object) -> object:
    if isinstance(payload, (BriefRecord, ReconReport, Plan, Debrief)):
        return payload.as_dict()
    if isinstance(payload, tuple):
        return [item.as_dict() for item in payload]
    raise MissionError(f"cannot checkpoint payload of type {type(payload).__name__}")


def _brief_from_dict(data: dict[str, object]) -> BriefRecord:
    return BriefRecord(
        provider=str(data["provider"]),
        package_id=str(data["package_id"]),
        text=str(data["text"]),
    )


def _recon_from_dict(data: dict[str, object]) -> ReconReport:
    outputs_raw = data.get("outputs", {})
    outputs = {str(key): str(value) for key, value in cast("dict[object, object]", outputs_raw).items()}
    return ReconReport(
        provider=str(data["provider"]),
        package_id=str(data["package_id"]),
        findings=tuple(str(item) for item in cast("list[object]", data.get("findings", []))),
        outputs=outputs,
    )


def _plan_from_dict(data: dict[str, object]) -> Plan:
    steps_raw = cast("list[dict[str, object]]", data.get("steps", []))
    steps = tuple(
        PlanStep(
            index=cast(int, item["index"]),
            action=str(item["action"]),
            detail=str(item.get("detail", "")),
        )
        for item in steps_raw
    )
    return Plan(
        provider=str(data["provider"]),
        package_id=str(data["package_id"]),
        steps=steps,
    )


def _execution_from_dict(data: dict[str, object]) -> ExecutionResult:
    return ExecutionResult(
        provider=str(data["provider"]),
        package_id=str(data["package_id"]),
        step_index=cast(int, data["step_index"]),
        action=str(data["action"]),
        outcome=str(data["outcome"]),
        detail=str(data.get("detail", "")),
    )


def _debrief_from_dict(data: dict[str, object]) -> Debrief:
    metrics_raw = cast("dict[object, object]", data.get("metrics", {}))
    metrics = {str(key): cast(float, value) for key, value in metrics_raw.items()}
    return Debrief(
        provider=str(data["provider"]),
        package_id=str(data["package_id"]),
        assessment=str(data["assessment"]),
        verdict=str(data["verdict"]),
        metrics=metrics,
    )

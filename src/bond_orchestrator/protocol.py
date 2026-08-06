"""MissionProvider protocol and the mission data model (pure core).

This module owns the **runner-side** protocol contract.  It is deliberately
distinct from the frozen ``bond_api.MissionProvider`` that the 27 film
packages implement: the runner's calls carry a :class:`MissionPackage` and the
shared :class:`MissionContext` (it must, to drive a DAG), whereas the frozen
protocol's calls carry neither.  Neither contract may move — both are consumed
across package boundaries — so the two are joined by an adapter in
``film_providers.py`` rather than merged.  See ``TODO.md`` integration point 4
for why re-export was considered and rejected.

Determinism contract
--------------------
Every dataclass here is frozen and serializable via :meth:`as_dict` so that
reports, checkpoint step files, and provenance records are byte-stable for
identical inputs.  Providers must not mutate shared state; the runner keeps
execution sequential for reproducibility (parallel execution is deferred to a
later phase; the DAG order is what makes it parallel-safe).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class MissionPackage:
    """A single film package inside a mission.

    Attributes:
        id: Stable package identifier (e.g. ``"goldfinger"``).
        title: Human-readable film title.
        objective: What the package's recon/plan/execute phases accomplish.
        depends_on: Package ids whose recon outputs feed this package's recon.
    """

    id: str
    title: str
    objective: str
    depends_on: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization of the package."""
        return {
            "id": self.id,
            "title": self.title,
            "objective": self.objective,
            "depends_on": list(self.depends_on),
        }


@dataclass(frozen=True)
class Mission:
    """A named mission: an ordered collection of film packages.

    The package ordering in :attr:`packages` is the declaration order; the
    actual execution order is derived from the dependency DAG by
    :func:`bond_orchestrator.graph.build_film_graph` + topological sort.
    """

    name: str
    packages: tuple[MissionPackage, ...]

    def package_ids(self) -> tuple[str, ...]:
        """Package ids in declaration order."""
        return tuple(pkg.id for pkg in self.packages)

    def package(self, package_id: str) -> MissionPackage:
        """Return the package with ``package_id`` (raises ``KeyError``)."""
        for pkg in self.packages:
            if pkg.id == package_id:
                return pkg
        raise KeyError(package_id)

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization of the mission."""
        return {"name": self.name, "packages": [pkg.as_dict() for pkg in self.packages]}


def mission_fingerprint(mission: Mission) -> str:
    """Canonical, deterministic fingerprint of a mission's full definition.

    Hashes the mission name together with every package's id, title, objective
    and ``depends_on`` edges (via :meth:`Mission.as_dict` serialised with sorted
    keys), so two missions that share a name but differ in *any* package or
    dependency edge produce different fingerprints.  This is the same material
    the runner records in ``manifest.json`` to bind a checkpoint directory to
    exactly one mission definition (see ``TODO.md`` C1), and it underlies
    :func:`bond_orchestrator.provenance.derive_run_id` so provenance run ids
    cannot collide across differently-shaped missions.

    Returns:
        A 64-char lowercase sha256 hex digest over the canonical serialisation.
    """
    material = json.dumps(mission.as_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


@dataclass(frozen=True)
class BriefRecord:
    """A single provider's briefing for its package."""

    provider: str
    package_id: str
    text: str

    def as_dict(self) -> dict[str, object]:
        return {"provider": self.provider, "package_id": self.package_id, "text": self.text}


@dataclass(frozen=True)
class ReconReport:
    """Findings + machine-readable outputs produced by a provider's recon.

    ``outputs`` is the hand-off channel of the DAG: a downstream package whose
    ``depends_on`` includes this package reads these outputs via
    :meth:`MissionContext.outputs_for`.
    """

    provider: str
    package_id: str
    findings: tuple[str, ...] = ()
    outputs: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "package_id": self.package_id,
            "findings": list(self.findings),
            "outputs": dict(self.outputs),
        }


@dataclass
class MissionContext:
    """Accumulated recon state visible to providers during a run.

    Populated in topological order: when a package's ``recon`` runs, every
    dependency's recon report is already present.
    """

    recon_reports: dict[str, ReconReport] = field(default_factory=dict)

    def has_recon(self, package_id: str) -> bool:
        """True if ``package_id`` has already completed recon."""
        return package_id in self.recon_reports

    def outputs_for(self, package_id: str) -> dict[str, str]:
        """Outputs of ``package_id``'s recon (empty dict when absent)."""
        report = self.recon_reports.get(package_id)
        if report is None:
            return {}
        return dict(report.outputs)


@dataclass(frozen=True)
class PlanStep:
    """One discrete action in a provider's execution plan."""

    index: int
    action: str
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {"index": self.index, "action": self.action, "detail": self.detail}


@dataclass(frozen=True)
class Plan:
    """A provider's plan for its package: an ordered tuple of steps."""

    provider: str
    package_id: str
    steps: tuple[PlanStep, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "package_id": self.package_id,
            "steps": [step.as_dict() for step in self.steps],
        }


@dataclass(frozen=True)
class ExecutionResult:
    """Outcome of one executed plan step (``outcome``: ``"success"`` | ``"failure"``)."""

    provider: str
    package_id: str
    step_index: int
    action: str
    outcome: str
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "package_id": self.package_id,
            "step_index": self.step_index,
            "action": self.action,
            "outcome": self.outcome,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Debrief:
    """A provider's after-action assessment (``verdict``: ``"pass"`` | ``"fail"`` | ``"conditional"``)."""

    provider: str
    package_id: str
    assessment: str
    verdict: str
    metrics: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "package_id": self.package_id,
            "assessment": self.assessment,
            "verdict": self.verdict,
            "metrics": dict(self.metrics),
        }


@runtime_checkable
class MissionProvider(Protocol):
    """The protocol every film provider must implement.

    Lifecycle per package, driven by the runner in phase-major order:

        1. ``brief``  — state the objective.
        2. ``recon``  — gather intelligence; write outputs for downstream DAG edges.
        3. ``plan``   — derive an ordered execution plan from recon context.
        4. ``execute``— run every plan step; return per-step outcomes.
        5. ``debrief``— assess the run; return verdict + numeric metrics.

    Implementations must be deterministic and side-effect free with respect to
    the provided inputs (the runner guarantees sequential execution and a
    stable topological order, which is what makes parallel execution safe in
    principle).
    """

    name: str

    def brief(self, package: MissionPackage) -> str: ...

    def recon(self, package: MissionPackage, context: MissionContext) -> ReconReport: ...

    def plan(self, package: MissionPackage, context: MissionContext) -> Plan: ...

    def execute(
        self,
        package: MissionPackage,
        plan: Plan,
        context: MissionContext,
    ) -> tuple[ExecutionResult, ...]: ...

    def debrief(
        self,
        package: MissionPackage,
        context: MissionContext,
        plan: Plan,
        results: tuple[ExecutionResult, ...],
    ) -> Debrief: ...

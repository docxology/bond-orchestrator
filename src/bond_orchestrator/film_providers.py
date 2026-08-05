"""Real film binding: adapt frozen ``bond-api`` MissionProviders to the orchestrator contract.

This is the consolidation point between the orchestrator's generic mission
machinery (DAG, checkpoint/resume, provenance) and the REAL film packages,
which implement the FROZEN ``bond_api`` MissionProvider protocol.

Design:

* :class:`FilmProviderAdapter` wraps a ``bond_api`` provider and presents the
  orchestrator-side provider interface (``brief/recon/plan/execute/debrief``
  over a :class:`~bond_orchestrator.protocol.MissionPackage` and
  :class:`~bond_orchestrator.protocol.MissionContext`).  The DAG hand-off
  channel is preserved: a package's ``depends_on`` outputs are rendered into
  the ``ReconRequest.goal`` text the film's recon receives, and the film's
  recon findings become the adapter's recon ``outputs`` for downstream edges.
* ``bond_api`` is imported LAZILY inside the methods so that importing this
  module (or ``bond_orchestrator`` itself) never requires bond-api — the pure
  core remains liftable; bond-api is only needed when real films are bound.
* All state is a per-run cache (brief / plan / outcome) so the phase-major
  runner can drive the adapter across phases while the underlying film
  provider stays deterministic and side-effect free (recompute-on-demand is
  safe because film providers are deterministic).

Nothing in this module imports ``infrastructure.*``; it is standalone-clean.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .protocol import (
    Debrief,
    ExecutionResult,
    MissionContext,
    MissionPackage,
    Plan,
    PlanStep,
    ReconReport,
)

__all__ = [
    "FilmProviderAdapter",
    "FilmProviderError",
    "load_film_providers",
    "load_mission_providers",
]


class FilmProviderError(RuntimeError):
    """Raised when a real film package cannot be bound to the orchestrator."""


class FilmProviderAdapter:
    """Adapt a real ``bond_api`` MissionProvider to the orchestrator contract.

    Args:
        film: The film slug (also used as the orchestrator provider name).
        provider: The discovered ``bond_api`` MissionProvider instance.

    The adapter is deterministic: every method is pure with respect to its
    inputs plus the cached protocol objects, and the underlying film provider
    is required (by the frozen protocol) to be deterministic too.
    """

    def __init__(self, film: str, provider: Any) -> None:
        self.name = film
        self._provider = provider
        self._brief_cache: Any = None
        self._plan_cache: Any = None
        self._outcome_cache: Any = None

    # -- internal helpers -------------------------------------------------

    def _brief(self) -> Any:
        if self._brief_cache is None:
            self._brief_cache = self._provider.brief()
        return self._brief_cache

    def _plan_for(self) -> Any:
        if self._plan_cache is None:
            self._plan_cache = self._provider.plan(self._brief())
        return self._plan_cache

    def _outcome_for(self) -> Any:
        if self._outcome_cache is None:
            self._outcome_cache = self._provider.execute(self._plan_for())
        return self._outcome_cache

    def _citation_text(self, package: MissionPackage, context: MissionContext) -> str:
        parts: list[str] = []
        for dep in package.depends_on:
            outputs = context.outputs_for(dep)
            if outputs:
                rendered = ", ".join(f"{key}={value}" for key, value in sorted(outputs.items()))
                parts.append(f"cites {dep}: {rendered}")
        return "; ".join(parts)

    # -- orchestrator provider interface ----------------------------------

    def brief(self, package: MissionPackage) -> str:
        brief = self._brief()
        objectives = " | ".join(brief.objectives)
        return f"{brief.codename}: {objectives}"

    def recon(self, package: MissionPackage, context: MissionContext) -> ReconReport:
        goal = package.objective
        citations = self._citation_text(package, context)
        if citations:
            goal = f"{goal}. {citations}"

        from bond_api.protocol import ReconRequest  # lazy: bond-api only when binding

        report = self._provider.recon(ReconRequest(goal=goal))
        findings = tuple(
            f"{finding.label}: {finding.detail}" if finding.detail else finding.label for finding in report.findings
        )
        outputs = {finding.label: finding.detail for finding in report.findings if finding.detail}
        return ReconReport(
            provider=self.name,
            package_id=package.id,
            findings=findings,
            outputs=outputs,
        )

    def plan(self, package: MissionPackage, context: MissionContext) -> Plan:
        plan = self._plan_for()
        steps = tuple(
            PlanStep(
                index=index,
                action=step.action,
                detail=str(step.params) if step.params else "",
            )
            for index, step in enumerate(plan.steps, start=1)
        )
        return Plan(provider=self.name, package_id=package.id, steps=steps)

    def execute(
        self,
        package: MissionPackage,
        plan: Plan,
        context: MissionContext,
    ) -> tuple[ExecutionResult, ...]:
        outcome = self._outcome_for()
        step_outcome = "success" if outcome.success else "failure"
        detail = str(outcome.results) if not outcome.success else "ok"
        return tuple(
            ExecutionResult(
                provider=self.name,
                package_id=package.id,
                step_index=step.index,
                action=step.action,
                outcome=step_outcome,
                detail=detail,
            )
            for step in plan.steps
        )

    def debrief(
        self,
        package: MissionPackage,
        context: MissionContext,
        plan: Plan,
        results: tuple[ExecutionResult, ...],
    ) -> Debrief:
        outcome = self._outcome_for()
        debrief = self._provider.debrief(outcome)
        assessment = "; ".join(debrief.lessons) if debrief.lessons else "Run complete."
        verdict = "pass" if outcome.success else "fail"
        metrics = {
            str(key): float(value)
            for key, value in outcome.results.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        return Debrief(
            provider=self.name,
            package_id=package.id,
            assessment=assessment,
            verdict=verdict,
            metrics=metrics,
        )


def load_film_providers(
    slugs: Iterable[str],
    bond_root: Path,
) -> dict[str, FilmProviderAdapter]:
    """Load real film providers from ``<bond_root>/<slug>/src`` as adapters.

    Args:
        slugs: Film slugs to bind (e.g. ``("goldfinger", "goldeneye")``).
        bond_root: The PROJECT BOND workspace root (parent of every film dir).

    Raises:
        FilmProviderError: when a film directory or its ``mission.py`` is
            missing, or the provider cannot be discovered (strict: a real-film
            mission must never silently drop a package).

    Returns:
        slug → :class:`FilmProviderAdapter` mapping.
    """
    from bond_api.discovery import DiscoveryError, load_provider  # lazy

    adapters: dict[str, FilmProviderAdapter] = {}
    for slug in slugs:
        search = bond_root / slug / "src"
        if not (search / slug / "mission.py").is_file():
            raise FilmProviderError(f"film package {slug!r} not built: {search / slug / 'mission.py'} missing")
        try:
            provider = load_provider(slug, search_paths=[str(search)])
        except DiscoveryError as exc:
            raise FilmProviderError(f"cannot discover film {slug!r}: {exc}") from exc
        adapters[slug] = FilmProviderAdapter(slug, provider)
    return adapters


def load_mission_providers(
    mission: Any,
    bond_root: Path,
) -> dict[str, FilmProviderAdapter]:
    """Bind every package of ``mission`` to its real film provider.

    Convenience over :func:`load_film_providers` for the orchestrator CLI: a
    real-film mission binds every declared package id.
    """
    return load_film_providers(mission.package_ids(), bond_root)

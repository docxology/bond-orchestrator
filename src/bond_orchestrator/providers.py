"""Deterministic reference film providers implementing the REAL protocol.

These are real Python classes with fixed, reproducible logic — NOT mocks.  They
stand in for the film packages (goldfinger, goldeneye, no_time_to_die, ...)
until those ship their own providers; see ``TODO.md`` for the integration
points.  Every method is pure with respect to its inputs, which is what makes
mission runs byte-deterministic.
"""

from __future__ import annotations

from .protocol import (
    Debrief,
    ExecutionResult,
    MissionContext,
    MissionPackage,
    Plan,
    PlanStep,
    ReconReport,
)
from .runner import ProviderNotFoundError

# Registry keys are package ids (for the reference missions every package is
# served by a provider of the same name).  When real film packages land, the
# binding moves to an entry-point registry; see TODO.md.


class DeterministicProvider:
    """Base class: fixed brief/findings/outputs/plan/assessment per provider.

    Subclasses declare their deterministic spec as class attributes; the
    lifecycle methods implement the
    :class:`~bond_orchestrator.protocol.MissionProvider` protocol with no
    hidden state, so any run is reproducible.
    """

    name: str = "reference"
    _brief_text: str = ""
    _findings: tuple[str, ...] = ()
    _outputs: dict[str, str] = {}
    _plan_actions: tuple[str, ...] = ()
    _assessment: str = ""
    _verdict: str = "pass"
    _metrics: dict[str, float] = {}
    _consumes: tuple[str, ...] = ()

    def brief(self, package: MissionPackage) -> str:
        return f"{self._brief_text} Objective: {package.objective}."

    def recon(self, package: MissionPackage, context: MissionContext) -> ReconReport:
        citations: list[str] = []
        for dep in self._consumes:
            outs = context.outputs_for(dep)
            rendered = ", ".join(f"{key}={value}" for key, value in sorted(outs.items()))
            citations.append(f"cites {dep}: {rendered}")
        findings = self._findings + tuple(citations)
        return ReconReport(
            provider=self.name,
            package_id=package.id,
            findings=findings,
            outputs=dict(self._outputs),
        )

    def plan(self, package: MissionPackage, context: MissionContext) -> Plan:
        steps = tuple(PlanStep(index=idx, action=action) for idx, action in enumerate(self._plan_actions, start=1))
        return Plan(provider=self.name, package_id=package.id, steps=steps)

    def execute(
        self,
        package: MissionPackage,
        plan: Plan,
        context: MissionContext,
    ) -> tuple[ExecutionResult, ...]:
        return tuple(
            ExecutionResult(
                provider=self.name,
                package_id=package.id,
                step_index=step.index,
                action=step.action,
                outcome="success",
                detail=f"{step.action} complete",
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
        all_success = all(result.outcome == "success" for result in results)
        verdict = self._verdict if all_success else "fail"
        return Debrief(
            provider=self.name,
            package_id=package.id,
            assessment=self._assessment,
            verdict=verdict,
            metrics=dict(self._metrics),
        )


class GoldfingerProvider(DeterministicProvider):
    """GOLDFINGER — recon the gold market (leaf package, OPERATION OMNIBUS)."""

    name = "goldfinger"
    _brief_text = "BRIEF GOLDFINGER: recon the Fort Knox gold market."
    _findings = ("market liquidity: high", "gold reserves audited: 4200 t")
    _outputs = {"market_index": "0.92", "gold_reserves_t": "4200"}
    _plan_actions = ("deploy bullion analysts", "price Fort Knox exposure")
    _assessment = "Market recon complete; gold exposure quantified."
    _metrics = {"market_index": 0.92, "reserves_t": 4200.0}


class GoldeneyeProvider(DeterministicProvider):
    """GOLDENEYE — EMP resilience; consumes GOLDFINGER's recon outputs."""

    name = "goldeneye"
    _brief_text = "BRIEF GOLDENEYE: assess EMP resilience of hardened sites."
    _findings = ("EMP shielding rated: 0.87", "satellite uplink redundancy: 2")
    _outputs = {"emp_shield_rating": "0.87", "uplink_redundancy": "2"}
    _plan_actions = ("map EMP contours", "harden uplink relays")
    _assessment = "EMP resilience mapped; uplink relays hardened."
    _metrics = {"shield_rating": 0.87, "uplink_redundancy": 2.0}
    _consumes = ("goldfinger",)


class NoTimeToDieProvider(DeterministicProvider):
    """NO TIME TO DIE — bioweapon countermeasure; consumes GOLDENEYE's outputs."""

    name = "no_time_to_die"
    _brief_text = "BRIEF NO TIME TO DIE: develop a bioweapon countermeasure."
    _findings = ("candidate antidotes screened: 3", "synthesis pipeline primed")
    _outputs = {"countermeasure_ready": "true", "candidate_antidotes": "3"}
    _plan_actions = ("synthesize antidote candidates", "validate neutralization assay")
    _assessment = "Countermeasure validated; neutralization confirmed."
    _metrics = {"candidate_antidotes": 3.0, "neutralization_rating": 0.99}
    _consumes = ("goldeneye",)


class ThunderballProvider(DeterministicProvider):
    """THUNDERBALL — salvage lost warheads (leaf package, OPERATION DIAMOND)."""

    name = "thunderball"
    _brief_text = "BRIEF THUNDERBALL: locate and salvage lost warheads."
    _findings = ("wreck located at 30.5N 74.2W", "salvage window: 72h")
    _outputs = {"salvage_loot_t": "12", "wreck_position": "30.5N 74.2W"}
    _plan_actions = ("dispatch salvage sub", "secure warhead casings")
    _assessment = "Salvage secured; casings accounted for."
    _metrics = {"salvage_loot_t": 12.0}


class FromRussiaWithLoveProvider(DeterministicProvider):
    """FROM RUSSIA WITH LOVE — map the Orient Express network (leaf, DIAMOND)."""

    name = "from_russia_with_love"
    _brief_text = "BRIEF FROM RUSSIA WITH LOVE: map the Orient Express network."
    _findings = ("train lines identified: 7", "primary hub: Istanbul")
    _outputs = {"train_lines": "7", "primary_hub": "Istanbul"}
    _plan_actions = ("chart corridor timetables", "plant listening posts")
    _assessment = "Corridor charted; listening posts planted."
    _metrics = {"train_lines": 7.0}


class SpectreProvider(DeterministicProvider):
    """SPECTRE — synthesize counterintelligence; joins both DIAMOND leaves."""

    name = "spectre"
    _brief_text = "BRIEF SPECTRE: synthesize counterintelligence from both leads."
    _findings = ("cross-correlation complete", "single coordinated plot confirmed")
    _outputs = {"synthesis_score": "0.81", "plot_codename": "EVEREST"}
    _plan_actions = ("fuse intelligence streams", "assign field tasking")
    _assessment = "Coordinated plot confirmed; tasking assigned."
    _metrics = {"synthesis_score": 0.81}
    _consumes = ("thunderball", "from_russia_with_love")


REFERENCE_PROVIDERS: dict[str, DeterministicProvider] = {
    provider.name: provider
    for provider in (
        GoldfingerProvider(),
        GoldeneyeProvider(),
        NoTimeToDieProvider(),
        ThunderballProvider(),
        FromRussiaWithLoveProvider(),
        SpectreProvider(),
    )
}


def get_provider(provider_id: str) -> DeterministicProvider:
    """Return the reference provider registered under ``provider_id``.

    Raises:
        ProviderNotFoundError: No provider is registered under ``provider_id``.
    """
    provider = REFERENCE_PROVIDERS.get(provider_id)
    if provider is None:
        available = ", ".join(sorted(REFERENCE_PROVIDERS))
        raise ProviderNotFoundError(f"no provider registered under {provider_id!r}; available: {available}")
    return provider

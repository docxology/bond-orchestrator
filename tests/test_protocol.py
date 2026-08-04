"""Tests for the MissionProvider protocol and the deterministic providers."""

from __future__ import annotations

import pytest

from bond_orchestrator.missions import OPERATION_OMNIBUS
from bond_orchestrator.protocol import (
    MissionContext,
    MissionPackage,
    MissionProvider,
)
from bond_orchestrator.providers import (
    REFERENCE_PROVIDERS,
    DeterministicProvider,
    GoldeneyeProvider,
    GoldfingerProvider,
    NoTimeToDieProvider,
    SpectreProvider,
    get_provider,
)
from bond_orchestrator.runner import ProviderNotFoundError


class TestProtocolConformance:
    """Reference providers implement the REAL protocol (isinstance + lifecycle)."""

    def test_providers_are_protocol_instances(self) -> None:
        for provider in REFERENCE_PROVIDERS.values():
            assert isinstance(provider, MissionProvider)
            assert isinstance(provider, DeterministicProvider)

    def test_brief_shape(self) -> None:
        package = OPERATION_OMNIBUS.package("goldfinger")
        text = GoldfingerProvider().brief(package)
        assert "gold market" in text
        assert package.objective in text

    def test_recon_outputs_are_stable(self) -> None:
        provider = GoldfingerProvider()
        package = OPERATION_OMNIBUS.package("goldfinger")
        report = provider.recon(package, MissionContext())
        assert report.package_id == "goldfinger"
        assert report.outputs["market_index"] == "0.92"
        assert "gold reserves audited: 4200 t" in report.findings

    def test_recon_consumes_dependency_outputs(self) -> None:
        """goldeneye recon cites goldfinger's recon outputs (DAG edge feed)."""
        context = MissionContext()
        goldfinger = OPERATION_OMNIBUS.package("goldfinger")
        context.recon_reports["goldfinger"] = GoldfingerProvider().recon(goldfinger, context)
        goldeneye_report = GoldeneyeProvider().recon(OPERATION_OMNIBUS.package("goldeneye"), context)
        assert any("cites goldfinger" in finding for finding in goldeneye_report.findings)
        assert any("market_index=0.92" in finding for finding in goldeneye_report.findings)

    def test_plan_steps_numbered_from_one(self) -> None:
        plan = GoldeneyeProvider().plan(OPERATION_OMNIBUS.package("goldeneye"), MissionContext())
        assert [step.index for step in plan.steps] == [1, 2]

    def test_execute_and_debrief_roundtrip(self) -> None:
        provider = NoTimeToDieProvider()
        package = OPERATION_OMNIBUS.package("no_time_to_die")
        context = MissionContext()
        plan = provider.plan(package, context)
        results = provider.execute(package, plan, context)
        assert all(result.outcome == "success" for result in results)
        debrief = provider.debrief(package, context, plan, results)
        assert debrief.verdict == "pass"
        assert debrief.metrics["candidate_antidotes"] == 3.0

    def test_join_provider_cites_both_leaves(self) -> None:
        context = MissionContext()
        for package_id in ("thunderball", "from_russia_with_love"):
            context.recon_reports[package_id] = REFERENCE_PROVIDERS[package_id].recon(
                MissionPackage(id=package_id, title=package_id, objective="x"),
                context,
            )
        report = SpectreProvider().recon(
            MissionPackage(id="spectre", title="SPECTRE", objective="y"),
            context,
        )
        assert any("cites thunderball" in f for f in report.findings)
        assert any("cites from_russia_with_love" in f for f in report.findings)

    def test_missing_dependency_outputs_yield_empty_citation(self) -> None:
        report = GoldeneyeProvider().recon(OPERATION_OMNIBUS.package("goldeneye"), MissionContext())
        assert any("cites goldfinger: " in f for f in report.findings)


class TestDeterminism:
    """Two identical runs produce byte-identical records."""

    def test_recon_repeatable(self) -> None:
        package = OPERATION_OMNIBUS.package("goldfinger")
        provider = GoldfingerProvider()
        first = provider.recon(package, MissionContext()).as_dict()
        second = provider.recon(package, MissionContext()).as_dict()
        assert first == second

    def test_plan_repeatable(self) -> None:
        provider = GoldeneyeProvider()
        package = OPERATION_OMNIBUS.package("goldeneye")
        assert provider.plan(package, MissionContext()).as_dict() == provider.plan(package, MissionContext()).as_dict()


class TestProviderRegistry:
    def test_get_provider_found(self) -> None:
        assert get_provider("goldfinger").name == "goldfinger"

    def test_get_provider_missing(self) -> None:
        with pytest.raises(ProviderNotFoundError, match="does_not_exist"):
            get_provider("does_not_exist")

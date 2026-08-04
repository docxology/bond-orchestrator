"""Integration test: real providers over the REAL protocol, end-to-end.

Exercises 2-3 real film providers (deterministic fake providers that implement
the actual :class:`~bond_orchestrator.protocol.MissionProvider` protocol — NOT
mocks), asserting the DAG executes in order and that checkpoint/resume resumes
from the last completed step.
"""

from __future__ import annotations

import json

from bond_orchestrator.missions import OPERATION_DIAMOND, OPERATION_OMNIBUS
from bond_orchestrator.providers import (
    REFERENCE_PROVIDERS,
    GoldeneyeProvider,
    GoldfingerProvider,
    NoTimeToDieProvider,
)
from bond_orchestrator.runner import MissionRunner


class TestOperationOmnibusEndToEnd:
    """OPERATION OMNIBUS across goldfinger + goldeneye + no_time_to_die."""

    def test_dag_executes_in_dependency_order(self) -> None:
        report = MissionRunner(REFERENCE_PROVIDERS).run(OPERATION_OMNIBUS)
        assert report.order == ("goldfinger", "goldeneye", "no_time_to_die")
        # dependency edge semantics: goldeneye's recon consumed goldfinger outputs
        goldeneye_recon = next(r for r in report.recon if r.package_id == "goldeneye")
        assert any("market_index=0.92" in f for f in goldeneye_recon.findings)
        # and no_time_to_die consumed goldeneye's outputs
        nttd_recon = next(r for r in report.recon if r.package_id == "no_time_to_die")
        assert any("emp_shield_rating=0.87" in f for f in nttd_recon.findings)

    def test_single_consolidated_debrief(self) -> None:
        report = MissionRunner(REFERENCE_PROVIDERS).run(OPERATION_OMNIBUS)
        text = report.consolidated_debrief()
        assert text.count("* ") == 3
        assert report.all_verdicts_pass()

    def test_deterministic_across_fresh_runs(self) -> None:
        first = MissionRunner(REFERENCE_PROVIDERS).run(OPERATION_OMNIBUS).as_dict()
        second = MissionRunner(REFERENCE_PROVIDERS).run(OPERATION_OMNIBUS).as_dict()
        assert first == second

    def test_checkpoint_resume_produces_identical_report(self, tmp_path) -> None:
        checkpoint_dir = tmp_path / "state"
        runner = MissionRunner(REFERENCE_PROVIDERS, checkpoint_dir=checkpoint_dir)
        first = runner.run(OPERATION_OMNIBUS)
        resumed = runner.run(OPERATION_OMNIBUS)
        assert resumed.as_dict() == first.as_dict()
        # persisted report matches the in-memory report
        persisted = json.loads((checkpoint_dir / "OPERATION_OMNIBUS" / "report.json").read_text())
        assert persisted == first.as_dict()


class TestOperationDiamondEndToEnd:
    """Parallel-safe shape: two independent leaves feed one join."""

    def test_leaves_precede_join(self) -> None:
        report = MissionRunner(REFERENCE_PROVIDERS).run(OPERATION_DIAMOND)
        assert report.order == (
            "from_russia_with_love",
            "thunderball",
            "spectre",
        )
        spectre_recon = next(r for r in report.recon if r.package_id == "spectre")
        assert any("cites thunderball" in f for f in spectre_recon.findings)
        assert any("cites from_russia_with_love" in f for f in spectre_recon.findings)
        assert report.all_verdicts_pass()


class TestProviderProtocolContract:
    """The fake providers really implement the protocol (structural check)."""

    def test_providers_are_protocol_instances(self) -> None:
        from bond_orchestrator.protocol import MissionProvider

        for provider in (GoldfingerProvider(), GoldeneyeProvider(), NoTimeToDieProvider()):
            assert isinstance(provider, MissionProvider)

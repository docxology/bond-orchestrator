"""Tests for the deterministic mission runner: order, phases, checkpoint/resume."""

from __future__ import annotations

import pytest

from bond_orchestrator.missions import OPERATION_OMNIBUS
from bond_orchestrator.protocol import MissionProvider
from bond_orchestrator.providers import (
    DeterministicProvider,
    GoldfingerProvider,
    NoTimeToDieProvider,
)
from bond_orchestrator.runner import (
    PHASES,
    MissionError,
    MissionRunner,
    ProviderNotFoundError,
    _RunState,
)


class TestPhaseMajorExecution:
    def test_omnibus_runs_all_phases_in_topo_order(self, omnibus_runner) -> None:
        report = omnibus_runner.run(OPERATION_OMNIBUS)
        expected = ("goldfinger", "goldeneye", "no_time_to_die")
        assert report.order == expected
        assert [b.package_id for b in report.briefs] == list(expected)
        assert [r.package_id for r in report.recon] == list(expected)
        assert [p.package_id for p in report.plans] == list(expected)
        assert [d.package_id for d in report.debriefs] == list(expected)

    def test_phase_major_grouping(self, omnibus_runner) -> None:
        """All briefs happen before any recon (phase-major, package-minor)."""
        report = omnibus_runner.run(OPERATION_OMNIBUS)
        assert len(report.briefs) == 3
        assert len(report.recon) == 3
        assert len(report.plans) == 3
        assert len(report.executions) == 6  # 2 plan steps per package
        assert len(report.debriefs) == 3
        assert report.total_steps() == 6

    def test_recon_context_feeds_downstream(self, omnibus_runner) -> None:
        report = omnibus_runner.run(OPERATION_OMNIBUS)
        goldeneye = next(r for r in report.recon if r.package_id == "goldeneye")
        assert any("cites goldfinger" in f for f in goldeneye.findings)
        nttd = next(r for r in report.recon if r.package_id == "no_time_to_die")
        assert any("cites goldeneye" in f for f in nttd.findings)

    def test_consolidated_debrief_mentions_every_package(self, omnibus_runner) -> None:
        report = omnibus_runner.run(OPERATION_OMNIBUS)
        text = report.consolidated_debrief()
        assert "OPERATION_OMNIBUS — consolidated debrief" in text
        assert "execution order: goldfinger → goldeneye → no_time_to_die" in text
        for package_id in ("goldfinger", "goldeneye", "no_time_to_die"):
            assert f"* {package_id}: PASS" in text
        assert report.all_verdicts_pass()

    def test_report_serialization_roundtrip(self, omnibus_runner) -> None:
        report = omnibus_runner.run(OPERATION_OMNIBUS)
        as_dict = report.as_dict()
        assert as_dict["mission"]["name"] == "OPERATION_OMNIBUS"
        assert len(as_dict["executions"]) == 6
        assert as_dict["consolidated_debrief"] == report.consolidated_debrief()


class TestRunnerErrors:
    def test_missing_provider_raises(self) -> None:
        runner = MissionRunner({"goldfinger": GoldfingerProvider()})
        with pytest.raises(ProviderNotFoundError, match="goldeneye"):
            runner.run(OPERATION_OMNIBUS)

    def test_run_state_plan_missing_raises(self, omnibus_runner) -> None:
        state = _RunState(
            mission=OPERATION_OMNIBUS,
            order=OPERATION_OMNIBUS.package_ids(),
            providers=dict(omnibus_runner._providers),
            checkpoint_dir=None,
        )
        with pytest.raises(MissionError, match="no plan recorded"):
            state._plan_for("goldfinger")

    def test_run_state_results_empty(self, omnibus_runner) -> None:
        state = _RunState(
            mission=OPERATION_OMNIBUS,
            order=OPERATION_OMNIBUS.package_ids(),
            providers=dict(omnibus_runner._providers),
            checkpoint_dir=None,
        )
        assert state._results_for("goldfinger") == ()

    def test_phases_are_stable(self) -> None:
        assert PHASES == ("brief", "recon", "plan", "execute", "debrief")

    def test_uncheckpointable_payload_is_rejected_loudly(self) -> None:
        """The checkpoint serializer must fail, never write a lossy record.

        Silently dropping an unknown payload would make a resumed run diverge
        from a fresh one while every gate stayed green, so the writer raises.
        """
        from bond_orchestrator.runner import _payload_as_dict

        with pytest.raises(MissionError, match="cannot checkpoint payload of type str"):
            _payload_as_dict("not a protocol record")

    def test_load_step_without_checkpoint_dir_is_a_no_op(self, omnibus_runner) -> None:
        """Replay is inert when no state dir is configured (no stray file reads)."""
        state = _RunState(
            mission=OPERATION_OMNIBUS,
            order=OPERATION_OMNIBUS.package_ids(),
            providers=dict(omnibus_runner._providers),
            checkpoint_dir=None,
        )
        state._load_step("brief", "goldfinger")
        assert state.report().briefs == ()


class TestCheckpointResume:
    def test_resume_replays_without_reexecuting(self, tmp_path) -> None:
        """A fully-checkpointed run resumes by replay; tripwire providers prove it."""
        checkpoint_dir = tmp_path / "state"
        first = MissionRunner(dict_of_reference_providers(), checkpoint_dir=checkpoint_dir).run(OPERATION_OMNIBUS)
        tripwire = {pid: TripwireProvider() for pid in OPERATION_OMNIBUS.package_ids()}
        resumed = MissionRunner(tripwire, checkpoint_dir=checkpoint_dir).run(OPERATION_OMNIBUS)
        assert resumed.as_dict() == first.as_dict()

    def test_resume_continues_after_interruption(self, tmp_path) -> None:
        """A crash before the final debrief resumes from the last completed step."""
        checkpoint_dir = tmp_path / "state"
        providers = dict_of_reference_providers()
        providers["no_time_to_die"] = InterruptedNoTimeToDieProvider()
        with pytest.raises(RuntimeError, match="simulated interruption"):
            MissionRunner(providers, checkpoint_dir=checkpoint_dir).run(OPERATION_OMNIBUS)

        recording = {pid: RecordingProvider() for pid in OPERATION_OMNIBUS.package_ids()}
        resumed = MissionRunner(recording, checkpoint_dir=checkpoint_dir).run(OPERATION_OMNIBUS)
        assert resumed.all_verdicts_pass()
        assert recording["goldfinger"].calls == []
        assert recording["goldeneye"].calls == []
        assert recording["no_time_to_die"].calls == ["debrief:no_time_to_die"]

    def test_resumed_report_matches_fresh_run(self, tmp_path) -> None:
        checkpoint_dir = tmp_path / "state"
        MissionRunner(dict_of_reference_providers(), checkpoint_dir=checkpoint_dir).run(OPERATION_OMNIBUS)
        resumed = MissionRunner(dict_of_reference_providers(), checkpoint_dir=checkpoint_dir).run(OPERATION_OMNIBUS)
        fresh = MissionRunner(dict_of_reference_providers()).run(OPERATION_OMNIBUS)
        assert resumed.as_dict() == fresh.as_dict()

    def test_checkpoint_files_are_written(self, tmp_path) -> None:
        checkpoint_dir = tmp_path / "state"
        MissionRunner(dict_of_reference_providers(), checkpoint_dir=checkpoint_dir).run(OPERATION_OMNIBUS)
        state_dir = checkpoint_dir / "OPERATION_OMNIBUS"
        assert (state_dir / "manifest.json").exists()
        assert (state_dir / "report.json").exists()
        assert (state_dir / "recon_goldfinger.json").exists()
        assert (state_dir / "execute_no_time_to_die.json").exists()
        manifest = (state_dir / "manifest.json").read_text()
        assert "debrief:no_time_to_die" in manifest


class TripwireProvider(DeterministicProvider):
    """A real provider that raises if any lifecycle method is invoked.

    Used to prove that a resumed run never re-executes completed steps.
    """

    name = "tripwire"

    def brief(self, package) -> str:
        raise AssertionError(f"brief called during resume for {package.id}")

    def recon(self, package, context):
        raise AssertionError(f"recon called during resume for {package.id}")

    def plan(self, package, context):
        raise AssertionError(f"plan called during resume for {package.id}")

    def execute(self, package, plan, context):
        raise AssertionError(f"execute called during resume for {package.id}")

    def debrief(self, package, context, plan, results):
        raise AssertionError(f"debrief called during resume for {package.id}")


class InterruptedNoTimeToDieProvider(NoTimeToDieProvider):
    """Like NO TIME TO DIE, but crashes on debrief (simulated mid-mission fault)."""

    def debrief(self, package, context, plan, results):
        raise RuntimeError("simulated interruption before debrief")


class RecordingProvider(DeterministicProvider):
    """A real provider that records which (phase, package) steps it executes."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    def _record(self, phase: str, package_id: str) -> None:
        self.calls.append(f"{phase}:{package_id}")

    def brief(self, package) -> str:
        self._record("brief", package.id)
        return super().brief(package)

    def recon(self, package, context):
        self._record("recon", package.id)
        return super().recon(package, context)

    def plan(self, package, context):
        self._record("plan", package.id)
        return super().plan(package, context)

    def execute(self, package, plan, context):
        self._record("execute", package.id)
        return super().execute(package, plan, context)

    def debrief(self, package, context, plan, results):
        self._record("debrief", package.id)
        return super().debrief(package, context, plan, results)


def dict_of_reference_providers() -> dict[str, MissionProvider]:
    """Fresh reference provider instances keyed by package id."""
    from bond_orchestrator.providers import REFERENCE_PROVIDERS

    return {pid: type(provider)() for pid, provider in REFERENCE_PROVIDERS.items()}

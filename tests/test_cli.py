"""Tests for the thin CLI: list/run, output artifacts, exit codes."""

from __future__ import annotations

import csv
import json

import pytest

from bond_orchestrator import cli
from bond_orchestrator.missions import OPERATION_OMNIBUS
from bond_orchestrator.protocol import Mission, MissionPackage, MissionProvider
from bond_orchestrator.providers import DeterministicProvider
from bond_orchestrator.runner import MissionRunner


class TestListCommand:
    def test_list_lists_all_missions(self, capsys) -> None:
        assert cli.main(["list"]) == 0
        out = capsys.readouterr().out
        assert "OPERATION_OMNIBUS" in out
        assert "OPERATION_DIAMOND" in out
        assert "OPERATION_SINGLET" in out
        assert "goldfinger → goldeneye → no_time_to_die" in out


class TestRunCommand:
    def test_run_omnibus_writes_artifacts(self, tmp_path, capsys) -> None:
        output_dir = tmp_path / "output"
        assert cli.main(["run", "OPERATION_OMNIBUS", "--output-dir", str(output_dir)]) == 0
        out = capsys.readouterr().out
        assert "OPERATION_OMNIBUS — consolidated debrief" in out
        assert "* no_time_to_die: PASS" in out

        report = json.loads((output_dir / "mission_report.json").read_text())
        assert report["order"] == ["goldfinger", "goldeneye", "no_time_to_die"]
        assert len(report["executions"]) == 6

        outcomes = json.loads((output_dir / "provenance" / "outcomes.json").read_text())
        assert len(outcomes) == 6 + 3  # executions + debriefs
        csv_path = output_dir / "provenance" / "provenance.csv"
        with csv_path.open() as handle:
            rows = list(csv.reader(handle))
        assert rows[0][0] == "run_id"
        assert len(rows) == 1 + 9

    def test_run_with_checkpoint_dir(self, tmp_path) -> None:
        state_dir = tmp_path / "state"
        assert (
            cli.main(
                [
                    "run",
                    "OPERATION_OMNIBUS",
                    "--checkpoint-dir",
                    str(state_dir),
                    "--output-dir",
                    str(tmp_path / "out"),
                ]
            )
            == 0
        )
        manifest = (state_dir / "OPERATION_OMNIBUS" / "manifest.json").read_text()
        assert "debrief:no_time_to_die" in manifest

    def test_run_unknown_mission_exits_two(self, capsys) -> None:
        with pytest.raises(SystemExit) as excinfo:
            cli.main(["run", "OPERATION_GHOST"])
        assert excinfo.value.code == 2
        assert "OPERATION_GHOST" in capsys.readouterr().err


class TestExitCodeHelper:
    def test_exit_code_zero_when_all_pass(self) -> None:
        report = MissionRunner(_reference_providers()).run(OPERATION_OMNIBUS)
        assert cli.exit_code_for(report) == 0

    def test_exit_code_one_when_any_fails(self) -> None:
        class FailingProvider(DeterministicProvider):
            """Real provider with a failing verdict (degraded outcome)."""

            name = "goldfinger"
            _brief_text = "BRIEF PROBE"
            _findings = ("probe degraded",)
            _outputs = {"probe": "0"}
            _plan_actions = ("probe",)
            _assessment = "Probe degraded; verdict fail."
            _verdict = "fail"
            _metrics = {"probe_score": 0.0}

        mission = Mission(
            name="OPERATION_PROBE",
            packages=(MissionPackage(id="goldfinger", title="GOLDFINGER", objective="probe"),),
        )
        report = MissionRunner({"goldfinger": FailingProvider()}).run(mission)
        assert not report.all_verdicts_pass()
        assert cli.exit_code_for(report) == 1


def _reference_providers() -> dict[str, MissionProvider]:
    from bond_orchestrator.providers import REFERENCE_PROVIDERS

    return dict(REFERENCE_PROVIDERS)

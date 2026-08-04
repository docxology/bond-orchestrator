"""Subprocess smoke tests for the thin scripts (real execution, no mocks)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_script(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/run_mission.py", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )


class TestRunMissionScript:
    def test_list_command(self, project_root: Path) -> None:
        result = _run_script(project_root, "list")
        assert result.returncode == 0
        assert "OPERATION_OMNIBUS" in result.stdout
        assert "goldfinger → goldeneye → no_time_to_die" in result.stdout

    def test_run_defaults_to_run_subcommand(self, project_root: Path, tmp_path: Path) -> None:
        output_dir = tmp_path / "out"
        result = _run_script(project_root, "OPERATION_SINGLET", "--output-dir", str(output_dir))
        assert result.returncode == 0
        assert "OPERATION_SINGLET — consolidated debrief" in result.stdout
        report = json.loads((output_dir / "mission_report.json").read_text())
        assert report["order"] == ["goldfinger"]
        assert (output_dir / "provenance" / "provenance.csv").exists()

    def test_run_unknown_mission_fails(self, project_root: Path) -> None:
        result = _run_script(project_root, "OPERATION_GHOST")
        assert result.returncode == 2
        assert "OPERATION_GHOST" in result.stderr

    def test_plan_command(self, project_root: Path) -> None:
        result = _run_script(project_root, "plan", "OPERATION_OMNIBUS")
        assert result.returncode == 0
        assert "OPERATION_OMNIBUS stage plan" in result.stdout
        assert "stage 3: no_time_to_die" in result.stdout
        assert "max parallelism: 1 | critical path: 3 stages" in result.stdout


class TestGenerateManuscriptVariablesScript:
    def test_draft_mode_writes_token_map(self, project_root: Path) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/generate_manuscript_variables.py", "--allow-draft"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        variables = json.loads((project_root / "output" / "data" / "manuscript_variables.json").read_text())
        assert variables["CONFIG_CODENAME"] == "DAG 00"
        # config-derived tokens are always resolved; result tokens resolve when
        # output/data/mission_report.json exists and fall back to N/A otherwise
        assert "RESULT_EXECUTION_ORDER" in variables

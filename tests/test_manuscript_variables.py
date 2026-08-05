"""Tests for manuscript {{TOKEN}} hydration from config.yaml + mission report."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from bond_orchestrator.manuscript_variables import generate_variables

MINIMAL_CONFIG = """\
identity:
  name: "BOND-ORCHESTRATOR"
  codename: "DAG 00"
paper:
  title: "BOND-ORCHESTRATOR: A Deterministic Mission DAG Runner"
  subtitle: "Test subtitle"
  version: "2.5.2"
authors:
  - name: "Daniel Ari Friedman"
    orcid: "0000-0001-6232-9096"
mission:
  name: "OPERATION_OMNIBUS"
  packages: [goldfinger, goldeneye, no_time_to_die]
  phases: [brief, recon, plan, execute, debrief]
  retry:
    max_attempts: 1
"""

TOKEN_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _make_project(tmp_path: Path) -> Path:
    """A fake project root with a minimal manuscript/config.yaml."""
    project = tmp_path / "project"
    (project / "manuscript").mkdir(parents=True)
    (project / "manuscript" / "config.yaml").write_text(MINIMAL_CONFIG)
    return project


class TestDraftFallbacks:
    def test_config_tokens_resolved_without_report(self, tmp_path) -> None:
        project = _make_project(tmp_path)
        variables = generate_variables(project, require_outputs=False)
        assert variables["CONFIG_TITLE"].startswith("BOND-ORCHESTRATOR")
        assert variables["CONFIG_CODENAME"] == "DAG 00"
        assert variables["CONFIG_IDENTITY"] == "BOND-ORCHESTRATOR"
        assert variables["CONFIG_MISSION_NAME"] == "OPERATION_OMNIBUS"
        assert variables["CONFIG_NUM_PACKAGES"] == "3"
        assert variables["CONFIG_PACKAGE_CHAIN"] == "goldfinger → goldeneye → no_time_to_die"
        assert "brief" in variables["CONFIG_PHASES"]
        assert variables["RESULT_EXECUTION_ORDER"] == "N/A"

    def test_strict_mode_requires_report(self, tmp_path) -> None:
        project = _make_project(tmp_path)
        with pytest.raises(FileNotFoundError, match="mission_report.json"):
            generate_variables(project, require_outputs=True)


class TestWithReport:
    def _project_with_report(self, tmp_path: Path) -> Path:
        project = _make_project(tmp_path)
        report_dir = project / "output" / "data"
        report_dir.mkdir(parents=True)
        (report_dir / "mission_report.json").write_text(
            json.dumps(
                {
                    "order": ["goldfinger", "goldeneye", "no_time_to_die"],
                    "executions": [{"action": "a"}] * 6,
                    "debriefs": [
                        {"verdict": "pass"},
                        {"verdict": "pass"},
                        {"verdict": "pass"},
                    ],
                }
            )
        )
        return project

    def test_result_tokens_resolved(self, tmp_path) -> None:
        variables = generate_variables(self._project_with_report(tmp_path))
        assert variables["RESULT_EXECUTION_ORDER"] == ("goldfinger → goldeneye → no_time_to_die")
        assert variables["RESULT_NUM_STEPS"] == "6"
        assert variables["RESULT_ALL_VERDICTS_PASS"] == "PASS"

    def test_stage_and_retry_tokens_resolved(self, tmp_path) -> None:
        project = _make_project(tmp_path)
        report_dir = project / "output" / "data"
        report_dir.mkdir(parents=True)
        (report_dir / "mission_report.json").write_text(
            json.dumps(
                {
                    "order": ["goldfinger", "goldeneye", "no_time_to_die"],
                    "executions": [{"action": "a"}] * 6,
                    "debriefs": [{"verdict": "pass"}] * 3,
                    "retries": [{"package_id": "goldfinger", "phase": "execute", "attempts": 3}],
                    "stage_plan": {
                        "mission_name": "OPERATION_OMNIBUS",
                        "stages": [
                            {"index": 1, "packages": ["goldfinger"]},
                            {"index": 2, "packages": ["goldeneye"]},
                            {"index": 3, "packages": ["no_time_to_die"]},
                        ],
                        "max_parallelism": 1,
                        "critical_path_length": 3,
                    },
                }
            )
        )
        variables = generate_variables(project)
        assert variables["RESULT_NUM_STAGES"] == "3"
        assert variables["RESULT_MAX_PARALLELISM"] == "1"
        assert variables["RESULT_CRITICAL_PATH_LENGTH"] == "3"
        assert variables["RESULT_STAGE_PLAN"] == "1: goldfinger | 2: goldeneye | 3: no_time_to_die"
        assert variables["RESULT_RETRY_COUNT"] == "1"

    def test_handoff_tokens_render_measured_recon_outputs(self, tmp_path) -> None:
        """§3's DAG hand-off evidence is generated from the run, not typed."""
        project = _make_project(tmp_path)
        report_dir = project / "output" / "data"
        report_dir.mkdir(parents=True)
        (report_dir / "mission_report.json").write_text(
            json.dumps(
                {
                    "mission": {
                        "name": "OPERATION_OMNIBUS",
                        "packages": [
                            {"id": "goldfinger", "depends_on": []},
                            {"id": "goldeneye", "depends_on": ["goldfinger"]},
                            {"id": "no_time_to_die", "depends_on": ["goldeneye"]},
                        ],
                    },
                    "order": ["goldfinger", "goldeneye", "no_time_to_die"],
                    "executions": [],
                    "debriefs": [{"verdict": "pass"}],
                    "recon": [
                        {"package_id": "goldfinger", "outputs": {"market_index": "0.92"}},
                        {"package_id": "goldeneye", "outputs": {"emp_shield_rating": "0.87"}},
                        {"package_id": "no_time_to_die", "outputs": {}},
                    ],
                }
            )
        )
        variables = generate_variables(project)
        assert variables["RESULT_NUM_HANDOFF_EDGES"] == "2"
        assert variables["RESULT_HANDOFF_SUMMARY"] == (
            "goldfinger → goldeneye: market_index=0.92; goldeneye → no_time_to_die: emp_shield_rating=0.87"
        )

    def test_handoff_edge_without_outputs_renders_bare(self, tmp_path) -> None:
        """An edge whose upstream produced nothing still appears, without a payload."""
        project = _make_project(tmp_path)
        report_dir = project / "output" / "data"
        report_dir.mkdir(parents=True)
        (report_dir / "mission_report.json").write_text(
            json.dumps(
                {
                    "mission": {
                        "name": "M",
                        "packages": [
                            {"id": "a", "depends_on": []},
                            {"id": "b", "depends_on": ["a"]},
                        ],
                    },
                    "order": ["a", "b"],
                    "executions": [],
                    "debriefs": [{"verdict": "pass"}],
                    "recon": [{"package_id": "a", "outputs": {}}],
                }
            )
        )
        variables = generate_variables(project)
        assert variables["RESULT_HANDOFF_SUMMARY"] == "a → b"

    def test_dependency_free_mission_reports_no_handoff_edges(self, tmp_path) -> None:
        project = _make_project(tmp_path)
        report_dir = project / "output" / "data"
        report_dir.mkdir(parents=True)
        (report_dir / "mission_report.json").write_text(
            json.dumps(
                {
                    "mission": {"name": "M", "packages": [{"id": "a", "depends_on": []}]},
                    "order": ["a"],
                    "executions": [],
                    "debriefs": [{"verdict": "pass"}],
                    "recon": [{"package_id": "a", "outputs": {"k": "v"}}],
                }
            )
        )
        variables = generate_variables(project)
        assert variables["RESULT_NUM_HANDOFF_EDGES"] == "0"
        assert variables["RESULT_HANDOFF_SUMMARY"] == "none"

    def test_config_retry_token(self, tmp_path) -> None:
        project = _make_project(tmp_path)
        (project / "manuscript" / "config.yaml").write_text(
            MINIMAL_CONFIG.replace(
                "retry:\n    max_attempts: 1",
                "retry:\n    max_attempts: 3",
            )
        )
        variables = generate_variables(project, require_outputs=False)
        assert variables["CONFIG_RETRY_MAX_ATTEMPTS"] == "3"

    def test_stage_tokens_fallback_to_na_without_report(self, tmp_path) -> None:
        variables = generate_variables(_make_project(tmp_path), require_outputs=False)
        assert variables["RESULT_NUM_STAGES"] == "N/A"
        assert variables["RESULT_MAX_PARALLELISM"] == "N/A"
        assert variables["RESULT_CRITICAL_PATH_LENGTH"] == "N/A"
        assert variables["RESULT_STAGE_PLAN"] == "N/A"
        assert variables["RESULT_RETRY_COUNT"] == "N/A"
        assert variables["RESULT_NUM_HANDOFF_EDGES"] == "N/A"
        assert variables["RESULT_HANDOFF_SUMMARY"] == "N/A"

    def test_failing_verdict_reports_fail(self, tmp_path) -> None:
        project = _make_project(tmp_path)
        report_dir = project / "output" / "data"
        report_dir.mkdir(parents=True)
        (report_dir / "mission_report.json").write_text(
            json.dumps(
                {
                    "order": ["goldfinger"],
                    "executions": [],
                    "debriefs": [{"verdict": "fail"}],
                }
            )
        )
        variables = generate_variables(project)
        assert variables["RESULT_ALL_VERDICTS_PASS"] == "FAIL"


class TestLiveCrossReference:
    def test_all_manuscript_tokens_are_generated(self, project_root: Path) -> None:
        """Every {{TOKEN}} referenced in manuscript sections must be generated.

        SYNTAX.md, AGENTS.md, and README.md are reference manuals that
        illustrate tokens with literal ``{{VARIABLE}}`` placeholders, so they
        are excluded from the scan; rendered sections (00_* .. 99_*) are
        scanned.
        """
        generated = generate_variables(project_root, require_outputs=False)
        manuscript_dir = project_root / "manuscript"
        referenced: set[str] = set()
        for path in sorted(manuscript_dir.glob("*.md")):
            if path.name in ("SYNTAX.md", "AGENTS.md", "README.md"):
                continue
            referenced.update(TOKEN_PATTERN.findall(path.read_text()))
        missing = sorted(referenced - set(generated))
        assert missing == [], f"manuscript tokens without generators: {missing}"

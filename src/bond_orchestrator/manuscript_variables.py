"""Manuscript ``{{TOKEN}}`` hydration from ``manuscript/config.yaml`` + mission report.

Manuscript prose never hand-authors metrics: every numeric/identity token is
injected here.  ``generate_variables`` reads the mission identity/parameters
from ``manuscript/config.yaml`` and, when present, the consolidated mission
report at ``output/data/mission_report.json`` (produced by
``scripts/run_mission.py``).  Strict mode (``require_outputs=True``) raises
when the report is absent; ``--allow-draft`` falls back to ``"N/A"``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import yaml

from .runner import PHASES

CONFIG_FILENAME = "config.yaml"
REPORT_RELATIVE_PATH = Path("output") / "data" / "mission_report.json"


def load_project_config(project_root: Path) -> dict[str, Any]:
    """Load and return ``manuscript/config.yaml`` as a plain dict."""
    config_path = project_root / "manuscript" / CONFIG_FILENAME
    return cast(dict[str, Any], yaml.safe_load(config_path.read_text()))


def generate_variables(project_root: Path, require_outputs: bool = True) -> dict[str, str]:
    """Compute the full ``{TOKEN: value}`` mapping for the manuscript.

    Args:
        project_root: Package root containing ``manuscript/`` and ``output/``.
        require_outputs: When True, raise ``FileNotFoundError`` if the mission
            report is missing instead of using ``"N/A"`` fallbacks.

    Returns:
        Mapping of manuscript token name to resolved string value.
    """
    config = load_project_config(project_root)
    paper = cast(dict[str, Any], config["paper"])
    identity = cast(dict[str, Any], config.get("identity", {}))
    mission = cast(dict[str, Any], config.get("mission", {}))
    authors = cast(list[dict[str, Any]], config.get("authors", []))

    packages = cast(list[str], mission.get("packages", []))
    retry = cast(dict[str, Any], mission.get("retry", {}))
    variables: dict[str, str] = {
        "CONFIG_TITLE": str(paper.get("title", "")),
        "CONFIG_SUBTITLE": str(paper.get("subtitle", "")),
        "CONFIG_VERSION": str(paper.get("version", "")),
        "CONFIG_IDENTITY": str(identity.get("name", "BOND-ORCHESTRATOR")),
        "CONFIG_CODENAME": str(identity.get("codename", "DAG 00")),
        "CONFIG_FIRST_AUTHOR": str(authors[0]["name"]) if authors else "",
        "CONFIG_MISSION_NAME": str(mission.get("name", "")),
        "CONFIG_NUM_PACKAGES": str(len(packages)),
        "CONFIG_PACKAGE_CHAIN": " → ".join(packages),
        "CONFIG_PHASES": ", ".join(PHASES),
        "CONFIG_RETRY_MAX_ATTEMPTS": str(retry.get("max_attempts", 1)),
    }

    report_path = project_root / REPORT_RELATIVE_PATH
    if report_path.exists():
        report = cast(dict[str, Any], json.loads(report_path.read_text()))
        debriefs = cast(list[dict[str, Any]], report.get("debriefs", []))
        all_pass = all(str(d.get("verdict", "")) == "pass" for d in debriefs)
        stage_plan = cast(dict[str, Any] | None, report.get("stage_plan"))
        variables.update(
            {
                "RESULT_EXECUTION_ORDER": " → ".join(cast(list[str], report.get("order", []))),
                "RESULT_NUM_STEPS": str(len(cast(list[Any], report.get("executions", [])))),
                "RESULT_ALL_VERDICTS_PASS": "PASS" if all_pass else "FAIL",
                "RESULT_RETRY_COUNT": str(len(cast(list[Any], report.get("retries", [])))),
                **(_stage_plan_tokens(stage_plan) if stage_plan else _stage_plan_tokens(None)),
            }
        )
    elif require_outputs:
        raise FileNotFoundError(
            f"mission report missing at {report_path}; run "
            "`uv run python scripts/run_mission.py OPERATION_OMNIBUS` first "
            "(or pass --allow-draft for an early draft)"
        )
    else:
        variables.update(
            {
                "RESULT_EXECUTION_ORDER": "N/A",
                "RESULT_NUM_STEPS": "N/A",
                "RESULT_ALL_VERDICTS_PASS": "N/A",
                "RESULT_RETRY_COUNT": "N/A",
                "RESULT_NUM_STAGES": "N/A",
                "RESULT_MAX_PARALLELISM": "N/A",
                "RESULT_CRITICAL_PATH_LENGTH": "N/A",
                "RESULT_STAGE_PLAN": "N/A",
            }
        )
    return variables


def _stage_plan_tokens(stage_plan: dict[str, Any] | None) -> dict[str, str]:
    """RESULT_* tokens derived from the report's ``stage_plan`` block."""
    if stage_plan is None:
        return {
            "RESULT_NUM_STAGES": "N/A",
            "RESULT_MAX_PARALLELISM": "N/A",
            "RESULT_CRITICAL_PATH_LENGTH": "N/A",
            "RESULT_STAGE_PLAN": "N/A",
        }
    stages = cast(list[dict[str, Any]], stage_plan.get("stages", []))
    rendered = " | ".join(
        f"{stage['index']}: {','.join(cast(list[str], stage.get('packages', [])))}" for stage in stages
    )
    return {
        "RESULT_NUM_STAGES": str(len(stages)),
        "RESULT_MAX_PARALLELISM": str(stage_plan.get("max_parallelism", 0)),
        "RESULT_CRITICAL_PATH_LENGTH": str(stage_plan.get("critical_path_length", 0)),
        "RESULT_STAGE_PLAN": rendered,
    }

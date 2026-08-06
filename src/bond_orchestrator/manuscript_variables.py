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

from .missions import MISSION_NAMES, MISSIONS
from .planning import build_stage_plan
from .protocol import Mission
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
        **_mission_surface_tokens(),
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
                **_handoff_tokens(report),
                **_results_tokens(report),
                **_dag_figure(report),
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
                "RESULT_NUM_HANDOFF_EDGES": "N/A",
                "RESULT_HANDOFF_SUMMARY": "N/A",
                "RESULT_PACKAGE_RESULTS": "N/A",
                "RESULT_DAG_FIGURE": "N/A",
            }
        )
    return variables


def _mission_surface_tokens() -> dict[str, str]:
    """``SURFACE_<MISSION>_*`` tokens derived from the mission registry itself.

    §5.4 tabulates the three canned missions' package counts, parallelism and
    critical-path lengths.  Those numbers were hand-typed in the prose, four
    lines after §5.1 states that no metric is hand-authored.  They are now
    computed here from :data:`~bond_orchestrator.missions.MISSIONS` and the
    same :func:`~bond_orchestrator.planning.build_stage_plan` the runner uses,
    so the table cannot disagree with the registry.

    Returns:
        For each registered mission ``M``: ``SURFACE_M_PACKAGES``,
        ``SURFACE_M_HANDOFF_EDGES``, ``SURFACE_M_STAGES``,
        ``SURFACE_M_MAX_PARALLELISM`` and ``SURFACE_M_CRITICAL_PATH``.
    """
    tokens: dict[str, str] = {}
    for name in MISSION_NAMES:
        mission: Mission = MISSIONS[name]
        plan = build_stage_plan(mission)
        edges = sum(len(package.depends_on) for package in mission.packages)
        tokens.update(
            {
                f"SURFACE_{name}_PACKAGES": str(len(mission.packages)),
                f"SURFACE_{name}_HANDOFF_EDGES": str(edges),
                f"SURFACE_{name}_STAGES": str(len(plan.stages)),
                f"SURFACE_{name}_MAX_PARALLELISM": str(plan.max_parallelism()),
                f"SURFACE_{name}_CRITICAL_PATH": str(plan.critical_path_length()),
            }
        )
    return tokens


def _handoff_tokens(report: dict[str, Any]) -> dict[str, str]:
    """RESULT_* tokens describing the DAG's measured recon hand-off edges.

    A hand-off edge is a ``(dependency, dependent)`` pair declared by
    ``depends_on``; its payload is the dependency's *measured* recon
    ``outputs`` as recorded in the mission report.  Rendering them as a token
    keeps §3 prose free of hand-authored metric values: the numbers that show
    a DAG edge actually carried data come from the run, not the author.

    Args:
        report: The parsed ``output/data/mission_report.json`` mapping.

    Returns:
        ``RESULT_NUM_HANDOFF_EDGES`` and ``RESULT_HANDOFF_SUMMARY``.
    """
    mission = cast(dict[str, Any], report.get("mission", {}))
    packages = cast(list[dict[str, Any]], mission.get("packages", []))
    outputs_by_package: dict[str, dict[str, str]] = {
        str(entry.get("package_id", "")): {
            str(key): str(value) for key, value in cast(dict[str, Any], entry.get("outputs", {})).items()
        }
        for entry in cast(list[dict[str, Any]], report.get("recon", []))
    }

    rendered: list[str] = []
    for package in packages:
        package_id = str(package.get("id", ""))
        for dependency in cast(list[str], package.get("depends_on", [])):
            payload = outputs_by_package.get(str(dependency), {})
            values = ", ".join(f"{key}={value}" for key, value in sorted(payload.items()))
            rendered.append(f"{dependency} → {package_id}: {values}" if values else f"{dependency} → {package_id}")

    return {
        "RESULT_NUM_HANDOFF_EDGES": str(len(rendered)),
        "RESULT_HANDOFF_SUMMARY": "; ".join(rendered) if rendered else "none",
    }


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


def _results_tokens(report: dict[str, Any]) -> dict[str, str]:
    """Per-package verdict + numeric metrics rendered as a markdown table.

    Fed by the mission report's ``debriefs`` list, so §3's results table is
    the live execution's own record — no hand-authored cell. Metrics are
    sorted by key and formatted with ``%g`` (deterministic, matches the
    consolidated debrief's rendering).
    """
    debriefs = cast(list[dict[str, Any]], report.get("debriefs", []))
    rows: list[str] = []
    for debrief in debriefs:
        package_id = str(debrief.get("package_id", ""))
        verdict = str(debrief.get("verdict", ""))
        metrics = cast(dict[str, Any], debrief.get("metrics", {}))
        rendered = ", ".join(f"{key}={float(value):g}" for key, value in sorted(metrics.items()))
        rows.append(f"| {package_id} | {verdict} | {rendered} |")
    table = "| Package | Verdict | Metrics |\n|---|---|---|\n" + "\n".join(rows)
    return {"RESULT_PACKAGE_RESULTS": table}


def _dag_figure(report: dict[str, Any]) -> dict[str, str]:
    """A deterministic text 'figure': the measured DAG bound to live results.

    Renders each package from ``report["order"]`` with its stage (from
    ``stage_plan``) and debrief verdict, then each declared hand-off edge with
    the upstream's *measured* recon ``outputs``. Every glyph is derived from
    the run's own JSON, so the figure cannot disagree with the engine.
    """
    order = cast(list[str], report.get("order", []))
    debriefs = cast(list[dict[str, Any]], report.get("debriefs", []))
    recon = cast(list[dict[str, Any]], report.get("recon", []))
    stage_plan = cast(dict[str, Any] | None, report.get("stage_plan"))
    mission = cast(dict[str, Any], report.get("mission", {}))

    verdicts = {str(d.get("package_id", "")): str(d.get("verdict", "")) for d in debriefs}
    stage_of: dict[str, int] = {}
    if stage_plan:
        for stage_obj in cast(list[dict[str, Any]], stage_plan.get("stages", [])):
            for pid in cast(list[str], stage_obj.get("packages", [])):
                stage_of[str(pid)] = cast(int, stage_obj.get("index", 0))
    outputs_by: dict[str, dict[str, str]] = {
        str(r.get("package_id", "")): {str(k): str(v) for k, v in cast(dict[str, Any], r.get("outputs", {})).items()}
        for r in recon
    }

    lines: list[str] = []
    lines.append("measured DAG (from the live mission report)")
    for pid in order:
        stage = stage_of.get(pid, 0)
        verdict = verdicts.get(pid, "?")
        lines.append(f"  stage {stage}  {pid}  verdict={verdict}")
    for package in cast(list[dict[str, Any]], mission.get("packages", [])):
        pid = str(package.get("id", ""))
        for dependency in cast(list[str], package.get("depends_on", [])):
            payload = outputs_by.get(str(dependency), {})
            label = ", ".join(f"{k}={v}" for k, v in sorted(payload.items())) if payload else ""
            arrow = f"\u2502{label}\u2500\u25b6 {pid}" if label else f"\u2502\u2500\u25b6 {pid}"
            lines.append(f"     {arrow}")
    return {"RESULT_DAG_FIGURE": "\n".join(lines)}

"""Real film binding: run orchestrator missions against REAL bond-api film packages.

These tests exercise the consolidation path: film packages built to the
frozen ``bond_api`` protocol are discovered from their own ``src/`` dirs,
adapted to the orchestrator contract, and driven through the real
:class:`~bond_orchestrator.runner.MissionRunner` (DAG order, checkpoint/
resume, provenance).  Zero mocks: the films are real packages with real
domain cores.

The canonical OPERATION_OMNIBUS chain is goldfinger -> goldeneye ->
no_time_to_die; ``goldeneye`` may not be built yet, so the in-suite fixture
mission uses three films that are always available once Phase 2 Wave A lands:
goldfinger -> spectre -> no_time_to_die.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bond_orchestrator.film_providers import (
    FilmProviderAdapter,
    FilmProviderError,
    load_film_providers,
)
from bond_orchestrator.protocol import Mission, MissionContext, MissionPackage
from bond_orchestrator.runner import MissionRunner

BOND = Path(__file__).resolve().parents[2]

REAL_FILMS = ("goldfinger", "spectre", "no_time_to_die")

pytestmark = pytest.mark.skipif(
    not all((BOND / slug / "src" / slug / "mission.py").is_file() for slug in REAL_FILMS),
    reason="real film packages not built yet (Phase 2)",
)


def _real_mission() -> Mission:
    return Mission(
        name="REAL_OMNIBUS",
        packages=(
            MissionPackage(id="goldfinger", title="GOLDFINGER", objective="recon the gold market"),
            MissionPackage(
                id="spectre",
                title="SPECTRE",
                objective="synthesize counterintelligence",
                depends_on=("goldfinger",),
            ),
            MissionPackage(
                id="no_time_to_die",
                title="NO TIME TO DIE",
                objective="develop bioweapon countermeasure",
                depends_on=("spectre",),
            ),
        ),
    )


def test_load_real_films() -> None:
    adapters = load_film_providers(REAL_FILMS, BOND)
    assert set(adapters) == set(REAL_FILMS)
    for slug, adapter in adapters.items():
        assert isinstance(adapter, FilmProviderAdapter)
        assert adapter.name == slug
        # The underlying bond-api provider answers to its slug.
        assert adapter._provider.film == slug  # noqa: SLF001 - test observes the binding


def test_load_missing_film_raises() -> None:
    with pytest.raises(FilmProviderError):
        load_film_providers(("no_such_film_2026",), BOND)


def test_adapter_phase_contract() -> None:
    adapters = load_film_providers(("goldfinger",), BOND)
    adapter = adapters["goldfinger"]
    package = _real_mission().package("goldfinger")
    context = MissionContext()

    text = adapter.brief(package)
    assert isinstance(text, str) and "GRAND SLAM" in text

    report = adapter.recon(package, context)
    assert report.provider == "goldfinger"
    assert report.package_id == "goldfinger"
    assert report.findings, "recon must produce findings"
    assert isinstance(report.outputs, dict)

    plan = adapter.plan(package, context)
    assert plan.steps, "plan must produce steps"
    assert [step.index for step in plan.steps] == list(range(1, len(plan.steps) + 1))

    results = adapter.execute(package, plan, context)
    assert len(results) == len(plan.steps)
    assert all(result.outcome == "success" for result in results)

    debrief = adapter.debrief(package, context, plan, results)
    assert debrief.verdict == "pass"
    assert debrief.assessment
    assert all(isinstance(value, float) for value in debrief.metrics.values())


def test_real_mission_run_with_checkpoint(tmp_path: Path) -> None:
    adapters = load_film_providers(REAL_FILMS, BOND)
    mission = _real_mission()
    runner = MissionRunner(adapters, checkpoint_dir=tmp_path)
    report = runner.run(mission)

    assert report.all_verdicts_pass()
    assert report.order == ("goldfinger", "spectre", "no_time_to_die")
    assert report.total_steps() > 0
    consolidated = report.consolidated_debrief()
    for slug in REAL_FILMS:
        assert slug in consolidated

    # Checkpoint artifacts on disk: manifest + per-step records + report.
    step_dir = tmp_path / mission.name
    assert (step_dir / "manifest.json").is_file()
    assert (step_dir / "report.json").is_file()
    assert len(list(step_dir.glob("*_*.json"))) >= 5 * len(REAL_FILMS)


def test_resume_replays_deterministically(tmp_path: Path) -> None:
    adapters = load_film_providers(REAL_FILMS, BOND)
    mission = _real_mission()
    first = MissionRunner(adapters, checkpoint_dir=tmp_path).run(mission)
    # Second run against the same checkpoint dir replays completed steps.
    second = MissionRunner(adapters, checkpoint_dir=tmp_path).run(mission)
    assert first.consolidated_debrief() == second.consolidated_debrief()
    assert first.as_dict() == second.as_dict()

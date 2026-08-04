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
from typing import Any, cast

import pytest

from bond_orchestrator.film_providers import (
    FilmProviderAdapter,
    FilmProviderError,
    load_film_providers,
)
from bond_orchestrator.graph import CycleError
from bond_orchestrator.planning import build_stage_plan
from bond_orchestrator.protocol import Mission, MissionContext, MissionPackage, MissionProvider
from bond_orchestrator.retry import RetryPolicy, RetryRecord
from bond_orchestrator.runner import MissionRunner

from tests.test_retry import FlakyExecuteDecorator

BOND = Path(__file__).resolve().parents[2]

REAL_FILMS = ("goldfinger", "spectre", "no_time_to_die")
# The canonical OPERATION OMNIBUS chain, now that all three films are built.
REAL_OMNIBUS_FILMS = ("goldfinger", "goldeneye", "no_time_to_die")

pytestmark = pytest.mark.skipif(
    not all((BOND / slug / "src" / slug / "mission.py").is_file() for slug in REAL_FILMS)
    or not all((BOND / slug / "src" / slug / "mission.py").is_file() for slug in REAL_OMNIBUS_FILMS),
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


def _canonical_omnibus() -> Mission:
    """The canonical OPERATION OMNIBUS shape over REAL films."""
    return Mission(
        name="REAL_CANONICAL_OMNIBUS",
        packages=(
            MissionPackage(id="goldfinger", title="GOLDFINGER", objective="recon the gold market"),
            MissionPackage(
                id="goldeneye",
                title="GOLDENEYE",
                objective="assess EMP resilience",
                depends_on=("goldfinger",),
            ),
            MissionPackage(
                id="no_time_to_die",
                title="NO TIME TO DIE",
                objective="develop bioweapon countermeasure",
                depends_on=("goldeneye",),
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


class TestRealCanonicalOmnibus:
    """OPERATION OMNIBUS shape over the REAL goldfinger/goldeneye/no_time_to_die."""

    def test_runs_in_dependency_order(self) -> None:
        adapters = load_film_providers(REAL_OMNIBUS_FILMS, BOND)
        report = MissionRunner(adapters).run(_canonical_omnibus())
        assert report.order == ("goldfinger", "goldeneye", "no_time_to_die")
        assert report.all_verdicts_pass()
        assert report.total_steps() > 0
        for slug in REAL_OMNIBUS_FILMS:
            assert f"* {slug}: PASS" in report.consolidated_debrief()

    def test_dependency_edge_feed(self) -> None:
        """goldeneye's recon consumed goldfinger's outputs (real DAG edge)."""
        adapters = load_film_providers(REAL_OMNIBUS_FILMS, BOND)
        report = MissionRunner(adapters).run(_canonical_omnibus())
        goldeneye = next(r for r in report.recon if r.package_id == "goldeneye")
        assert any("cites goldfinger" in finding for finding in goldeneye.findings)

    def test_stage_plan_is_three_serial_stages(self) -> None:
        plan = build_stage_plan(_canonical_omnibus())
        assert [stage.packages for stage in plan.stages] == [
            ("goldfinger",),
            ("goldeneye",),
            ("no_time_to_die",),
        ]
        assert plan.max_parallelism() == 1
        assert plan.critical_path_length() == 3


class TestRealFilmCycleDetection:
    def test_cycle_between_real_films_detected(self) -> None:
        """A goldfinger <-> goldeneye dependency loop is caught with a path."""
        mission = Mission(
            name="REAL_LOOP",
            packages=(
                MissionPackage(
                    id="goldfinger",
                    title="GOLDFINGER",
                    objective="recon the gold market",
                    depends_on=("goldeneye",),
                ),
                MissionPackage(
                    id="goldeneye",
                    title="GOLDENEYE",
                    objective="assess EMP resilience",
                    depends_on=("goldfinger",),
                ),
            ),
        )
        with pytest.raises(CycleError) as excinfo:
            build_stage_plan(mission)
        assert excinfo.value.cycle == ("goldeneye", "goldfinger", "goldeneye")


class TestRealFilmRetry:
    def test_real_film_transient_failure_retries(self) -> None:
        """A real film with a transient execute fault recovers via the policy."""
        adapters = cast(
            dict[str, MissionProvider],
            load_film_providers(("goldfinger",), BOND),
        )
        adapters["goldfinger"] = FlakyExecuteDecorator(adapters["goldfinger"], fail_attempts=2)
        mission = Mission(
            name="REAL_RETRY",
            packages=(MissionPackage(id="goldfinger", title="GOLDFINGER", objective="recon the gold market"),),
        )
        report = MissionRunner(adapters, retry_policy=RetryPolicy(max_attempts=3)).run(mission)
        assert report.all_verdicts_pass()
        assert report.retries == (RetryRecord(package_id="goldfinger", phase="execute", attempts=3, succeeded=True),)

    def test_real_film_retry_persists_across_resume(self, tmp_path: Path) -> None:
        checkpoint_dir = tmp_path / "state"
        mission = Mission(
            name="REAL_RETRY",
            packages=(MissionPackage(id="goldfinger", title="GOLDFINGER", objective="recon the gold market"),),
        )

        def run_with_flaky() -> dict[str, Any]:
            adapters = cast(
                dict[str, MissionProvider],
                load_film_providers(("goldfinger",), BOND),
            )
            adapters["goldfinger"] = FlakyExecuteDecorator(adapters["goldfinger"], fail_attempts=1)
            return (
                MissionRunner(
                    adapters,
                    checkpoint_dir=checkpoint_dir,
                    retry_policy=RetryPolicy(max_attempts=3),
                )
                .run(mission)
                .as_dict()
            )

        first = run_with_flaky()
        assert first["retries"][0]["attempts"] == 2
        assert run_with_flaky() == first

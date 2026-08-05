"""Byte-level determinism gate for every persisted artifact.

Manuscript §3.2 and §6.1 claim that two fresh runs produce *byte-identical*
checkpoint step files, ``manifest.json``, ``report.json``, ``outcomes.json``
and ``provenance.csv``.  Before this module that claim was ungated: the
existing tests compared ``report.as_dict()`` (a Python ``dict`` equality, which
is blind to key order, separators, indentation and trailing newlines) and
compared provenance as decoded text.

Everything here reads the files back as ``bytes`` and compares those.  The
comparison is between two *independent* runs into two *separate* directories,
so a run cannot pass by reading its own earlier output.

These tests can fail.  Removing ``sort_keys=True`` from any writer in
``runner.py`` / ``provenance.py``, or letting a wall-clock value or a ``set``
iteration order reach a persisted artifact, turns them red.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bond_orchestrator.missions import OPERATION_DIAMOND, OPERATION_OMNIBUS, OPERATION_SINGLET
from bond_orchestrator.protocol import Mission
from bond_orchestrator.provenance import write_outcome_records
from bond_orchestrator.providers import REFERENCE_PROVIDERS
from bond_orchestrator.runner import MissionRunner

ALL_MISSIONS = (OPERATION_OMNIBUS, OPERATION_DIAMOND, OPERATION_SINGLET)


def _run_into(mission: Mission, root: Path) -> Path:
    """Execute ``mission`` fresh, writing checkpoints + provenance under ``root``.

    Args:
        mission: The mission to execute.
        root: A directory unique to this run (never shared with another run).

    Returns:
        The directory holding this run's artifacts.
    """
    root.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = root / "state"
    report = MissionRunner(REFERENCE_PROVIDERS, checkpoint_dir=checkpoint_dir).run(mission)
    write_outcome_records(report, root / "provenance")
    return root


def _artifact_bytes(root: Path) -> dict[str, bytes]:
    """Map every artifact's run-relative path to its raw bytes on disk."""
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


class TestTwoFreshRunsAreByteIdentical:
    """§3.2 / §6.1: two independent fresh runs write identical bytes."""

    @pytest.mark.parametrize("mission", ALL_MISSIONS, ids=lambda m: m.name)
    def test_all_persisted_artifacts_match_byte_for_byte(self, mission: Mission, tmp_path: Path) -> None:
        first = _artifact_bytes(_run_into(mission, tmp_path / "run_a"))
        second = _artifact_bytes(_run_into(mission, tmp_path / "run_b"))

        assert sorted(first) == sorted(second), "the two runs produced different artifact sets"
        assert first, "no artifacts were written; the comparison would be vacuous"
        differing = [name for name in first if first[name] != second[name]]
        assert not differing, f"byte-level drift across two fresh runs: {differing}"

    def test_checkpoint_step_files_specifically_match(self, tmp_path: Path) -> None:
        """The step files named in §6.1, isolated from the aggregate check."""
        first = _run_into(OPERATION_OMNIBUS, tmp_path / "run_a") / "state" / OPERATION_OMNIBUS.name
        second = _run_into(OPERATION_OMNIBUS, tmp_path / "run_b") / "state" / OPERATION_OMNIBUS.name

        step_files = sorted(p.name for p in first.glob("*.json") if p.name not in {"manifest.json", "report.json"})
        # 3 packages x 5 lifecycle phases -> 15 step files; assert the count so
        # an empty glob cannot make the loop below vacuously pass.
        assert len(step_files) == 15, step_files
        for name in step_files:
            assert (first / name).read_bytes() == (second / name).read_bytes(), name

    @pytest.mark.parametrize("name", ["manifest.json", "report.json"])
    def test_manifest_and_report_match(self, name: str, tmp_path: Path) -> None:
        first = _run_into(OPERATION_OMNIBUS, tmp_path / "run_a") / "state" / OPERATION_OMNIBUS.name / name
        second = _run_into(OPERATION_OMNIBUS, tmp_path / "run_b") / "state" / OPERATION_OMNIBUS.name / name
        assert first.read_bytes() == second.read_bytes()

    @pytest.mark.parametrize("name", ["outcomes.json", "provenance.csv"])
    def test_provenance_artifacts_match(self, name: str, tmp_path: Path) -> None:
        first = _run_into(OPERATION_OMNIBUS, tmp_path / "run_a") / "provenance" / name
        second = _run_into(OPERATION_OMNIBUS, tmp_path / "run_b") / "provenance" / name
        assert first.read_bytes() == second.read_bytes()


class TestByteComparisonIsSensitive:
    """Positive control: the comparison used above detects a real difference.

    Without this, a green byte-equality suite could mean "the writers are
    deterministic" *or* "the comparison cannot tell two files apart".  This
    test proves it is the former by feeding the same comparison two artifact
    sets that differ by one byte and requiring it to notice.
    """

    def test_one_byte_of_drift_is_detected(self, tmp_path: Path) -> None:
        root_a = _run_into(OPERATION_OMNIBUS, tmp_path / "run_a")
        root_b = _run_into(OPERATION_OMNIBUS, tmp_path / "run_b")
        target = root_b / "state" / OPERATION_OMNIBUS.name / "report.json"
        target.write_bytes(target.read_bytes() + b" ")

        first, second = _artifact_bytes(root_a), _artifact_bytes(root_b)
        differing = [name for name in first if first[name] != second[name]]
        assert differing == [str(target.relative_to(root_b))]


class TestCheckpointResumeIsByteIdentical:
    """§3.2: a resumed run reproduces a fresh run's bytes, not merely its dict."""

    def test_resumed_report_bytes_match_fresh_report_bytes(self, tmp_path: Path) -> None:
        fresh = _run_into(OPERATION_OMNIBUS, tmp_path / "fresh")
        resumed_root = _run_into(OPERATION_OMNIBUS, tmp_path / "resumed")
        # Second pass over the same checkpoint dir: every step replays from disk.
        MissionRunner(
            REFERENCE_PROVIDERS,
            checkpoint_dir=resumed_root / "state",
        ).run(OPERATION_OMNIBUS)

        fresh_report = fresh / "state" / OPERATION_OMNIBUS.name / "report.json"
        resumed_report = resumed_root / "state" / OPERATION_OMNIBUS.name / "report.json"
        assert resumed_report.read_bytes() == fresh_report.read_bytes()

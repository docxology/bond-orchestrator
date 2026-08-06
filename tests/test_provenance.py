"""Tests for provenance recording (mission_io-equivalent)."""

from __future__ import annotations

import csv
import json

from bond_orchestrator.missions import OPERATION_DIAMOND, OPERATION_OMNIBUS
from bond_orchestrator.protocol import Mission, MissionPackage
from bond_orchestrator.provenance import (
    PROVENANCE_CSV_FIELDS,
    PROVENANCE_SCHEMA_VERSION,
    ProvenanceRecord,
    collect_outcome_records,
    derive_run_id,
    write_mission_report,
    write_outcome_records,
)
from bond_orchestrator.providers import REFERENCE_PROVIDERS
from bond_orchestrator.runner import MissionRunner


def _omnibus_report():
    return MissionRunner(REFERENCE_PROVIDERS).run(OPERATION_OMNIBUS)


class TestRunId:
    def test_derive_run_id_deterministic(self) -> None:
        assert derive_run_id(OPERATION_OMNIBUS) == derive_run_id(OPERATION_OMNIBUS)

    def test_derive_run_id_distinct_per_mission(self) -> None:
        assert derive_run_id(OPERATION_OMNIBUS) != derive_run_id(OPERATION_DIAMOND)

    def test_run_id_is_twelve_hex_chars(self) -> None:
        assert len(derive_run_id(OPERATION_OMNIBUS)) == 12

    def test_run_id_fingerprints_dependency_structure(self) -> None:
        """Two missions with the same name and package set but different edges
        must NOT share a provenance run id (pre-round-2 hashed name+ids only)."""
        a = MissionPackage(id="a", title="A", objective="x")
        m1 = Mission(
            name="M",
            packages=(
                a,
                MissionPackage(id="b", title="B", objective="y", depends_on=("a",)),
            ),
        )
        m2 = Mission(
            name="M",
            packages=(a, MissionPackage(id="b", title="B", objective="y")),  # edge removed
        )
        assert derive_run_id(m1) != derive_run_id(m2)


class TestCollectOutcomeRecords:
    def test_one_record_per_outcome(self) -> None:
        report = _omnibus_report()
        records = collect_outcome_records(OPERATION_OMNIBUS, report)
        assert len(records) == len(report.executions) + len(report.debriefs) == 9

    def test_phases_and_outcomes(self) -> None:
        report = _omnibus_report()
        records = collect_outcome_records(OPERATION_OMNIBUS, report)
        execute_records = [r for r in records if r.phase == "execute"]
        debrief_records = [r for r in records if r.phase == "debrief"]
        assert all(r.outcome == "success" for r in execute_records)
        assert all(r.outcome == "pass" for r in debrief_records)

    def test_custom_run_id_and_identity_fields(self) -> None:
        report = _omnibus_report()
        records = collect_outcome_records(OPERATION_OMNIBUS, report, run_id="deadbeef")
        assert all(r.run_id == "deadbeef" for r in records)
        first = records[0].as_dict()
        assert first["orchestrator"] == "BOND-ORCHESTRATOR"
        assert first["codename"] == "DAG 00"
        assert first["schema_version"] == PROVENANCE_SCHEMA_VERSION


class TestWriteOutcomeRecords:
    def test_json_and_csv_written(self, tmp_path) -> None:
        report = _omnibus_report()
        json_path, csv_path = write_outcome_records(report, tmp_path / "provenance")
        assert json_path.exists() and csv_path.exists()

        records = json.loads(json_path.read_text())
        assert len(records) == 9
        assert records[0]["mission"] == "OPERATION_OMNIBUS"

        with csv_path.open() as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == list(PROVENANCE_CSV_FIELDS)
        assert len(rows) == 10  # header + 9 records
        # csv row 9 is the no_time_to_die debrief record
        assert rows[9][5] == "no_time_to_die"
        assert rows[9][7] == "debrief"

    def test_records_deterministic_across_runs(self, tmp_path) -> None:
        first = write_outcome_records(_omnibus_report(), tmp_path / "a")
        second = write_outcome_records(_omnibus_report(), tmp_path / "b")
        assert first[0].read_text() == second[0].read_text()
        assert first[1].read_text() == second[1].read_text()


class TestWriteMissionReport:
    def test_report_json_contains_consolidated_debrief(self, tmp_path) -> None:
        report = _omnibus_report()
        path = write_mission_report(report, tmp_path / "mission_report.json")
        data = json.loads(path.read_text())
        assert data["consolidated_debrief"] == report.consolidated_debrief()
        assert data["order"] == ["goldfinger", "goldeneye", "no_time_to_die"]


class TestProvenanceRecord:
    def test_csv_row_roundtrip(self) -> None:
        record = ProvenanceRecord(
            run_id="abc123",
            mission="OPERATION_OMNIBUS",
            package_id="goldfinger",
            provider="goldfinger",
            phase="debrief",
            outcome="pass",
            detail="ok",
            artifact_refs={"verdict": "pass"},
            metrics={"score": 0.92},
        )
        row = record.as_csv_row()
        assert row[0] == "abc123"
        assert row[8] == "pass"
        assert json.loads(row[10]) == {"verdict": "pass"}
        assert json.loads(row[11]) == {"score": 0.92}

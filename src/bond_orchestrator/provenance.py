"""Provenance recording for every mission outcome.

This module is an **independent, non-delegating** provenance writer today: it
does not import ``bond-utilities.mission_io`` and its record schema differs
from that helper's (see ``TODO.md`` V1/E6). It is the canonical writer of one :class:`ProvenanceRecord` per executed plan step and per debrief,
serialized to ``outcomes.json`` (record list) and ``provenance.csv`` (flat
rows) with a deterministic ``run_id`` so records are reproducible.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from .protocol import Mission, mission_fingerprint
from .runner import MissionReport

ORCHESTRATOR_IDENTITY = "BOND-ORCHESTRATOR"
ORCHESTRATOR_CODENAME = "DAG 00"
PROVENANCE_SCHEMA_VERSION = "1.0"

PROVENANCE_CSV_FIELDS = (
    "run_id",
    "orchestrator",
    "codename",
    "schema_version",
    "mission",
    "package_id",
    "provider",
    "phase",
    "outcome",
    "detail",
    "artifact_refs",
    "metrics",
)


@dataclass(frozen=True)
class ProvenanceRecord:
    """One provenance record for a single outcome (step execution or debrief)."""

    run_id: str
    mission: str
    package_id: str
    provider: str
    phase: str
    outcome: str
    detail: str = ""
    artifact_refs: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Deterministic serialization (sorted keys via ``sort_keys`` at write time)."""
        return {
            "run_id": self.run_id,
            "orchestrator": ORCHESTRATOR_IDENTITY,
            "codename": ORCHESTRATOR_CODENAME,
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "mission": self.mission,
            "package_id": self.package_id,
            "provider": self.provider,
            "phase": self.phase,
            "outcome": self.outcome,
            "detail": self.detail,
            "artifact_refs": dict(self.artifact_refs),
            "metrics": dict(self.metrics),
        }

    def as_csv_row(self) -> list[str]:
        """Flat CSV row aligned with :data:`PROVENANCE_CSV_FIELDS`."""
        return [
            self.run_id,
            ORCHESTRATOR_IDENTITY,
            ORCHESTRATOR_CODENAME,
            PROVENANCE_SCHEMA_VERSION,
            self.mission,
            self.package_id,
            self.provider,
            self.phase,
            self.outcome,
            self.detail,
            json.dumps(self.artifact_refs, sort_keys=True),
            json.dumps(self.metrics, sort_keys=True),
        ]


def derive_run_id(mission: Mission) -> str:
    """Deterministic run id: 12 hex chars of the mission-definition fingerprint.

    Fingerprints the *full* mission definition (name plus every package and its
    ``depends_on`` edges) via :func:`bond_orchestrator.protocol.mission_fingerprint`,
    so two missions that share a name and package set but differ in any
    dependency edge cannot collide on a provenance run id. (The prior form
    hashed name + package ids only and was blind to the DAG structure.)
    """
    return mission_fingerprint(mission)[:12]


def collect_outcome_records(
    mission: Mission,
    report: MissionReport,
    run_id: str | None = None,
) -> list[ProvenanceRecord]:
    """One record per execution result, then one per debrief (topological order)."""
    resolved_run_id = run_id if run_id is not None else derive_run_id(mission)
    records: list[ProvenanceRecord] = []
    for result in report.executions:
        records.append(
            ProvenanceRecord(
                run_id=resolved_run_id,
                mission=mission.name,
                package_id=result.package_id,
                provider=result.provider,
                phase="execute",
                outcome=result.outcome,
                detail=result.detail,
                artifact_refs={"action": result.action, "step_index": str(result.step_index)},
            )
        )
    for debrief in report.debriefs:
        records.append(
            ProvenanceRecord(
                run_id=resolved_run_id,
                mission=mission.name,
                package_id=debrief.package_id,
                provider=debrief.provider,
                phase="debrief",
                outcome=debrief.verdict,
                detail=debrief.assessment,
                artifact_refs={"verdict": debrief.verdict},
                metrics=dict(debrief.metrics),
            )
        )
    return records


def write_outcome_records(
    report: MissionReport,
    out_dir: Path,
    run_id: str | None = None,
) -> tuple[Path, Path]:
    """Write ``outcomes.json`` + ``provenance.csv`` under ``out_dir``.

    Returns:
        Tuple of the two written paths (json first, then csv).
    """
    records = collect_outcome_records(report.mission, report, run_id=run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "outcomes.json"
    csv_path = out_dir / "provenance.csv"
    json_path.write_text(json.dumps([record.as_dict() for record in records], indent=2, sort_keys=True) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(PROVENANCE_CSV_FIELDS))
        for record in records:
            writer.writerow(record.as_csv_row())
    return json_path, csv_path


def write_mission_report(report: MissionReport, path: Path) -> Path:
    """Write the full consolidated mission report as JSON; returns ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n")
    return path

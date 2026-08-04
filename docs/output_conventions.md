# Output Conventions — bond-orchestrator

`output/` is disposable: everything under it is written by scripts and
overwritten on every run. Never hand-edit generated files — change the
generator instead.

## Layout

```
output/
├── data/
│   ├── mission_report.json        # consolidated MissionReport (provenance.py::write_mission_report)
│   ├── provenance/
│   │   ├── outcomes.json          # per-outcome ProvenanceRecords (provenance.py::write_outcome_records)
│   │   └── provenance.csv         # flat CSV rows, same records
│   └── manuscript_variables.json  # {{TOKEN}} map (scripts/generate_manuscript_variables.py)
└── state/
    └── <mission>/
        ├── manifest.json          # completed step ids
        ├── <phase>_<package>.json # per-step payloads (checkpoint layer)
        └── report.json            # full report at completion
```

## Regeneration sequence

```bash
# 1. Run the mission (writes mission_report.json + provenance + checkpoint state)
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state

# 2. Hydrate manuscript tokens from config.yaml + mission_report.json
uv run python scripts/generate_manuscript_variables.py
```

- `--checkpoint-dir` is optional; without it no state is persisted and every
  run is fresh.
- Delete `output/state/<mission>/` to force a fresh (non-resumed) run.
- `--allow-draft` on the variables script uses `"N/A"` fallbacks when the
  mission report is absent (early drafts only).

## Producer/consumer map

| Artifact | Producer | Consumers |
|---|---|---|
| `output/data/mission_report.json` | `scripts/run_mission.py` | `manuscript_variables.generate_variables` (RESULT_* tokens) |
| `output/data/provenance/*` | `scripts/run_mission.py` | humans, evidence tooling |
| `output/data/manuscript_variables.json` | `scripts/generate_manuscript_variables.py` | rendering pipeline |
| `output/state/<mission>/*` | runner checkpoint layer | subsequent resumed runs |

Determinism: every JSON/CSV artifact is written with `sort_keys=True` —
byte-stable for identical inputs.

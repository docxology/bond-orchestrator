# Reproducibility

## 6.1 Determinism policy

Determinism is a hard contract, not a preference:

- Providers are pure with respect to their inputs (fixed spec classes in
  `src/bond_orchestrator/providers.py`); there are no random draws and no
  wall-clock dependencies in any report artifact.
- Topological order is canonical (sorted ready-worklist), so execution order
  is declaration-order independent.
- Checkpoint step files, `manifest.json`, `report.json`, `outcomes.json`, and
  `provenance.csv` are written with `sort_keys=True` — byte-stable across runs
  for identical inputs. Two-run byte-equality tests enforce this boundary.
- Wall-clock timing is never part of a persisted artifact.

## 6.2 Verification commands

```bash
# Enforced gate: tests + ≥90% line+branch coverage on src/
uv run pytest tests/ --cov=src --cov-fail-under=90

# No mocks anywhere in tests/
grep -r "unittest.mock\|MagicMock\|@patch\|create_autospec" tests/ || echo "Clean"

# No template-scaffold lineage strings
rg -n "template_code_project" . --glob '!uv.lock' --glob '!.git/**' || echo "Clean"

# Reproduce the flagship run + provenance
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state

# Hydrate manuscript tokens (strict: requires the mission report above)
uv run python scripts/generate_manuscript_variables.py
```

## 6.3 Artifact inventory

| Artifact | Producer | Status |
|---|---|---|
| `output/data/mission_report.json` | `scripts/run_mission.py` | Regenerated |
| `output/data/provenance/outcomes.json`, `provenance.csv` | `scripts/run_mission.py` | Regenerated |
| `output/state/<mission>/*.json` | runner checkpoint layer | Regenerated |
| `output/data/manuscript_variables.json` | `scripts/generate_manuscript_variables.py` | Regenerated |

For {{CONFIG_MISSION_NAME}} (version {{CONFIG_VERSION}}, first author
{{CONFIG_FIRST_AUTHOR}}) the all-verdicts outcome was
**{{RESULT_ALL_VERDICTS_PASS}}**. Live test counts and measured coverage are
tracked in [`docs/_generated/COUNTS.md`](../docs/_generated/COUNTS.md).

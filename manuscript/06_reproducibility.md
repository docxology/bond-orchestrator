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
  for identical inputs. `tests/test_determinism_bytes.py` enforces this
  boundary at the byte level: it executes each of the three missions twice
  into two separate directories and compares every written file with
  `Path.read_bytes()`, so key order, separators, indentation and trailing
  newlines are all in scope. It carries a positive control
  (`TestByteComparisonIsSensitive`) proving the comparison detects a
  one-byte difference, and injecting a wall-clock value into any persisted
  record turns it red. Earlier revisions compared `report.as_dict()` — a
  Python `dict` equality that is blind to all of the above.
- Wall-clock timing is never part of a persisted artifact.

## 6.2 Verification commands

```bash
# Enforced gate: tests + ≥90% line+branch coverage on src/
uv run pytest tests/ --cov=src --cov-fail-under=90

# No mocks anywhere in tests/
grep -r "unittest.mock\|MagicMock\|@patch\|create_autospec" tests/ || echo "Clean"

# Packaging + lineage honesty gates (declared-vs-imported dependencies, a
# relative bond-api path, no forked-scaffold slug in any declared value)
uv run pytest tests/test_packaging.py -v

# Reproduce the flagship run + provenance
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state

# Hydrate manuscript tokens (strict: requires the mission report above)
uv run python scripts/generate_manuscript_variables.py
```

The lineage check is a test, not a `rg` one-liner. The one-liner previously
printed here never reported `Clean`: `rg` skips dotfiles by default, so it was
blind to `.template-export.json` — a stale export manifest whose recorded
`source_project` named the exemplar and whose 1,075 file hashes had decayed to
12 matches and 1,014 deleted paths. That file has been removed. The command
also matched its own text in this manuscript and in `docs/AGENTS.md`, so it
could not have printed `Clean` even on a genuinely clean tree.

What the replacement gate covers, stated so it is not read as more: it scans
every `.py` file under `src/`, `scripts/` and `tests/` for the exemplar slug,
and every scalar *value* of `pyproject.toml`, `manuscript/config.yaml`,
`CITATION.cff`, `codemeta.json`, `.zenodo.json`, `domain_profile.yaml`,
`experiment_plan.yaml` and `export.toml`. It does **not** scan Markdown prose
or configuration comments, because this package's own remediation notes name
the fork source deliberately. Un-forked *narrative* text is therefore not
gated and remains a review responsibility.

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

# scripts/

Thin orchestrators for BOND-ORCHESTRATOR (codename DAG 00).

- `run_mission.py` — run a canned mission (`list`, `run <mission>
  [--checkpoint-dir]`) with report + provenance persistence.
- `generate_manuscript_variables.py` — hydrate `{{TOKEN}}`s from
  `manuscript/config.yaml` + `output/data/mission_report.json`.

See [`AGENTS.md`](AGENTS.md) for the thin-orchestrator contract.

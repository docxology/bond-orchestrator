# scripts/ — Thin Orchestrators

## Overview

The `scripts/` directory contains **thin orchestrators**: `sys.path`
bootstrap + argv forwarding only. All mission logic lives in
`src/bond_orchestrator/`. The boundary test: if a line here determines mission
semantics (order, phases, checkpoint decisions, verdicts), it belongs in
`src/` with a test.

## Scripts

| Script | Wraps | Purpose |
|---|---|---|
| `run_mission.py` | `bond_orchestrator.cli.main` | `list` missions; `plan <mission>` stage plan; `run <mission> [--checkpoint-dir DIR] [--output-dir DIR] [--retry-max-attempts N]`; persists report + provenance; prints consolidated debrief |
| `generate_manuscript_variables.py` | `bond_orchestrator.manuscript_variables.generate_variables` | Hydrates `{{TOKEN}}` map to `output/data/manuscript_variables.json` (strict; `--allow-draft` for N/A fallbacks) |
| `__init__.py` | — | Package marker |

## Usage

```bash
# From the package directory
uv run python scripts/run_mission.py list
uv run python scripts/run_mission.py plan OPERATION_OMNIBUS
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state
uv run python scripts/run_mission.py OPERATION_OMNIBUS --retry-max-attempts 3
uv run python scripts/run_mission.py run OPERATION_OMNIBUS   # explicit subcommand
uv run python scripts/generate_manuscript_variables.py
uv run python scripts/generate_manuscript_variables.py --allow-draft
```

`run_mission.py` defaults the subcommand to `run` when the first argument is
not a known command (`run`/`list`/`plan`), so
`run_mission.py OPERATION_OMNIBUS` is equivalent to
`run_mission.py run OPERATION_OMNIBUS` (see `_with_default_command`).

## Conventions

- Scripts never import `infrastructure.*` (package runs standalone).
- No business logic, no literal phase lists, no hardcoded mission data —
  everything comes from `src/bond_orchestrator/` or `manuscript/config.yaml`.
- Exit codes: `run` returns 0 iff every debrief verdict is `"pass"`; argparse
  errors exit 2.

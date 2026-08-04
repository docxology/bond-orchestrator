# Live Counts — bond-orchestrator

Regenerated whenever the suite changes; never hardcode these numbers in prose
(they drift faster than the docs touching them).

## Test suite (measured 2026-08-04, phase-1 build)

| Metric | Value |
|---|---|
| Tests passing | 77 |
| Tests skipped / failed | 0 / 0 |
| Line coverage on `src/` | 98.16% |
| Branch coverage on `src/` | ≥92% |
| Coverage floor (`pyproject.toml`) | 90% |

Command: `uv run pytest tests/ --cov=src --cov-fail-under=90`

## Source surface

- `src/bond_orchestrator/`: protocol, graph, runner, missions, providers,
  provenance, manuscript_variables, cli (544 statements measured)
- `scripts/`: run_mission.py, generate_manuscript_variables.py (thin)

## Mission registry

OPERATION_OMNIBUS (goldfinger → goldeneye → no_time_to_die) ·
OPERATION_DIAMOND (thunderball, from_russia_with_love → spectre) ·
OPERATION_SINGLET (goldfinger)

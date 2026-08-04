# Live Counts — bond-orchestrator

Regenerated whenever the suite changes; never hardcode these numbers in prose
(they drift faster than the docs touching them).

## Test suite (measured 2026-08-04, phase-4 build)

| Metric | Value |
|---|---|
| Tests passing | 131 |
| Tests skipped / failed | 0 / 0 |
| Line coverage on `src/` | 97.54% |
| Branch coverage on `src/` | ≥92% |
| Coverage floor (`pyproject.toml`) | 90% |

Command: `uv run pytest tests/ --cov=src --cov-fail-under=90`

## Source surface

- `src/bond_orchestrator/`: protocol, graph, planning, retry, runner,
  missions, providers, film_providers, provenance, manuscript_variables, cli
- `scripts/`: run_mission.py, generate_manuscript_variables.py (thin)

## Mission registry

OPERATION_OMNIBUS (goldfinger → goldeneye → no_time_to_die) ·
OPERATION_DIAMOND (thunderball, from_russia_with_love → spectre) ·
OPERATION_SINGLET (goldfinger)

## CLI

`run <mission> [--checkpoint-dir] [--output-dir] [--retry-max-attempts N]` ·
`plan <mission>` · `list`

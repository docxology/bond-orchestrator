# Live Counts — bond-orchestrator

Regenerated whenever the suite changes; never hardcode these numbers in prose
(they drift faster than the docs touching them). Everything below was read out
of an actual gate run — no figure here is estimated or rounded.

## Test suite (measured 2026-08-06, round-2 improvement pass)

| Metric | Value |
|---|---|
| Tests passing | 178 |
| Tests skipped / failed | 0 / 0 |
| Statements in `src/` | 840 |
| Statements missed | 0 |
| Line coverage on `src/` | 100.00% |
| Branches in `src/` | 190 |
| Partial branches | 10 |
| Branch coverage on `src/` | 94.74% |
| Combined line+branch coverage (the gate's figure) | 99.03% |
| Coverage floor (`pyproject.toml`) | 90% |
| Interpreter used for this run | CPython 3.14.6 (darwin) |

Commands:

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90     # the enforced gate
uv run coverage json -o cov.json                       # for the split figures
```

The gate prints the combined line+branch figure (99.03%); the split figures
come from `coverage json`. The 10 partial branches are the `...` bodies of the
`MissionProvider` Protocol stubs (9) plus one fall-through in checkpoint
replay: structural, not logic gaps. See `docs/testing_philosophy.md`.

Round-2 added 5 tests (173 → 178) for the three hardened gates: checkpoint
definition-hash resume (C1), empty-mission rejection, and the full-definition
provenance run id.

## Lint and types

| Gate | Command | Result |
|---|---|---|
| ruff lint | `uv run ruff check src/ scripts/ tests/` | clean |
| ruff format | `uv run ruff format --check src/ scripts/` | 15 files already formatted |
| packaging + lineage gates | `uv run pytest tests/test_packaging.py` | 15 passed |
| byte-determinism gates | `uv run pytest tests/test_determinism_bytes.py` | 10 passed |
| mypy | `uv run mypy src/ scripts/` | no issues in 15 source files |

## Source surface

`src/bond_orchestrator/` — 11 modules:
protocol · graph · planning · retry · runner · missions · providers ·
film_providers · provenance · manuscript_variables · cli

`scripts/` — 2 thin orchestrators:
run_mission.py · generate_manuscript_variables.py

`tests/` — 14 test modules:
test_protocol · test_graph · test_planning · test_retry · test_runner ·
test_missions · test_cli · test_provenance · test_manuscript_variables ·
test_integration · test_film_binding · test_scripts_smoke ·
test_determinism_bytes · test_packaging

## Mission registry

OPERATION_OMNIBUS (goldfinger → goldeneye → no_time_to_die) ·
OPERATION_DIAMOND (thunderball, from_russia_with_love → spectre) ·
OPERATION_SINGLET (goldfinger)

## Manuscript tokens

36 tokens generated (11 `CONFIG_*`, 15 `SURFACE_*`, 10 `RESULT_*`),
cross-checked against
every rendered manuscript section by
`tests/test_manuscript_variables.py::TestLiveCrossReference`. Regenerate:

```bash
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state
uv run python scripts/generate_manuscript_variables.py
```

## CLI

`run <mission> [--checkpoint-dir] [--output-dir] [--retry-max-attempts N]` ·
`plan <mission>` · `list`

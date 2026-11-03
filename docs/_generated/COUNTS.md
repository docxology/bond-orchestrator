# Live Counts — bond-orchestrator

Regenerated whenever the suite changes; never hardcode these numbers in prose
(they drift faster than the docs touching them). Everything below was read out
of an actual gate run — no figure here is estimated or rounded.

## Test suite (measured 2026-11-03, lock-and-film-binding pass)

| Metric | Value |
|---|---|
| Tests passing | 179 |
| Tests skipped / failed | 0 / 0 |
| Statements in `src/` | 846 |
| Statements missed | 0 |
| Line coverage on `src/` | 100.00% |
| Branches in `src/` | 194 |
| Partial branches | 10 |
| Branch coverage on `src/` | 94.85% |
| Combined line+branch coverage (the gate's figure) | 99.04% |
| Coverage floor (`pyproject.toml`) | 90% |
| Interpreter used for this run | CPython 3.15.1 (darwin) |

Commands:

```bash
uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90     # the enforced gate
uv run coverage json -o cov.json                       # for the split figures
```

The gate prints the combined line+branch figure (99.04%); the split figures
come from `coverage json`. The 10 partial branches are the `...` bodies of the
`MissionProvider` Protocol stubs (9) plus one fall-through in checkpoint
replay: structural, not logic gaps. See `docs/testing_philosophy.md`.

Round-2 added 5 tests (173 → 178) for the three hardened gates: checkpoint
definition-hash resume (C1), empty-mission rejection, and the full-definition
provenance run id.

This pass added 1 test (178 → 179) and 6 statements (840 → 846): the
film-package path resolution now has its own named helper
(`film_providers.film_package_dir`, with the gate asserting the directory
naming), so `film_package_dir` and its call site are the new statements. The
eleven failures this repaired were the gate's, not the claim's — the gate
joined a film slug straight onto the workspace root while every film directory
carries the `bond-` prefix — so suite health moved with no change to what the
package does.

## Lint and types

| Gate | Command | Result |
|---|---|---|
| ruff lint | `uvx ruff check --line-length 120 src/ scripts/ tests/` | **28 findings, all pre-existing** — see the note below |
| ruff format | `uvx ruff format --check --line-length 120 src/ scripts/` | 20 files already formatted |
| packaging + lineage gates | `uv run --extra dev pytest tests/test_packaging.py` | 15 passed |
| byte-determinism gates | `uv run --extra dev pytest tests/test_determinism_bytes.py` | 10 passed |
| mypy | `uvx mypy src/ scripts/` | no issues found in 15 source files |

**Note on the ruff row.** The earlier figure in this file said `clean`, and that
does not reproduce: run against the current `uvx ruff` (no `[tool.ruff]` is
committed here, so the tool's defaults apply) the check reports 28 findings at
the house line length and 31 at the default one, of which the great majority are
in `src/bond_orchestrator/providers.py` (14) and `tests/conftest.py` (4). The
twelve it will fix automatically are unused `noqa: SLF001` directives (the rule
is not enabled here) and one unsorted import block. **All of them are
pre-existing**: the count is 28 both with and without this pass's change, and the
files carrying them are not the files this pass touched. They are recorded rather
than swept, because a 28-finding lint sweep across ten files is a change of its
own and does not belong inside a path-resolution repair. What this means in
practice: the ruff row above is a measurement with its command named, not a claim
that the tree is lint-clean.

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

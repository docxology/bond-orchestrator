# Live Counts — bond-orchestrator

Regenerated whenever the suite changes; never hardcode these numbers in prose
(they drift faster than the docs touching them). Everything below was read out
of an actual gate run — no figure here is estimated or rounded.

## Test suite (measured 2026-11-04, bond-api vendoring pass)

| Metric | Value |
|---|---|
| Tests passing | 180 |
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
provenance run id. The lock-and-film-binding pass added 1 test (178 → 179) and
6 statements (840 → 846): the film-package path resolution now has its own named
helper (`film_providers.film_package_dir`, with the gate asserting the directory
naming), so `film_package_dir` and its call site are the new statements. The
eleven failures that pass repaired were the gate's, not the claim's — the gate
joined a film slug straight onto the workspace root while every film directory
carries the `bond-` prefix — so suite health moved with no change to what the
package does.

The vendoring pass added 1 test (179 → **180**): `tests/test_vendor_provenance.py`
runs `scripts/vendor.py --check` inside the suite. `--cov=src` is unchanged by it
— `scripts/vendor.py` is not part of the measured package.

## Lint and types

| Gate | Command | Result |
|---|---|---|
| ruff lint | `uvx ruff check src/ scripts/ tests/` | **28 findings, all pre-existing** (16 RUF012, 8 RUF100, 3 I001, 1 RUF022) — see the note below |
| ruff format | `uvx ruff format --check --line-length 120 src/ scripts/` | 21 files already formatted |
| packaging + lineage gates | `uv run --extra dev pytest tests/test_packaging.py` | 15 passed |
| byte-determinism gates | `uv run --extra dev pytest tests/test_determinism_bytes.py` | 10 passed |
| mypy | `uvx mypy src/ scripts/` | no issues found in 16 source files |
| recorded copies | `uv run --no-sync python scripts/vendor.py --check` | `vendor/bond-api: ok`, 0 findings |

**The ruff rows now read the committed `[tool.ruff]` table.** This pass adds that
table (it carries the `vendor/` exclusion) and declares `line-length = 120`, the
width this tree is written to: with the table in place the documented check
reports 28 findings at the house length, and with the width line removed it
reports 31 at the formatter's default 88 — the same command, the same tree, only
the table's body varying. Before this pass no `[tool.ruff]` existed in the
checkout, so the tool's defaults applied and neither figure was reachable from a
committed file.

**Tool versions are recorded because the commands do not pin them.** `ruff` and
`mypy` are not declared dependencies, so `uvx` fetches the current release:
these figures were measured with `uvx ruff 0.17.3` and `uvx mypy 2.4.1`. A
future release can move the finding count without any change to this tree, which
is why the numbers above are dated and versioned rather than left bare.

**Note on the ruff row.** The earlier figure in this file said `clean`, and that
does not reproduce: run against `uvx ruff` the check reports 28 findings at the
house line length and 31 at the default one, of which the great majority are in
`src/bond_orchestrator/providers.py` (14) and `tests/conftest.py` (4). The
twelve it will fix automatically are eight unused `noqa: SLF001` directives (the
rule is not enabled here), three unsorted import blocks and one unsorted
`__all__`. **All of them are pre-existing**: the count is 28 both with and
without the vendoring change, and none of the 28 is in `vendor/` or in the two
files this pass adds. They are recorded rather than swept, because a 28-finding
lint sweep across ten files is a change of its own and does not belong inside a
dependency change. What this means in practice: the ruff row above is a
measurement with its command named, not a claim that the tree is lint-clean.

## Source surface

`src/bond_orchestrator/` — 11 modules:
protocol · graph · planning · retry · runner · missions · providers ·
film_providers · provenance · manuscript_variables · cli

`scripts/` — 2 thin orchestrators plus the vendoring checker:
run_mission.py · generate_manuscript_variables.py · vendor.py

`tests/` — 15 test modules:
test_protocol · test_graph · test_planning · test_retry · test_runner ·
test_missions · test_cli · test_provenance · test_manuscript_variables ·
test_integration · test_film_binding · test_scripts_smoke ·
test_determinism_bytes · test_packaging · test_vendor_provenance

`vendor/bond-api/` — the recorded copy of the `bond-api` protocol package
(upstream commit `c0362ff0c9d7`, per-file sha256 in `PROVENANCE.json`).

## Mission registry

OPERATION_OMNIBUS (goldfinger → goldeneye → no_time_to_die) ·
OPERATION_DIAMOND (thunderball, from_russia_with_love → spectre) ·
OPERATION_SINGLET (goldfinger)

## Manuscript tokens

38 tokens generated (11 `CONFIG_*`, 15 `SURFACE_*`, 12 `RESULT_*`),
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

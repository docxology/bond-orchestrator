# AI Agent Instructions — bond-orchestrator

## Why This File Exists

`bond-orchestrator` is the **Layer 3 mission DAG runner** of the BOND suite.
Its contract is narrow: execute multi-package film missions end-to-end over
the `MissionProvider` protocol, in deterministic topological order, with
checkpoint/resume and provenance on every outcome. Deviating from the rules
below — introducing a mock, moving business logic into scripts/, importing
`infrastructure` into the pure core — breaks the package's guarantees and the
BOND-suite integration points.

Read this file before touching any other file in this project.

---

## Rule 1: Read the Hub First

Reading order is mandatory, not advisory. Each document gates a category of
action:

| Document | Governs | Skip consequence |
|---|---|---|
| **This file** | All modifications | Risk all violations below |
| [`architecture.md`](architecture.md) | Any file-boundary change | Risk violating src/scripts boundary |
| [`protocol.md`](protocol.md) | The `MissionProvider` contract | Risk breaking bond-api integration |
| [`testing_philosophy.md`](testing_philosophy.md) | Any test modification | Risk introducing mocks or reducing coverage |
| [`style_guide.md`](style_guide.md) | Any source code modification | Risk wrong import layer, bad error messages |
| [`output_conventions.md`](output_conventions.md) | Any output/ change | Risk editing generated files |
| [`_generated/COUNTS.md`](_generated/COUNTS.md) | Any claim about a measured number | Risk quoting a stale figure as evidence |

---

## Rule 2: Coverage Gate — ≥90% on `src/`

The enforced gate is `pyproject.toml`'s `fail_under = 90` on line **and**
branch coverage over `src/` (the whole package, not just one module). Run:

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90 --cov-report=term-missing
```

If coverage drops, do not delete tests to make the number work — fix the gap.
Live test count + current coverage percentage live in
[`docs/_generated/COUNTS.md`](../docs/_generated/COUNTS.md) — do not hardcode
either number in prose.

---

## Rule 3: The Thin Orchestrator Boundary — `scripts/` vs `src/`

**`src/bond_orchestrator/`** contains the mission logic: protocol, DAG
construction, phase-major execution, checkpointing, provenance, missions,
manuscript variables. No file I/O except inside the runner's checkpoint layer
and the provenance/manuscript-variables writers.

**`scripts/*.py`** contains glue: `sys.path` bootstrap + argv forwarding.
`scripts/run_mission.py` must not contain a single lifecycle call beyond
`bond_orchestrator.cli.main(sys.argv[1:])`.

**The boundary test**: if a line in `scripts/` determines mission semantics —
an execution order, a phase, a checkpoint decision, a verdict — it violates
the boundary. Move it to `src/` and write a test for it.

**Forbidden**:
```python
# In scripts/run_mission.py — BAD
for phase in ("brief", "recon", "plan", "execute", "debrief"):  # semantics in scripts/
    ...
```

**Correct**:
```python
# In scripts/run_mission.py — GOOD
raise SystemExit(main(sys.argv[1:]))  # main() lives in src/bond_orchestrator/cli.py
```

---

## Rule 4: "Show, Not Tell" Documentation

Use explicit, verifiable references instead of vague descriptions.

**BAD**: "The runner executes missions in order and supports resuming."

**GOOD**: "`src/bond_orchestrator/runner.py::MissionRunner.run` executes every
package through `PHASES` in `graph.topological_order()` order; completed steps
persist under `<checkpoint_dir>/<mission>/` and resume replays them via
`manifest.json`."

---

## Rule 5: Determinism Policy

Determinism is a hard contract, not a preference.

1. Providers must be pure with respect to their inputs. The reference
   providers (`src/bond_orchestrator/providers.py`) are fixed-spec classes —
   no RNG, no wall-clock, no hidden state.
2. Topological order must be canonical (id tie-break), so execution order is
   declaration-order independent.
3. Persisted artifacts (`report.json`, step files, `outcomes.json`,
   `provenance.csv`, `manuscript_variables.json`) are written with
   `sort_keys=True` — byte-stable for identical inputs. Two-run byte-equality
   tests enforce this boundary.
4. Wall-clock timing is a runtime-only diagnostic at most; it is never part
   of a persisted artifact.

---

## Rule 6: Do Not Move a Frozen Surface

Three surfaces cross package boundaries and are consumed by code you cannot
see from here. Changing any of them breaks siblings silently — nothing in this
package's gates will catch it.

1. **The five `MissionProvider` methods** and their signatures
   (`brief`/`recon`/`plan`/`execute`/`debrief`).
2. **`MissionPackage` and `MissionContext` field shapes** — `bond-cli`'s `run`
   command and `bond-coordinator` construct and read these directly.
3. **The frozen `bond_api` protocol** used in `film_providers.py`. It is owned
   by `bond-api` and implemented by 27 film packages. Adapt to it; never
   change it, and never change this package to require a change in it.

Additive change is fine: a new module, a new manuscript token, a new CLI flag
with a backwards-compatible default. Renaming or re-typing is a suite break.

Related hard constraint: **`bond_api` may be imported only inside
`film_providers.py`, and only inside a function body.** A module-scope import
passes ruff, mypy, and the full test suite while quietly making the pure core
un-importable wherever bond-api is absent. Check it explicitly:

```bash
grep -rnE "^(from|import) bond_api" src/bond_orchestrator/ || echo "Clean"
```

---

## Rule 7: Style and Syntax Guides Govern Their Domains

- [`style_guide.md`](style_guide.md) governs `src/`, `scripts/`, `tests/`:
  mock prohibition, pure-core boundary, thin orchestrator, type hints, error
  messages.
- [`manuscript/SYNTAX.md`](../manuscript/SYNTAX.md) governs
  `manuscript/*.md`: `{{TOKEN}}` injection, `[@key]` Pandoc citations. Do not
  apply code-style rules to manuscript prose or manuscript syntax to Python.

---

## Rule 8: `output/` Is Disposable — Never Edit Generated Files

The `output/` tree is written by the pipeline and overwritten on every run.
Editing a file in `output/` has zero lasting effect.

- `output/data/mission_report.json` → regenerate via
  `scripts/run_mission.py OPERATION_OMNIBUS`
- `output/data/provenance/*` → regenerate via the same
- `output/data/manuscript_variables.json` → regenerate via
  `scripts/generate_manuscript_variables.py`
- `output/state/<mission>/*` → checkpoint files; delete the state dir to
  force a fresh run

See [`output_conventions.md`](output_conventions.md) for the full
regeneration sequence.

---

## Verification Checklist

Run all of these before submitting any change:

```bash
# 0. Setup — the gate tools are not runtime deps; pytest/coverage live in the
#    `dev` extra, which uv does not install implicitly
uv sync --extra dev

# 1. Tests pass and coverage gate is met
uv run pytest tests/ --cov=src --cov-fail-under=90 -q

# 2. No mocks anywhere in tests/
grep -r "unittest.mock\|MagicMock\|@patch\|create_autospec" tests/ \
    || echo "Clean — no mocks found"

# 3. The pure core has no infrastructure imports
grep -rnE "^(from|import) infrastructure" src/bond_orchestrator/ \
    && echo "VIOLATION — pure core imports infrastructure" \
    || echo "Clean — pure core is infrastructure-free"

# 4. Packaging + forked-scaffold-lineage gates (declared-vs-imported runtime
#    dependencies, relative bond-api path, no exemplar slug in any declared
#    value or .py source). Replaces an `rg` one-liner that skipped dotfiles
#    and matched its own text, so it could never report Clean.
uv run pytest tests/test_packaging.py -q

# 5. No module-scope bond_api import (the pure core must stay liftable)
grep -rnE "^(from|import) bond_api" src/bond_orchestrator/ \
    && echo "VIOLATION — bond_api imported at module scope" \
    || echo "Clean — bond_api is lazy-imported only"

# 6. Lint, format, types (ruff/mypy are not declared deps — uvx runs them)
uvx ruff check src/ scripts/ tests/
uvx ruff format --check --line-length 120 src/ scripts/   # 120-col house rule
uvx mypy src/ scripts/
```

All six must produce zero violations (or the "Clean" message).

If you changed anything that affects a measured figure, re-run the gate and
update [`docs/_generated/COUNTS.md`](_generated/COUNTS.md) — and only that
file. If your change adds a quantitative claim to the manuscript, add the
token generator to `src/bond_orchestrator/manuscript_variables.py` and cite
the token; never write the number into prose.

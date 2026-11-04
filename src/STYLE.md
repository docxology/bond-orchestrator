# STYLE.md — src/bond_orchestrator code style contract

Applies to every module in `src/bond_orchestrator/` (and, by extension,
`scripts/` and `tests/`). Full prose rules: [`../docs/style_guide.md`](../docs/style_guide.md).

1. **Pure core** — no `infrastructure.*` imports, ever. Standalone-clean.
2. **Determinism** — canonical topological order (id tie-break); providers
   pure w.r.t. inputs; persisted artifacts `sort_keys=True`; no RNG, no
   wall-clock in any artifact.
3. **Type hints** — full annotations, PEP 585 generics,
   `from __future__ import annotations`; explicit `cast` at JSON boundaries.
4. **Docstrings** — module docstring (purpose + contracts), one-line or
   multi-line docstrings on all public functions/classes; Google-ish style.
5. **Error messages** — actionable, name the offending value and the options.
6. **Line length** — ≤120, the house rule, committed as `[tool.ruff]`
   `line-length = 120` in `pyproject.toml` (the vendoring commit adds that table
   for the `vendor/` exclusion and records the measured width beside it).
   `uvx ruff format --check --line-length 120 src/ scripts/` is clean — 21 files
   already formatted; with the width line removed the formatter's default
   reports 11 of them as unformatted, which is why the width is committed.
7. **I/O placement** — checkpoint layer in `runner.py`, records in
   `provenance.py`, token map in `manuscript_variables.py`, output
   persistence in `cli.py`; providers do no I/O.

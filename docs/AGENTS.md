# docs/ — Agent-Facing Documentation Hub

Technical rulebook for agents and developers working inside the
`bond-orchestrator` package (BOND-ORCHESTRATOR, codename
DAG 00). Every document is a constraint, not a suggestion.

## File Inventory

| File | Purpose |
|---|---|
| `README.md` | Quick navigation and audience-targeted entry points |
| `AGENTS.md` | This index — technical overview of `docs/` |
| `agent_instructions.md` | Behavioral constraints for AI agents (read-first priority) |
| `architecture.md` | Module inventory, composition order, DAG model, five-phase lifecycle, frozen `bond_api` binding, checkpoint schema, CLI surface, frozen surfaces |
| `protocol.md` | The MissionProvider protocol spec (canonical contract) |
| `testing_philosophy.md` | Zero-mock policy; coverage mechanics; per-file coverage map |
| `style_guide.md` | 7 rules: zero-mock, pure-core boundary, thin orchestrator, show-not-tell, explicit paths, type hints, error messages |
| `output_conventions.md` | `output/` layout and regeneration sequence |
| `_generated/COUNTS.md` | The single sanctioned home for measured numbers (tests, coverage split, lint/type results) |

## Reading Order

1. **`agent_instructions.md`** — 8 hard rules + verification checklist.
2. **`architecture.md`** — layer boundaries before touching files.
3. **`protocol.md`** — the provider contract before touching providers.
4. **`testing_philosophy.md`** — zero-mock constraint before writing tests.
5. **`style_guide.md`** — code style before writing source.
6. **`output_conventions.md`** — output layout before running scripts.

## Key Conventions

- **Pure-core isolation**: `src/bond_orchestrator/` is standalone-clean (no
  `infrastructure.*`). `bond_api` may be imported only inside
  `film_providers.py`, and only inside a function body — a module-scope import
  there would silently make the whole package un-liftable.
- **Frozen cross-package surfaces**: the five `MissionProvider` methods, the
  `MissionPackage`/`MissionContext` shapes, and the `bond_api` protocol are
  consumed by sibling packages. Additive change only.
- **Numbers live in one file**: measured counts and percentages belong in
  `_generated/COUNTS.md` and nowhere else; prose describes the gate.
- **Determinism is load-bearing**: canonical topological order, pure
  providers, `sort_keys=True` artifacts, and true byte-equality tests
  (`tests/test_determinism_bytes.py` — two independent runs into separate
  dirs, compared with `read_bytes()`, with a positive control).
- **Zero-mock enforcement**: no `unittest.mock`/`MagicMock`/`@patch`/
  `create_autospec` in `tests/`; deterministic fake providers implement the
  real protocol.
- **Thin scripts**: `scripts/` = `sys.path` bootstrap + argv forwarding.

## Verification Commands

```bash
uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90 -q   # gate: dev extra,
                                                                    # uv never installs it implicitly
grep -r "unittest.mock\|MagicMock\|@patch\|create_autospec" tests/ || echo "Clean"
grep -rnE "^(from|import) infrastructure" src/bond_orchestrator/ || echo "Clean"
# Packaging + forked-scaffold-lineage gates. This replaced an `rg` one-liner
# that could never print "Clean": rg skips dotfiles (so it missed the stale
# .template-export.json, now deleted) and the pattern matched its own text in
# this file. Scope is documented in the module docstring — declared values and
# .py sources only, not Markdown prose.
uv run --extra dev pytest tests/test_packaging.py -q
# ruff/mypy are not declared deps here — uvx is uv's isolated tool runner
uvx ruff check src/ scripts/
uvx mypy src/ scripts/
```

## REQUIRED vs CONVENTION

| Path | Status |
|---|---|
| `src/bond_orchestrator/*.py` | REQUIRED (coverage gate; all modules exercised) |
| `scripts/run_mission.py`, `scripts/generate_manuscript_variables.py` | REQUIRED (thin orchestrators; CLI path) |
| `scripts/vendor.py` | REQUIRED (recorded-copy checker; run by `tests/test_vendor_provenance.py`) |
| `vendor/bond-api/` | REQUIRED (recorded upstream copy of the `bond-api` protocol; `PROVENANCE.json` binds its bytes) |
| `tests/` (all `test_*.py`) | REQUIRED (90% line+branch gate) |
| `tests/conftest.py` | REQUIRED (path bootstrap + fixtures) |
| `manuscript/config.yaml` + `manuscript/*.md` | REQUIRED (token cross-ref test) |
| `docs/` prose files | Convention (keep accurate; they gate nothing automatically) |
| `output/` | Generated — never hand-edit |

# docs/ — Agent-Facing Documentation Hub

Technical rulebook for agents and developers working inside
`projects/working/bond/bond-orchestrator/` (BOND-ORCHESTRATOR, codename
DAG 00). Every document is a constraint, not a suggestion.

## File Inventory

| File | Purpose |
|---|---|
| `README.md` | Quick navigation and audience-targeted entry points |
| `AGENTS.md` | This index — technical overview of `docs/` |
| `agent_instructions.md` | Behavioral constraints for AI agents (read-first priority) |
| `architecture.md` | Layers, DAG model, five-phase lifecycle, checkpoint schema |
| `protocol.md` | The MissionProvider protocol spec (canonical contract) |
| `testing_philosophy.md` | Zero-mock policy; coverage mechanics; per-file coverage map |
| `style_guide.md` | 7 rules: zero-mock, pure-core boundary, thin orchestrator, show-not-tell, explicit paths, type hints, error messages |
| `output_conventions.md` | `output/` layout and regeneration sequence |

## Reading Order

1. **`agent_instructions.md`** — 7 hard rules + verification checklist.
2. **`architecture.md`** — layer boundaries before touching files.
3. **`protocol.md`** — the provider contract before touching providers.
4. **`testing_philosophy.md`** — zero-mock constraint before writing tests.
5. **`style_guide.md`** — code style before writing source.
6. **`output_conventions.md`** — output layout before running scripts.

## Key Conventions

- **Pure-core isolation**: `src/bond_orchestrator/` is standalone-clean (no
  `infrastructure.*`). This is the load-bearing property for the bond-api /
  bond-utilities integration points.
- **Determinism is load-bearing**: canonical topological order, pure
  providers, `sort_keys=True` artifacts, byte-equality tests.
- **Zero-mock enforcement**: no `unittest.mock`/`MagicMock`/`@patch`/
  `create_autospec` in `tests/`; deterministic fake providers implement the
  real protocol.
- **Thin scripts**: `scripts/` = `sys.path` bootstrap + argv forwarding.

## Verification Commands

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90 -q          # gate
grep -r "unittest.mock\|MagicMock\|@patch\|create_autospec" tests/ || echo "Clean"
grep -rnE "^(from|import) infrastructure" src/bond_orchestrator/ || echo "Clean"
rg -n "template_code_project" . --glob '!uv.lock' --glob '!.git/**' || echo "Clean"
uv run ruff check src/ scripts/
uv run mypy src/ scripts/
```

## REQUIRED vs CONVENTION

| Path | Status |
|---|---|
| `src/bond_orchestrator/*.py` | REQUIRED (coverage gate; all modules exercised) |
| `scripts/run_mission.py`, `scripts/generate_manuscript_variables.py` | REQUIRED (thin orchestrators; CLI path) |
| `tests/` (all `test_*.py`) | REQUIRED (90% line+branch gate) |
| `tests/conftest.py` | REQUIRED (path bootstrap + fixtures) |
| `manuscript/config.yaml` + `manuscript/*.md` | REQUIRED (token cross-ref test) |
| `docs/` prose files | Convention (keep accurate; they gate nothing automatically) |
| `output/` | Generated — never hand-edit |

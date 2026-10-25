# bond-orchestrator skill

Project-scoped skill for the BOND-suite package at
`projects/working/bond/bond-orchestrator/`. Load this when working inside the
project.

## When to Use

- Working inside `bond-orchestrator` — running missions, editing source,
  regenerating outputs.
- Extending the BOND suite: implementing `MissionProvider` in a film package
  or a sibling package.
- Validating that the package's contracts (pure core, thin scripts,
  zero-mock tests, determinism) still hold after changes.

## Quick Reference

```bash
# From the package directory
uv sync --extra dev                              # gate tools live in the `dev` extra
uv run pytest tests/ --cov=src --cov-fail-under=90
uv run python scripts/run_mission.py list
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state
uv run python scripts/generate_manuscript_variables.py
uvx ruff check src/ scripts/                     # ruff/mypy are not declared deps
uvx mypy src/ scripts/
```

## Pitfalls

- **Keep scripts thin.** Business logic (phases, order, checkpoints,
  verdicts) belongs in `src/bond_orchestrator/`, not in `scripts/`.
- **Pure core, no infrastructure.** `src/bond_orchestrator/` must never
  import `infrastructure.*`; the package runs standalone.
- **No mocks.** Tests use deterministic fake providers that implement the
  REAL `MissionProvider` protocol — real classes, no mock framework.
- **Determinism is load-bearing.** Canonical topological order, pure
  providers, `sort_keys=True` artifacts, byte-equality tests; no wall-clock
  or RNG in persisted artifacts.
- **Outputs are disposable.** Never hand-edit `output/`; regenerate from
  `scripts/`.
- **Checkpoint dirs resume by design.** Re-running with the same
  `--checkpoint-dir` replays completed steps; delete the state dir for a
  fresh run.

## Cross-refs

- Package contract: [`AGENTS.md`](../../../AGENTS.md)
- Protocol spec: [`docs/protocol.md`](../../../docs/protocol.md)
- TODO + integration points: [`TODO.md`](../../../TODO.md)
- Agent rules: [`docs/agent_instructions.md`](../../../docs/agent_instructions.md)

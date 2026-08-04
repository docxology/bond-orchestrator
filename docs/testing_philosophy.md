# Testing Philosophy — bond-orchestrator

## Zero-Mock Policy

All tests in this package use **real data and real computation**. The
"fake providers" in tests are real Python classes that implement the real
`MissionProvider` protocol with deterministic logic
(`tests/test_runner.py::TripwireProvider`, `RecordingProvider`,
`InterruptedNoTimeToDieProvider`, and the reference providers in
`src/bond_orchestrator/providers.py`) — they are not mocks, and no mock
framework is used anywhere:

```bash
grep -r "unittest.mock\|MagicMock\|@patch\|create_autospec" tests/ || echo "Clean"
```

Mocks are banned because they can pass while the actual orchestration logic is
wrong; deterministic providers exercise the real lifecycle, the real DAG
order, and the real checkpoint files.

## Coverage mechanics

- Gate: ≥90% line **and** branch coverage on `src/` (`pyproject.toml`:
  `fail_under = 90`, `branch = true`, `source = ["src"]`).
- Live counts live in `docs/_generated/COUNTS.md`; never hardcode test totals
  or coverage % in prose.
- `tests/` and `*/__init__.py` are omitted from coverage by config.
- Run: `uv run pytest tests/ --cov=src --cov-fail-under=90`.

## What each test file covers

| File | Coverage target |
|---|---|
| `test_protocol.py` | Protocol conformance (isinstance + lifecycle), dependency-edge citation, determinism of providers, registry lookups |
| `test_graph.py` | DAG construction, validation errors (self-dep, unknown node, cycle), canonical topological order, declaration-order independence |
| `test_runner.py` | Phase-major execution, DAG order, context feeding, consolidated debrief, runner errors, checkpoint/resume (replay + interrupt-continue), byte-equality across resume |
| `test_missions.py` | Canned mission shapes, registry, unknown-mission errors |
| `test_cli.py` | `list`/`run`, output artifacts (report + provenance), checkpoint-dir flag, exit codes, unknown-mission handling |
| `test_provenance.py` | Deterministic run id, record collection, JSON/CSV writing, byte-stability across runs |
| `test_manuscript_variables.py` | Config parsing, N/A fallbacks, strict-mode error, result-token resolution, live `{{TOKEN}}` cross-reference over manuscript sections |
| `test_integration.py` | End-to-end OPERATION OMNIBUS + OPERATION DIAMOND over real reference providers: DAG order, consolidated debrief, determinism, checkpoint/resume identity |

## Determinism in tests

- No RNG anywhere; no wall-clock assertions.
- Checkpoint/resume tests use `tmp_path` state dirs; two-run byte-equality
  (`report.as_dict() == resumed.as_dict()`) enforces the determinism boundary.
- The interrupt test (`InterruptedNoTimeToDieProvider`) simulates a mid-run
  crash with a real provider that raises, then proves resume executes exactly
  the remaining step (`RecordingProvider.calls`).

## Integration test requirement

The spec requires "a small integration test that operates on 2-3 REAL film
providers (deterministic fake providers implementing the REAL protocol),
asserting the DAG executes in order and checkpoint/resume resumes" —
`tests/test_integration.py` satisfies exactly this: OPERATION OMNIBUS across
goldfinger + goldeneye + no_time_to_die with dependency-order assertions and a
checkpoint/resume identity assertion.

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

### Why the stand-ins here are not mocks

The distinction matters enough to state precisely. A mock records expected
calls and replays canned answers, so the test asserts against the test's own
fiction. Every stand-in in this package instead **implements the protocol and
computes**:

| Stand-in | Where | What makes it real |
|---|---|---|
| `DeterministicProvider` subclasses | `src/bond_orchestrator/providers.py` | Fixed-spec classes running the full five-phase lifecycle, including reading dependency outputs out of the live `MissionContext` |
| `FlakyExecuteDecorator` | `tests/test_retry.py` | Wraps a *real* provider (reference or film adapter) and fails its first N `execute` calls by counting them — deterministic fault injection, then delegates to the real implementation |
| `TripwireProvider`, `RecordingProvider`, `InterruptedNoTimeToDieProvider` | `tests/test_runner.py` | Real providers that additionally record which steps ran, or raise mid-run to force a genuine interrupted-then-resumed execution |
| The malformed probe film | `tests/test_film_binding.py` | A real package tree on disk with a real `mission.py` that genuinely exposes no provider class, so bond-api's real discovery raises |
| The film packages themselves | `projects/working/bond/bond-<slug>` | Not stand-ins at all — `tests/test_film_binding.py` imports and runs the actual shipped films |

`pytest.MonkeyPatch` is not used anywhere; dependencies are injected instead
(the runner takes a providers mapping, the CLI takes `argv`, the variable
generator takes a project root).

## Coverage mechanics

- Gate: ≥90% line **and** branch coverage on `src/` (`pyproject.toml`:
  `fail_under = 90`, `branch = true`, `source = ["src"]`).
- Live counts live in `docs/_generated/COUNTS.md`; never hardcode test totals
  or coverage % in prose.
- `tests/` and `*/__init__.py` are omitted from coverage by config.
- Run: `uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90`.

## What each test file covers

| File | Coverage target |
|---|---|
| `test_protocol.py` | Protocol conformance (isinstance + lifecycle), dependency-edge citation, `MissionContext` readers (`has_recon`, `outputs_for` including its defensive copy), determinism of providers, registry lookups |
| `test_graph.py` | DAG construction, validation errors (self-dep, unknown node, cycle), canonical topological order, declaration-order independence, ordered cycle-path detection (`find_cycle`, `CycleError.cycle`) |
| `test_planning.py` | Parallel-stage plans: wavefront decomposition, parallelism/critical-path metrics, determinism, cycle rejection with path (both via `build_stage_plan` and directly against a hand-built cyclic `FilmGraph`, so the planner's own guard is exercised rather than shadowed by `build_film_graph`) |
| `test_retry.py` | `RetryPolicy` validation, `should_retry` gate, runner retry/recovery/exhaustion, retry persistence across checkpoint/resume, `FlakyExecuteDecorator` (real deterministic wrapper) |
| `test_runner.py` | Phase-major execution, DAG order, context feeding, consolidated debrief, runner errors, checkpoint/resume (replay + interrupt-continue), byte-equality across resume, loud rejection of an uncheckpointable payload, inert replay when no state dir is configured |
| `test_missions.py` | Canned mission shapes, registry, unknown-mission errors |
| `test_cli.py` | `list`/`run`/`plan`, output artifacts (report + provenance), checkpoint flag, retry flag, exit codes, unknown-mission handling, default-output-root resolution (package root, never the cwd) |
| `test_provenance.py` | Deterministic run id, record collection, JSON/CSV writing, byte-stability across runs |
| `test_manuscript_variables.py` | Config parsing, N/A fallbacks, strict-mode error, result-token resolution, stage/retry tokens, DAG hand-off tokens (populated, payload-free, and dependency-free missions), live `{{TOKEN}}` cross-reference over manuscript sections |
| `test_integration.py` | End-to-end OPERATION OMNIBUS + OPERATION DIAMOND over real reference providers: DAG order, consolidated debrief, determinism, checkpoint/resume identity |
| `test_film_binding.py` | REAL film packages (goldfinger/spectre/no_time_to_die + canonical OMNIBUS): adapter lifecycle, `load_mission_providers` whole-mission binding, strict failure on a missing package and on a present-but-undiscoverable one, citation suppression for an output-free dependency, real stage planning, real-film cycle detection, real-film retry |
| `test_scripts_smoke.py` | Thin-script subprocess smoke (list/run/plan, unknown-mission error, draft vars) |

## Determinism in tests

- No RNG anywhere; no wall-clock assertions.
- Checkpoint/resume tests use `tmp_path` state dirs; two-run byte-equality
  (`report.as_dict() == resumed.as_dict()`) enforces the determinism boundary.
- The interrupt test (`InterruptedNoTimeToDieProvider`) simulates a mid-run
  crash with a real provider that raises, then proves resume executes exactly
  the remaining step (`RecordingProvider.calls`).

## Coverage-gap discipline

The gate is a floor, not a target. Two rules keep it from going hollow:

1. **Never delete a test to move the number.** Fix the gap.
2. **An uncovered line is a question, not a nuisance.** Before adding a test,
   ask why nothing reached it. The Phase-5 pass found two answers worth
   keeping: `plan_stages`' cycle guard was unreachable through
   `build_stage_plan` (whose `build_film_graph` call raises first), and
   `load_mission_providers` — a public function `bond-cli` calls — had no test
   at all. Both were real gaps, not coverage theatre.

The residual uncovered *branches* are the `...` bodies of the
`MissionProvider` Protocol stubs and one fall-through in checkpoint replay;
these are structural, not logic gaps.

## Integration test requirement

The spec requires "a small integration test that operates on 2-3 REAL film
providers (deterministic fake providers implementing the REAL protocol),
asserting the DAG executes in order and checkpoint/resume resumes" —
`tests/test_integration.py` satisfies exactly this: OPERATION OMNIBUS across
goldfinger + goldeneye + no_time_to_die with dependency-order assertions and a
checkpoint/resume identity assertion.

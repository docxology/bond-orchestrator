# bond-orchestrator TODO

Forward-only backlog for **BOND-ORCHESTRATOR (DAG 00)** — Layer 3, the
multi-package mission DAG runner.

## Phase 1 — delivered

- Pure-core mission DAG runner over the `MissionProvider` protocol:
  `src/bond_orchestrator/{protocol,graph,runner,missions,providers,provenance,manuscript_variables,cli}.py`.
- Canned missions: OPERATION OMNIBUS (chain), OPERATION DIAMOND (diamond),
  OPERATION SINGLET.
- Checkpoint/resume: per-(phase, package) step files + manifest; resume
  replays completed steps and continues from the last completed step.
- Provenance (mission_io-equivalent): one record per executed step + debrief,
  deterministic run id, `outcomes.json` + `provenance.csv`.
- Manuscript identity BOND-ORCHESTRATOR / codename DAG 00; `{{TOKEN}}`
  hydration from `manuscript/config.yaml` + `output/data/mission_report.json`.
- Thin CLI + thin scripts; zero-mock deterministic test suite.

## Phase 2/3 — real-film binding (delivered by the fleet)

- `film_providers.py` — `FilmProviderAdapter` adapting real `bond-api`
  `MissionProvider` films to the orchestrator contract; `bond-api` is a local
  path dependency (lazy import keeps the pure core liftable).
- Real-film integration tests run the REAL goldfinger/spectre/no_time_to_die
  packages through the runner (DAG order, checkpoint/resume, provenance).

## Phase 4 — deep improvement (delivered this pass)

- **Ordered cycle-path detection** — `FilmGraph.find_cycle()` (deterministic
  DFS) returns the exact closed dependency path; `CycleError` carries it and
  the message names the loop (`goldeneye → goldfinger → goldeneye`).
- **Deterministic retry policy** — `src/bond_orchestrator/retry.py`:
  `RetryPolicy` (max attempts, retryable outcomes), `RetryRecord`, and the
  `should_retry` gate. The runner re-executes a failing `execute` step
  immediately (no wall-clock backoff — byte-determinism preserved), persists
  the attempt count in the checkpoint record, and reports `report.retries`.
- **Parallel-stage planning** — `src/bond_orchestrator/planning.py`: wavefront
  `StagePlan` (achievable parallelism + critical path), rendered by the new
  `plan <mission>` CLI command and carried in every `MissionReport`.
- New manuscript tokens: `CONFIG_RETRY_MAX_ATTEMPTS`, `RESULT_RETRY_COUNT`,
  `RESULT_NUM_STAGES`, `RESULT_MAX_PARALLELISM`, `RESULT_CRITICAL_PATH_LENGTH`,
  `RESULT_STAGE_PLAN`; `references.bib` gains Chandy & Lamport (1985) and
  Kwok & Ahmad (1999).
- Real-film tests cover the canonical OMNIBUS (goldfinger→goldeneye→
  no_time_to_die), real-film cycle detection, stage planning, and retry with a
  real film wrapped in a deterministic flaky decorator.

### Current validation evidence (measured 2026-08-04, phase 4)

- `uv run pytest tests/ --cov=src --cov-fail-under=90` → **131 passed**,
  0 skipped, 0 failed, **97.54%** line coverage on `src/` (floor 90%).
- `uv run ruff check src/ scripts/ tests/` + `ruff format` clean;
  `uv run mypy src/ scripts/` clean.
- `rg -n "template_code_project"` → only self-referential hits inside the
  verification-command docs (0 leftover scaffold strings in code/content).
- OPERATION OMNIBUS runs deterministically (byte-identical reports across
  fresh runs and across resume); retried steps persist and resume byte-stably;
  stage plans are canonical for a given package set.

## BOND-suite integration points

| # | Integration | Dependency | Status / acceptance criteria |
| --- | --- | --- | --- |
| 1 | Real film providers bound via `film_providers.py` adapter | `bond-api` (WIRED) | `load_film_providers(<slugs>, BOND)` runs real films; reference providers remain for the canned missions |
| 2 | `provenance.py` delegates to `mission_io` | `bond-utilities` (not yet) | Provenance records written via `bond_utilities.mission_io`; schema identical; tests green |
| 3 | Mission handoff | `bond-coordinator` (not yet) | Coordinator-produced mission objects (same `Mission` shape) execute unchanged |
| 4 | `protocol.py` re-uses the frozen `bond_api.MissionProvider` as the canonical contract | wired via the adapter | functional; no re-export refactor needed unless bond-api API changes |

Until un-wired dependencies land, this package runs on its own pure core — no
stalls.

## Backlog (ordered)

1. Add a `--list-providers` CLI view and provider/package coverage report
   (which film capabilities a mission exercises).
2. Parallel *execution* flag (`--parallel`): run independent packages per
   stage concurrently while preserving topological order; keep sequential as
   the default and keep byte-determinism tests green (the stage plan already
   makes this provably safe).
3. Optional wall-clock diagnostics (runtime-only, never persisted): phase
   durations per package.
4. `output/` regeneration script that runs mission → provenance → manuscript
   variables in one thin orchestrator (pipeline stage).
5. Mission manifest checksum: record config/registry hash in `manifest.json`
   and warn on resume when the mission definition changed.
6. Reference-provider coverage for the full BOND fleet once `bond-coordinator`
   declares the roster (currently 27 film packages; the canned missions bind
   the built reference set).

## Quality gates (never regress)

- ≥90% line+branch coverage on `src/` (`pyproject.toml` gate).
- Zero mocks in `tests/`; deterministic fake providers implement the REAL
  protocol.
- `ruff check` + `mypy` clean on `src/` and `scripts/`.
- Determinism: no wall-clock or RNG in any persisted artifact; two-run
  byte-equality tests enforce the boundary.
- Manuscript metrics injected via `{{TOKEN}}` only — never hand-authored.

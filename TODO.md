# bond-orchestrator TODO

Forward-only backlog for **BOND-ORCHESTRATOR (DAG 00)** — Layer 3, the
multi-package mission DAG runner.

## Phase 1 — delivered (this pass)

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
- Thin CLI + thin scripts; zero-mock deterministic test suite (73 tests).

### Current validation evidence (measured 2026-08-04)

- `uv run pytest tests/ --cov=src --cov-fail-under=90` → **77 passed**,
  **98.16%** line coverage on `src/` (floor 90%), branch ≥92%.
- `uv run ruff check src/ scripts/` clean; `uv run mypy src/ scripts/` clean.
- `rg -n "template_code_project"` → only self-referential hits inside the
  verification-command docs (0 leftover scaffold strings in code/content).
- OPERATION OMNIBUS runs deterministically; two fresh runs produce
  byte-identical reports/provenance; interrupted runs resume from the last
  completed step (enforced by tests).

## BOND-suite integration points (blocked on dependencies)

| # | Integration | Dependency | Acceptance criteria |
| --- | --- | --- | --- |
| 1 | `protocol.py` re-exports canonical `MissionProvider` | `bond-api` ships the contract | `from bond_api import MissionProvider` is the single source; orchestrator tests still green |
| 2 | `provenance.py` delegates to `mission_io` | `bond-utilities` ships `mission_io` | Provenance records written via `bond_utilities.mission_io`; schema identical; tests green |
| 3 | Real film providers bound by entry-point registry | film packages ship providers | `run_mission.py OPERATION_OMNIBUS` executes real provider logic; reference providers demoted to fixtures |
| 4 | Mission handoff | `bond-coordinator` ships mission specs | Coordinator-produced mission objects (same `Mission` shape) execute unchanged |

Until each lands, this package runs on its own pure core — no stalls.

## Backlog (ordered)

1. Add a `--list-providers` CLI view and provider/package coverage report
   (which film capabilities a mission exercises).
2. Parallel-safe execution flag (`--parallel`): run independent packages'
   phases concurrently while preserving topological order; keep sequential as
   the default and keep byte-determinism tests green.
3. Optional wall-clock diagnostics (runtime-only, never persisted): phase
   durations per package.
4. `output/` regeneration script that runs mission → provenance → manuscript
   variables in one thin orchestrator (pipeline stage).
5. Mission manifest checksum: record config/registry hash in
   `manifest.json` and warn on resume when the mission definition changed.
6. Extend the reference provider set to cover every film package in the BOND
   suite (casino_royale_1967 … you_only_live_twice) as canned reference
   missions, once `bond-coordinator` declares the fleet roster.

## Quality gates (never regress)

- ≥90% line+branch coverage on `src/` (`pyproject.toml` gate).
- Zero mocks in `tests/`; deterministic fake providers implement the REAL
  protocol.
- `ruff check` + `mypy` clean on `src/` and `scripts/`.
- Determinism: no wall-clock or RNG in any persisted artifact; two-run
  byte-equality tests enforce the boundary.
- Manuscript metrics injected via `{{TOKEN}}` only — never hand-authored.

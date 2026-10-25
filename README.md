# bond-orchestrator

**BOND-ORCHESTRATOR** — codename **DAG 00** — is the Layer 3 mission DAG
runner of the BOND suite. It executes multi-package film missions end-to-end
over the `MissionProvider` protocol:

```
brief() all → recon() (sequential + deterministic) → plan() → execute() → debrief() → consolidated report
```

with checkpoint/resume (intermediate reports persisted to a state dir),
deterministic retry policy, parallel-stage planning, and provenance
(written by an independent, deterministic provenance module) for every outcome.

## What it does

A mission is a DAG of film packages; a dependency edge exists exactly where
one film's recon outputs feed another film's recon
(`src/bond_orchestrator/graph.py`). The runner
(`src/bond_orchestrator/runner.py`) executes every package through the five
lifecycle phases in deterministic topological order, sharing one
`MissionContext` so downstream packages consume upstream recon outputs. The
result is a single consolidated debrief per mission, plus per-outcome
provenance records. Real film packages built to the frozen `bond-api`
protocol are bound through the adapter in `src/bond_orchestrator/film_providers.py`.

Six guarantees are enforced by construction:

- **Order** — canonical topological order (Kahn's algorithm, id tie-break);
  execution order never depends on declaration order.
- **Cycle detection** — a cyclic dependency graph is rejected with the exact
  ordered cycle path (`FilmGraph.find_cycle()`), before any provider runs.
- **Resumability** — every completed `(phase, package)` step persists to a
  checkpoint dir; re-running resumes from the last completed step and
  replays the rest (including retry attempt counts).
- **Retry policy** — a bounded, deterministic retry policy re-executes a
  failing `execute` step (immediate re-attempts, no wall-clock backoff) and
  records a `RetryRecord` per retried step.
- **Parallel-stage planning** — `src/bond_orchestrator/planning.py` computes
  the wavefront stages (what may run concurrently), achievable parallelism,
  and critical path length, rendered by the `plan` CLI command.
- **Provenance** — one `ProvenanceRecord` per executed plan step and per
  debrief, with a deterministic run id (`outcomes.json` + `provenance.csv`).

The execution core is pure logic with zero infrastructure imports; `bond-api`
is imported lazily only when real films are bound.

## Quick start

```bash
# From the package directory
uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90

# List canned missions
uv run python scripts/run_mission.py list

# Show a mission's parallel-stage plan
uv run python scripts/run_mission.py plan OPERATION_OMNIBUS

# Run the flagship mission end-to-end (with checkpoint/resume state dir)
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state

# Run with a retry policy (max 3 execute attempts per failing step)
uv run python scripts/run_mission.py OPERATION_OMNIBUS --retry-max-attempts 3

# Hydrate manuscript tokens from config.yaml + the mission report (strict)
uv run python scripts/generate_manuscript_variables.py
```

Output artifacts:

```
output/data/mission_report.json            # consolidated report
output/data/provenance/outcomes.json       # provenance records (JSON)
output/data/provenance/provenance.csv      # provenance records (CSV)
output/data/manuscript_variables.json      # {{TOKEN}} map for the manuscript
output/state/<mission>/                    # checkpoint step files + manifest
```

## Canned missions

| Mission | Shape | Packages |
|---|---|---|
| `OPERATION_OMNIBUS` | chain | goldfinger → goldeneye → no_time_to_die |
| `OPERATION_DIAMOND` | diamond (2 leaves → 1 join) | thunderball, from_russia_with_love → spectre |
| `OPERATION_SINGLET` | single package | goldfinger |

## Architecture

Every module in `src/bond_orchestrator/`, and what it computes:

| Module | What it does |
|---|---|
| `protocol.py` | The runner-side mission data model (`Mission`, `MissionPackage`, `MissionContext`, `BriefRecord`, `ReconReport`, `Plan`/`PlanStep`, `ExecutionResult`, `Debrief`) and the `MissionProvider` Protocol. Frozen dataclasses with `as_dict()` for byte-stable serialization. |
| `graph.py` | Builds the film DAG from `depends_on`, validates it (self-dependency, unknown node, acyclicity), computes the canonical topological order (Kahn's algorithm, sorted worklist), and recovers the ordered cycle path via DFS. |
| `planning.py` | Wavefront decomposition of the DAG into parallel stages; achievable parallelism (widest stage) and critical path (stage count). |
| `retry.py` | The bounded, backoff-free retry policy (`RetryPolicy`, `RetryRecord`) and the `should_retry` decision function. Self-validating construction. |
| `runner.py` | Phase-major, package-minor execution over the topological order; the shared `MissionContext`; checkpoint/resume (manifest + per-step files + report); retry application; `MissionReport` and the consolidated debrief. |
| `missions.py` | The canned mission registry — the three DAG shapes this package ships. |
| `providers.py` | Deterministic reference providers: real classes implementing the real protocol with fixed specs. Used by the canned missions and the pure-core tests. |
| `film_providers.py` | The adapter edge — binds REAL film packages written against the frozen `bond_api.MissionProvider` to the runner-side contract. Strict discovery; `bond_api` imported lazily. |
| `provenance.py` | One `ProvenanceRecord` per executed step and per debrief; deterministic run id; `outcomes.json` + `provenance.csv` + full-report writers. |
| `manuscript_variables.py` | The `{{TOKEN}}` map: identity/parameters from `manuscript/config.yaml` plus measured results (order, steps, verdicts, retries, stage plan, DAG hand-off edges) from the mission report. |
| `cli.py` | Argument parsing and dispatch only: `run`, `plan`, `list`, plus the exit-code rule. |

```
scripts/
├── run_mission.py                    # thin wrapper → bond_orchestrator.cli.main
└── generate_manuscript_variables.py  # thin wrapper → generate_variables
```

Full module-by-module detail, the composition order of one run, and the
frozen-surface list: [`docs/architecture.md`](docs/architecture.md).

Layer contract: the pure core (`protocol/graph/planning/retry/runner/missions/
providers/provenance/manuscript_variables`) never imports `infrastructure.*` or
`bond-api` (standalone-liftable); `bond-api` is imported lazily inside
`film_providers.py` only when real films are bound; `scripts/` are thin
wrappers; tests use real deterministic providers implementing the real
protocol — no mocks anywhere.

## Protocol contract

Every film provider implements `MissionProvider` (`src/bond_orchestrator/protocol.py`):

```python
class MissionProvider(Protocol):
    name: str
    def brief(self, package: MissionPackage) -> str: ...
    def recon(self, package: MissionPackage, context: MissionContext) -> ReconReport: ...
    def plan(self, package: MissionPackage, context: MissionContext) -> Plan: ...
    def execute(self, package, plan: Plan, context: MissionContext) -> tuple[ExecutionResult, ...]: ...
    def debrief(self, package, context: MissionContext, plan: Plan,
                results: tuple[ExecutionResult, ...]) -> Debrief: ...
```

Full contract documentation: [`docs/protocol.md`](docs/protocol.md).

### Binding a real film package

Film packages implement the **frozen** `bond_api` protocol in their own
`src/<slug>/mission.py` — narrower signatures (`recon(ReconRequest)`,
`plan(MissionBrief)`, `execute(MissionPlan)`, `debrief(MissionOutcome)`) that
carry no DAG concepts at all. `film_providers.py` adapts between the two:

```python
from pathlib import Path
from bond_orchestrator import MissionRunner, load_film_providers, load_mission_providers

BOND = Path("projects/working/bond")

# Bind a slug list …
adapters = load_film_providers(("goldfinger", "goldeneye", "no_time_to_die"), BOND)
# … or every package a Mission declares:
adapters = load_mission_providers(my_mission, BOND)

report = MissionRunner(adapters).run(my_mission)
```

The adapter folds each dependency's recon `outputs` into the goal text the
film's `recon` receives, and turns the film's `Finding` list back into
`outputs` for downstream edges — so a DAG-unaware film participates in the
DAG. Binding is strict: a missing or undiscoverable film raises
`FilmProviderError` rather than being skipped. `bond_api` is imported lazily,
so the pure core still runs where bond-api is not installed.

## Verification

Three gates, all runnable from this directory. Coverage must stay at or above
the `pyproject.toml` floor of 90% line+branch on `src/`; the *measured* figures
live in [`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md) and are
deliberately not quoted here, so this file cannot go stale.

```bash
# Setup — the gate tools are not runtime deps: pytest/coverage live in the `dev`
# optional-dependency extra. uv never installs extras implicitly, and a bare
# `uv run` re-syncs them away, so each gate command asks for the extra itself.
uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90

# ruff and mypy are not declared in this package's pyproject.toml — run them via
# uvx. No ruff config is committed here, so the 120-column house rule
# (src/STYLE.md rule 6) has to be passed to the formatter explicitly.
uvx ruff check src/ scripts/ tests/
uvx ruff format --check --line-length 120 src/ scripts/
uvx mypy src/
```

## Documentation

- [`AGENTS.md`](AGENTS.md) — package contract, layer rules, verification
- [`docs/README.md`](docs/README.md) — the docs hub index
- [`docs/agent_instructions.md`](docs/agent_instructions.md) — agent rules (read first)
- [`docs/architecture.md`](docs/architecture.md) — module inventory, composition order, frozen `bond_api` binding, checkpoint schema, CLI
- [`docs/protocol.md`](docs/protocol.md) — the MissionProvider protocol spec
- [`docs/testing_philosophy.md`](docs/testing_philosophy.md) — zero-mock policy, what the stand-ins are, coverage mechanics
- [`docs/style_guide.md`](docs/style_guide.md) — the seven code/doc style rules
- [`docs/output_conventions.md`](docs/output_conventions.md) — `output/` layout and regeneration
- [`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md) — measured counts, coverage split, lint/type results
- [`TODO.md`](TODO.md) — forward backlog + BOND-suite integration points
- [`manuscript/`](manuscript/) — publication manuscript (identity: BOND-ORCHESTRATOR, codename DAG 00)

## License

MIT — see [`LICENSE`](LICENSE).

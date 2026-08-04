# bond-orchestrator

**BOND-ORCHESTRATOR** — codename **DAG 00** — is the Layer 3 mission DAG
runner of the BOND suite. It executes multi-package film missions end-to-end
over the `MissionProvider` protocol:

```
brief() all → recon() (sequential + deterministic) → plan() → execute() → debrief() → consolidated report
```

with checkpoint/resume (intermediate reports persisted to a state dir) and
provenance (mission_io-equivalent) written for every outcome.

## What it does

A mission is a DAG of film packages; a dependency edge exists exactly where
one film's recon outputs feed another film's recon
(`src/bond_orchestrator/graph.py`). The runner
(`src/bond_orchestrator/runner.py`) executes every package through the five
lifecycle phases in deterministic topological order, sharing one
`MissionContext` so downstream packages consume upstream recon outputs. The
result is a single consolidated debrief per mission, plus per-outcome
provenance records.

Three guarantees are enforced by construction:

- **Order** — canonical topological order (Kahn's algorithm, id tie-break);
  execution order never depends on declaration order.
- **Resumability** — every completed `(phase, package)` step persists to a
  checkpoint dir; re-running resumes from the last completed step and
  replays the rest.
- **Provenance** — one `ProvenanceRecord` per executed plan step and per
  debrief, with a deterministic run id (`outcomes.json` + `provenance.csv`).

The execution core is pure logic with zero infrastructure imports; the whole
package runs standalone with only `pyyaml` as a runtime dependency.

## Quick start

```bash
# From the package directory
uv run pytest tests/ --cov=src --cov-fail-under=90

# List canned missions
uv run python scripts/run_mission.py list

# Run the flagship mission end-to-end (with checkpoint/resume state dir)
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state

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

```
src/bond_orchestrator/
├── protocol.py            # MissionProvider protocol + mission data model (pure)
├── graph.py               # film DAG construction + deterministic topo sort (pure)
├── runner.py              # phase-major executor + checkpoint/resume (pure core)
├── missions.py            # canned missions: OMNIBUS / DIAMOND / SINGLET (pure)
├── providers.py           # deterministic reference providers (real protocol impls)
├── provenance.py          # mission_io-equivalent outcome records (pure)
├── manuscript_variables.py# {{TOKEN}} hydration from config.yaml + mission report
└── cli.py                 # thin CLI: `run <mission> [--checkpoint-dir]`, `list`
scripts/
├── run_mission.py         # thin wrapper → bond_orchestrator.cli.main
└── generate_manuscript_variables.py  # thin wrapper → generate_variables
```

Layer contract: `src/bond_orchestrator/` never imports `infrastructure.*`
(standalone-clean); `scripts/` are thin wrappers; tests use real deterministic
providers implementing the real protocol — no mocks anywhere.

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

## Documentation

- [`AGENTS.md`](AGENTS.md) — package contract, layer rules, verification
- [`docs/agent_instructions.md`](docs/agent_instructions.md) — agent rules (read first)
- [`docs/architecture.md`](docs/architecture.md) — layers, DAG model, checkpoint schema
- [`docs/protocol.md`](docs/protocol.md) — the MissionProvider protocol spec
- [`docs/testing_philosophy.md`](docs/testing_philosophy.md) — zero-mock policy, coverage mechanics
- [`TODO.md`](TODO.md) — forward backlog + BOND-suite integration points
- [`manuscript/`](manuscript/) — publication manuscript (identity: BOND-ORCHESTRATOR, codename DAG 00)

## License

MIT — see [`LICENSE`](LICENSE).

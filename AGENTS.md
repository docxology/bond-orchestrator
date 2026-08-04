# BOND-ORCHESTRATOR — AGENTS.md

**BOND-ORCHESTRATOR (codename DAG 00)** — Layer 3 of the BOND suite: the
mission DAG runner. Executes multi-package film missions end-to-end over the
`MissionProvider` protocol, with checkpoint/resume and provenance on every
outcome. This is an active BOND phase-1 package under
`projects/working/bond/bond-orchestrator/`.

## Layer contract

| Surface | Rule |
| --- | --- |
| `src/bond_orchestrator/protocol.py`, `graph.py`, `runner.py`, `missions.py`, `providers.py`, `provenance.py`, `manuscript_variables.py` | Pure core — **no** `infrastructure.*` imports, standalone-clean |
| `scripts/` | Thin orchestrators (sys.path bootstrap + argv forwarding only) |
| `tests/` | Real data + real computation; deterministic providers implementing the REAL protocol; **no mocks** |
| Live counts | Link `docs/_generated/COUNTS.md`; do not hardcode measured test totals or coverage % |

Enforced by: `pyproject.toml` coverage gate (≥90% line+branch on `src/`),
`manuscript/layer_contract.yaml`, and the verification commands below.

## Overview

A mission is a DAG of film packages: dependency edges exist exactly where one
film's recon outputs feed another film's recon. The runner executes every
package through the five lifecycle phases (`brief`, `recon`, `plan`,
`execute`, `debrief`) in deterministic topological order, accumulating a
shared `MissionContext`, and produces a single consolidated debrief plus
per-outcome provenance records.

## Key features

- **Deterministic DAG execution** — canonical topological order (Kahn's
  algorithm, sorted ready-worklist); declaration-order independent.
- **Checkpoint/resume** — every completed `(phase, package)` step persisted to
  `<checkpoint-dir>/<mission>/`; resume replays completed steps and continues
  from the last completed step; `report.json` persisted at completion.
- **Provenance** — one `ProvenanceRecord` per executed step and per debrief
  (mission_io-equivalent; `outcomes.json` + `provenance.csv`, deterministic
  run id).
- **Canned missions** — OPERATION OMNIBUS (chain), OPERATION DIAMOND
  (diamond), OPERATION SINGLET; `run <mission> [--checkpoint-dir]`, `list`.
- **Manuscript variable hydration** — identity/mission parameters from
  `manuscript/config.yaml` + measured results from
  `output/data/mission_report.json`; prose never hand-authors metrics.
- **Zero-mock testing** — deterministic reference providers
  (`src/bond_orchestrator/providers.py`) implement the real protocol.

## Directory structure

```mermaid
flowchart TB
    P[projects/working/bond/bond-orchestrator]
    P --> SRC[src/bond_orchestrator<br/>Pure core · protocol/graph/runner/missions/providers/provenance]
    P --> SC[scripts<br/>run_mission.py · generate_manuscript_variables.py]
    P --> T[tests<br/>77 tests · no mocks · 98% coverage]
    P --> DOCS[docs<br/>agent_instructions · architecture · protocol · testing_philosophy]
    P --> M[manuscript<br/>config.yaml · 00_abstract..99_references · SYNTAX.md]
    P --> OUT[output<br/>mission_report.json · provenance/ · state/ · manuscript_variables.json]
    P --> PY[pyproject.toml<br/>pytest/coverage config · ≥90% gate]
    P --> DP[domain_profile.yaml · experiment_plan.yaml · data/claim_ledger.yaml]
```

## Usage

```bash
# From the package directory (canonical gates)
uv run pytest tests/ --cov=src --cov-fail-under=90

# CLI
uv run python scripts/run_mission.py list
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state

# Manuscript token hydration (strict by default)
uv run python scripts/generate_manuscript_variables.py
uv run python scripts/generate_manuscript_variables.py --allow-draft   # N/A fallbacks
```

### Python API

```python
from bond_orchestrator import OPERATION_OMNIBUS, MissionRunner, get_provider

providers = {pid: get_provider(pid) for pid in OPERATION_OMNIBUS.package_ids()}
report = MissionRunner(providers, checkpoint_dir="output/state").run(OPERATION_OMNIBUS)
print(report.consolidated_debrief())   # single debrief
```

## Protocol for AI agents

- Start with `docs/agent_instructions.md` (all modifications).
- Consult `docs/architecture.md` before altering `src/` boundaries or adding
  modules.
- Consult `docs/testing_philosophy.md` before writing/modifying pytest files.
- Consult `docs/protocol.md` before changing the `MissionProvider` contract.

## Testing

```bash
uv run pytest tests/ -v
uv run pytest tests/ --cov=src --cov-fail-under=90 --cov-report=term-missing
```

Live test count + measured coverage: `docs/_generated/COUNTS.md`.

## BOND-suite integration (wired in commit 728d8f3)

| Dependency | Status | What changed |
| --- | --- | --- |
| `bond-api` (frozen `MissionProvider`) | **wired** | `film_providers.py` adapts real bond-api providers to the runner contract; `bond-api` is a local path dependency (imported lazily so the pure core stays liftable) |
| `bond-utilities` (`mission_io`) | declared | `provenance.py` may delegate to it; `mission_io.record_provenance_outcome` is the shared provenance helper |
| film packages (27) | **wired** | `film_providers.load_film_providers`/`load_mission_providers` discover real films from `src/` and bind them; `providers.py` reference classes remain for pure tests |

Real-film missions (e.g. goldfinger → goldeneye → no_time_to_die) run through
`MissionRunner` with checkpoint/resume + provenance; see `tests/test_film_binding.py`.

Residual acceptance criteria live in [`TODO.md`](TODO.md).

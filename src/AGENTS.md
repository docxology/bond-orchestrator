# src/bond_orchestrator/ — Pure Core

## Overview

`src/bond_orchestrator/` is the importable mission logic of the package: the
`MissionProvider` protocol, film-DAG construction, deterministic phase-major
execution with checkpoint/resume, provenance recording, canned missions, the
deterministic reference providers, manuscript-variable hydration, and the thin
CLI. **No module imports `infrastructure.*`** — the whole tree is
standalone-clean (stdlib + pyyaml), which is what makes the bond-api /
bond-utilities integration points trivial.

## Module map

| Module | Responsibility |
|---|---|
| `protocol.py` | `MissionProvider` protocol + frozen mission data model (`Mission`, `MissionPackage`, `ReconReport`, `MissionContext`, `Plan`, `ExecutionResult`, `Debrief`) |
| `graph.py` | `build_film_graph` + `FilmGraph` (validation, canonical topological order, ordered cycle-path detection via `find_cycle`) |
| `planning.py` | `plan_stages` + `StagePlan`/`Stage` (wavefront parallel-stage planning: parallelism + critical path) |
| `retry.py` | `RetryPolicy`, `RetryRecord`, `should_retry` (deterministic bounded retry, no wall-clock backoff) |
| `runner.py` | `MissionRunner`, `MissionReport`, `PHASES`, checkpoint/resume state layer, execute-phase retry, stage plan attachment |
| `missions.py` | Registry: OPERATION OMNIBUS / DIAMOND / SINGLET, `get_mission` |
| `providers.py` | `DeterministicProvider` base + reference film providers |
| `film_providers.py` | `FilmProviderAdapter` binding real `bond-api` film providers (lazy import) |
| `provenance.py` | independent deterministic writer: `ProvenanceRecord`, `write_outcome_records`, `write_mission_report` |
| `manuscript_variables.py` | `generate_variables()` — `{{TOKEN}}` map from config.yaml + mission report |
| `cli.py` | argparse CLI: `run <mission> [--checkpoint-dir] [--output-dir] [--retry-max-attempts]`, `plan <mission>`, `list` |
| `__init__.py` | Public re-exports; identity BOND-ORCHESTRATOR / codename DAG 00 |

## Boundary rules

- Pure logic, no infrastructure imports, no hidden I/O.
- I/O is confined to: runner checkpoint layer, `provenance.py`,
  `manuscript_variables.py`, `cli.py` (output persistence).
- Providers are pure with respect to their inputs; determinism is a hard
  contract (canonical topo order, `sort_keys=True` artifacts, no RNG/wall-clock).
- Type hints + docstrings everywhere; `ruff` + `mypy` clean.

## Usage

```python
from bond_orchestrator import OPERATION_OMNIBUS, MissionRunner, get_provider

providers = {pid: get_provider(pid) for pid in OPERATION_OMNIBUS.package_ids()}
report = MissionRunner(providers, checkpoint_dir="output/state").run(OPERATION_OMNIBUS)
print(report.consolidated_debrief())
```

See [`STYLE.md`](STYLE.md) for the code style contract.

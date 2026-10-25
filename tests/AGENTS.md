# tests/ — Test Suite

## Overview

Tests for the bond-orchestrator mission DAG runner: protocol conformance,
DAG construction/order, phase-major execution, checkpoint/resume,
provenance, missions registry, CLI, and manuscript-variable hydration —
all with real data and real computation. **Zero mocks.**

## Key Concepts

- **Deterministic fake providers implement the REAL protocol**: real Python
  classes (`DeterministicProvider` subclasses and test-local providers like
  `TripwireProvider`, `RecordingProvider`,
  `InterruptedNoTimeToDieProvider`) — not mocks.
- **Byte-determinism**: two-run equality on `report.as_dict()`, checkpoint
  step files, and provenance records.
- **Real files**: checkpoint/resume tested through real state dirs
  (`tmp_path`); CLI tested through real output dirs.

## Files

| File | Coverage target |
|---|---|
| `conftest.py` | Path bootstrap + fixtures (project_root, reference providers, runners, missions) |
| `test_protocol.py` | Protocol conformance, dependency-edge citations, provider determinism, registry |
| `test_graph.py` | DAG build/validate, topological order, declaration-order independence, ordered cycle-path detection |
| `test_planning.py` | Parallel-stage plans: metrics, determinism, cycle rejection |
| `test_retry.py` | RetryPolicy validation, `should_retry`, runner retry/recovery/exhaustion, retry persistence across resume, flaky decorator |
| `test_runner.py` | Phase-major execution, context feeding, debrief, errors, checkpoint/resume, byte-equality |
| `test_missions.py` | Canned mission shapes + registry errors |
| `test_cli.py` | list/run/plan, artifacts, checkpoint flag, retry flag, exit codes |
| `test_provenance.py` | run id determinism, record collection, JSON/CSV output, byte-stability |
| `test_manuscript_variables.py` | token map, fallbacks, strict mode, stage/retry tokens, live cross-reference |
| `test_integration.py` | End-to-end OMNIBUS/DIAMOND over real reference providers; DAG order; checkpoint/resume identity |
| `test_film_binding.py` | Real film binding: adapter lifecycle, real OMNIBUS, real stage plan, real cycle detection, real-film retry |
| `test_scripts_smoke.py` | Thin-script subprocess smoke (list/run/plan, unknown mission) |

## Commands

```bash
uv run --extra dev pytest tests/ -v
uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90 --cov-report=term-missing
```

Live test count + measured coverage: [`../docs/_generated/COUNTS.md`](../docs/_generated/COUNTS.md).

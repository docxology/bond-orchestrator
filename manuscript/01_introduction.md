# Introduction

The BOND suite splits multi-package research-and-response operations into
six cooperating packages: `bond-utilities` (shared mission I/O and
provenance), `bond-api` (the `MissionProvider` contract), `bond-coordinator`
(fleet-level planning), `bond-orchestrator` (this package — Layer 3, the DAG
runner), `bond-cli`, and `bond-ops`. Each film package (GOLDFINGER,
GOLDENEYE, NO TIME TO DIE, ...) is itself a self-contained mission capability
that implements the provider protocol.

This package, **BOND-ORCHESTRATOR** (codename **DAG 00**), is responsible for
one thing: running a mission across N providers end-to-end and reporting a
single consolidated debrief. It does not implement any film's business logic —
that belongs to the providers — and it does not decide which missions exist —
that belongs to the mission registry in
`src/bond_orchestrator/missions.py`. It only guarantees *order*, *resumability*,
and *provenance*.

The guarantees are enforced by construction:

- **Order** — `src/bond_orchestrator/graph.py` builds the film DAG from
  `depends_on` edges and computes a canonical topological order (Kahn's
  algorithm with id tie-breaking), so execution order never depends on
  declaration order or dictionary iteration.
- **Resumability** — `src/bond_orchestrator/runner.py` persists every
  completed `(phase, package)` step to a state directory and replays it on
  resume, continuing from the last completed step.
- **Provenance** — `src/bond_orchestrator/provenance.py` writes one
  provenance record per executed plan step and per debrief, with a
  deterministic run id.
- **Bounded recovery** — `src/bond_orchestrator/retry.py` re-executes a
  failing `execute` step a bounded number of times, immediately and without
  wall-clock backoff, so recovery never costs determinism.
- **Explicit concurrency** — `src/bond_orchestrator/planning.py` decomposes
  the DAG into the wavefront stages a parallel executor could run, reporting
  achievable parallelism and critical path without changing the sequential
  execution contract.
- **Real-film binding** — `src/bond_orchestrator/film_providers.py` adapts
  packages written against the frozen `bond_api.MissionProvider` protocol to
  the runner-side contract, so the fleet's real films run under all of the
  above rather than a parallel code path.

Two of those deserve their negative statement up front, because they are what
the package deliberately does *not* do. It does not sleep between retries: a
wall-clock delay would leak a non-reproducible quantity into an artifact whose
byte-stability is the point. And it does not execute packages concurrently:
concurrency is emitted as a plan and verified as a property, not performed,
so that the guarantees above hold under a single, auditable execution order.

The reader's guide: §2 details the DAG model, the five-phase lifecycle, the
retry policy, stage planning, real-film binding, and provenance; §3 reports
the measured OPERATION OMNIBUS execution and the real-film runs; §4 states
what the design bought and what it deferred; §5 lists the configured mission
parameters and the mission shapes under test; §6 documents reproducibility;
§7 bounds the scope and places the work against prior art.

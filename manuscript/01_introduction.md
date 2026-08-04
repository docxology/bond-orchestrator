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

The reader's guide: §2 details the DAG model and the five-phase execution
lifecycle; §3 reports the measured OPERATION OMNIBUS execution; §5 lists the
configured mission parameters; §6 documents reproducibility.

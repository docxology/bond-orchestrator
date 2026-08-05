# Scope and Related Work

## 7.1 Scope

This package scopes to orchestration only:

- **In scope**: DAG construction and validation with ordered cycle-path
  detection, deterministic topological execution, checkpoint/resume,
  deterministic retry policy, parallel-stage planning, provenance recording,
  canned mission registry, real-film binding, thin CLI.
- **Out of scope**: film business logic (provider concern), mission *choice*
  (coordinator concern), protocol ownership (now `bond-api`'s — see §7.3),
  shared mission I/O once `bond-utilities.mission_io` is adopted (see
  `TODO.md`).

Parallel execution is deliberately deferred: the runner executes sequentially
because determinism and resumability are the load-bearing guarantees. The
stage planner (§2.5) makes the parallelism explicit without changing that
contract — every package in a stage may run concurrently, and the sequential
runner is the reference implementation of the same order.

## 7.2 Related work

Topological sorting of dependency graphs dates to Kahn's algorithm
[@kahn1962topological] and is standard material in algorithms texts
[@cormen2009introduction]. Long-running multi-stage workloads recover from
interruption through checkpoint/rollback-recovery protocols, surveyed in
[@elnozahy2002survey], with distributed snapshots for coordinated state
capture [@chandy1985distributed]; the runner's manifest + per-step state files
follow that pattern specialised for deterministic single-node execution.
Scheduling directed task graphs onto parallel machines by level-by-level
wavefront decomposition is a classic static-scheduling result
[@kwok1999static]; the orchestrator's stage plan is its deterministic,
single-machine specialization. Bounded re-execution of a failing step is
fault tolerance in the dependability sense — masking a transient fault so it
does not become a system failure, while letting a persistent one surface
[@avizienis2004basic]; here it is made deterministic by removing wall-clock
backoff entirely, trading throughput for byte-reproducible artifacts. The
binding between the runner-side contract and the frozen `bond_api` protocol is
a textbook object adapter [@gamma1994design]: neither interface may move, so a
translating wrapper is the only structure that preserves both.

## 7.3 Integration points

Wired (phases 2–3): real film packages built to the frozen `bond-api`
`MissionProvider` protocol are bound through the adapter in
`src/bond_orchestrator/film_providers.py` (`bond-api` is a local path
dependency, imported lazily so the pure core stays liftable without it).

Declared, not yet wired (each tracked with acceptance criteria in `TODO.md`):

- `bond-utilities.mission_io` provenance delegation — `provenance.py` is the
  drop-in equivalent and will delegate to it once it ships.
- `bond-coordinator` mission-spec handoff — coordinator-produced missions (same
  `Mission` shape) should execute unchanged.

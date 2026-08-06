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

- `bond-utilities.mission_io` provenance delegation — `provenance.py` is an
  independent, non-delegating provenance writer today, because its record
  schema differs from `mission_io`'s (key sets share only `codename` and
  `schema_version`). Delegation means writing a mapping and picking a canonical
  record shape first; see `TODO.md` V1/E6.
- `bond-coordinator` mission-spec handoff — coordinator-produced missions (same
  `Mission` shape) should execute unchanged.

## 7.4 Limitations and uncertainty

This section states, in one place, what the package does *not* claim. Each
bullet is grounded in the current code and tracked where it is ongoing work.

- **Provenance is not yet `mission_io`.** `provenance.py` is an independent,
  deterministic writer; its records are the orchestrator's own schema, not
  `bond-utilities.mission_io`'s, and no test compares the two key sets. Until
  the delegation (TODO E6) and its schema mapping (TODO V1) exist, cross-package
  provenance is stored in this package's format, not the suite's shared one.
- **One interpreter is exercised.** Every gate this package has run used a
  single CPython (3.14.6, recorded in `docs/_generated/COUNTS.md`); the
  declared `requires-python = ">=3.10"` floor has not been run on 3.10–3.13
  (TODO V2). The floor is a declaration, not a matrix.
- **Live counts are hand-maintained.** The measured test/coverage figures that
  §5.3 and §6 defer to live in `docs/_generated/COUNTS.md`, which no script
  regenerates (TODO V3). It is updated by hand on every pass and can silently
  go stale; the deferral chain is only as honest as that one leaf.
- **Resuming a changed mission requires a fresh checkpoint dir.** Checkpoint
  resume is bound to the exact mission definition by a recorded hash (TODO C1,
  §2.3): mutate a mission's `depends_on` or package set and the runner refuses
  to replay the old steps. This closes a stale-replay hole but makes an
  in-place, same-directory *edit-and-resume* workflow impossible by design —
  the safe workflow deletes or renames the state dir for a genuinely changed
  mission.
- **Real-film retry cannot rescue a deterministic film.** The adapter caches a
  film's `execute` outcome for the run (determinism safety), so a film that
  fails once yields the same failure on every bounded re-attempt (§2.6, §2.4).
  The retry mechanism therefore demonstrably recovers only *non-deterministic*
  or deliberately fault-injected providers — real films are exercised against
  it with a call-counting fault in `tests/test_film_binding.py`, not as a
  claim that it masks a persistent film bug.
- **Parallel execution is planned, not performed.** The stage plan (§2.5) is a
  scheduling artifact; the runner executes sequentially, so achievable
  concurrency is verified as a property, not delivered as speed. No parallel
  executor or wall-clock performance characterization exists (deliberately:
  wall-clock values would break byte-determinism).
- **Empty-plan packages pass vacuously.** A package whose provider returns an
  empty execution plan records zero execution steps and debriefs `pass`
  (there is nothing to fail). The runner now rejects an *empty mission* at
  graph build (§2.1) so the vacuum cannot hide a misbuilt mission, but a
  single empty-plan provider is still treated as a no-op success.
- **Determinism is single-node and single-interpreter.** Byte-reproducibility
  (§6.1) is demonstrated for fixed seeds and one interpreter on one machine;
  it does not by itself guarantee bit-identical output across Python versions
  or platforms, a question the single-interpreter gap above does not yet
  answer.

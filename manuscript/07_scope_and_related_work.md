# Scope and Related Work

## 7.1 Scope

This package scopes to orchestration only:

- **In scope**: DAG construction and validation, deterministic topological
  execution, checkpoint/resume, provenance recording, canned mission
  registry, thin CLI.
- **Out of scope**: film business logic (provider concern), mission *choice*
  (coordinator concern), protocol ownership once `bond-api` lands (see
  §7.3), shared mission I/O once `bond-utilities` lands (see `TODO.md`).

Parallel execution is deliberately deferred: the runner executes sequentially
because determinism and resumability are the Phase 1 guarantees. The DAG order
is what makes parallel execution safe in a later phase, since a consumer's
dependencies are always scheduled before it.

## 7.2 Related work

Topological sorting of dependency graphs dates to Kahn's algorithm
[@kahn1962topological] and is standard material in algorithms texts
[@cormen2009introduction]. Long-running multi-stage workloads recover from
interruption through checkpoint/rollback-recovery protocols, surveyed in
[@elnozahy2002survey]; the runner's manifest + per-step state files follow
that pattern specialised for deterministic single-node execution.

## 7.3 Integration points (declared, not yet wired)

- `bond-api` will own the canonical `MissionProvider` protocol; this package
  already implements against it and will re-export instead of defining.
- `bond-utilities` will ship `mission_io`; `provenance.py` is the drop-in
  equivalent and will delegate to it.
- Real film packages will ship their own providers; the reference providers in
  `src/bond_orchestrator/providers.py` will yield to an entry-point registry.

Each integration point is tracked with acceptance criteria in `TODO.md`.

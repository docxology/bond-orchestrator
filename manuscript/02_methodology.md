# Methodology

## 2.1 The mission DAG

A mission is an ordered collection of film packages
(`src/bond_orchestrator/protocol.py::Mission`). Each package declares
`depends_on`, the set of package ids whose recon outputs feed its own recon.
`build_film_graph()` (`src/bond_orchestrator/graph.py`) turns that declaration
into a directed acyclic graph with an edge `(upstream, downstream)` for every
dependency, validating that:

1. no package depends on itself,
2. every dependency names a package inside the mission,
3. the graph is acyclic.

Execution order is the **deterministic topological order** of the DAG: Kahn's
algorithm with a sorted ready-worklist, so the result is canonical for a given
set of packages regardless of declaration order [@kahn1962topological;
@cormen2009introduction]. The current flagship mission,
{{CONFIG_MISSION_NAME}}, declares {{CONFIG_NUM_PACKAGES}} packages and is
therefore executed in exactly one valid topological order.

**Cycle detection.** A mission whose dependencies close a loop is rejected
before any provider runs: `FilmGraph.find_cycle()` (`src/bond_orchestrator/graph.py`)
runs a depth-first search over sorted node ids and returns the *ordered cycle
path* (e.g. `("goldeneye", "goldfinger", "goldeneye")`); the raised
`CycleError` carries that path, so a miswired mission names its own loop
(goldfinger ↔ goldeneye) instead of a bare "cycle detected" message. The same
validation gates the stage planner (§2.5) and therefore the `plan` CLI
command.

## 2.2 The five-phase lifecycle

Every provider implements the `MissionProvider` protocol
(`src/bond_orchestrator/protocol.py`): **{{CONFIG_PHASES}}**. The runner
(`src/bond_orchestrator/runner.py::MissionRunner`) executes phase-major,
package-minor: for each phase, every package runs in topological order,
sharing one `MissionContext` that accumulates recon reports. A downstream
package's `recon` therefore reads its dependencies' `outputs` (the DAG edge
semantics), and `plan`/`execute`/`debrief` see the full recon picture.

Execution is sequential and deterministic; the topological order is exactly
what makes a later parallel implementation safe, because every dependency's
outputs are guaranteed present before a consumer runs (§2.5 makes that
parallelism explicit without changing the sequential contract).

## 2.3 Checkpoint / resume

When a `checkpoint_dir` is supplied, every completed `(phase, package)` step
is persisted as `<checkpoint_dir>/<mission>/<phase>_<package>.json` with a
`manifest.json` tracking completed steps in order. Re-running the same mission
with the same checkpoint dir replays completed steps (recon reports are
restored into the context so downstream steps see identical inputs) and
resumes from the last completed step. Execute steps additionally persist
their attempt count, so a retried step (§2.4) resumes with an identical retry
record. This follows the standard checkpoint/rollback-recovery pattern for
long-running distributed work [@elnozahy2002survey; @chandy1985distributed],
specialised here for deterministic single-node execution.

## 2.4 Retry policy

A `RetryPolicy` (`src/bond_orchestrator/retry.py`) bounds how many attempts a
failing `execute` step is given (default **{{CONFIG_RETRY_MAX_ATTEMPTS}}**
attempt in configuration; the CLI raises it via `--retry-max-attempts N`).
When any execution result carries a retryable outcome (`"failure"` by
default), the step is re-executed — immediately and deterministically, with
**no wall-clock backoff**, because a sleep would break the byte-determinism of
reports, checkpoint files, and provenance records. After `max_attempts` the
final outcome stands. This is fault *tolerance* in the standard sense — a
transient fault is masked before it becomes a mission failure, while a
persistent one is allowed to surface [@avizienis2004basic] — with the backoff
term removed because reproducibility outranks throughput here. Every step that
needed more than one attempt records a
`RetryRecord` (package, phase, attempts, succeeded) in the mission report and
in its checkpoint record; retries are thus observable, resumable, and
manuscript-token-able, while the consolidated debrief only annotates them when
they occurred.

## 2.5 Parallel-stage planning

`src/bond_orchestrator/planning.py` decomposes the film DAG into **parallel
stages** — the classic wavefront scheduling of directed task graphs
[@kwok1999static]. Stage 1 holds every package with no dependencies; stage
`k` holds every package whose dependencies all sit in stages `< k`; within a
stage, package ids are sorted, so the plan is canonical. The `StagePlan`
reports the achievable parallelism (widest stage) and the critical path
length (number of stages), and the `plan` CLI command renders it. Execution
itself remains sequential — the stages are the *planning artifact* that makes
a future parallel executor provably safe, since every package in a stage may
run concurrently without violating dependency order.

## 2.6 Real-film binding

The orchestrator's own protocol (§2.2) is the *runner-side* contract: it is
package-aware, because the runner must hand a `MissionPackage` and the shared
`MissionContext` to every call. The film packages of the BOND fleet implement
a different, deliberately narrower contract — the **frozen `bond_api`
`MissionProvider`**, whose methods take only a `ReconRequest`, a
`MissionPlan`, or a `MissionOutcome` and know nothing about DAGs. Neither
contract may move: the frozen protocol is consumed by 27 film packages, and
the runner-side shapes (`MissionPackage`, `MissionContext`) are consumed by
`bond-cli` and `bond-coordinator`.

`src/bond_orchestrator/film_providers.py` resolves that tension with an
adapter [@gamma1994design]. `FilmProviderAdapter` wraps one discovered
`bond_api` provider and presents the runner-side interface, translating in
both directions:

- **Down** — the DAG hand-off is folded into the film's own vocabulary. The
  adapter renders each `depends_on` dependency's recon `outputs` into the
  `ReconRequest.goal` text (`_citation_text`), so a film that has never heard
  of the DAG still receives its upstream intelligence; a dependency that
  produced no outputs contributes nothing rather than an empty citation.
- **Up** — the film's `Finding` list becomes the adapter's `ReconReport`:
  labels with detail become `outputs` (the downstream hand-off channel),
  every finding becomes a rendered `findings` entry, the film's plan steps are
  renumbered from 1, and the `MissionOutcome`'s numeric results become the
  `Debrief` metrics (booleans excluded — `bool` is an `int` in Python and
  would otherwise be reported as a measurement).

`load_film_providers(slugs, bond_root)` discovers each film from
`<bond_root>/<slug>/src` through `bond_api.discovery.load_provider` and is
**strict**: a missing package directory, an absent `mission.py`, or a
discovery failure raises `FilmProviderError` rather than dropping a package,
because a silently short mission would still report all-verdicts-pass.
`load_mission_providers(mission, bond_root)` binds every package a `Mission`
declares. `bond_api` is imported *lazily*, inside the methods that need it, so
the pure core of §2.1–§2.5 remains liftable into any environment where
bond-api is not installed.

## 2.7 Provenance

For every outcome — each executed plan step and each debrief — the runner
emits a `ProvenanceRecord` (`src/bond_orchestrator/provenance.py`) carrying a
deterministic run id (sha256 over mission name + package ids), the package and
provider, the phase, the outcome, artifact references, and numeric metrics.
Records are written as `outcomes.json` and a flat `provenance.csv`. This is
the mission_io-equivalent of `bond-utilities`; the integration point is
tracked in `TODO.md`.

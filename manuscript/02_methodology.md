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
outputs are guaranteed present before a consumer runs.

## 2.3 Checkpoint / resume

When a `checkpoint_dir` is supplied, every completed `(phase, package)` step
is persisted as `<checkpoint_dir>/<mission>/<phase>_<package>.json` with a
`manifest.json` tracking completed steps in order. Re-running the same mission
with the same checkpoint dir replays completed steps (recon reports are
restored into the context so downstream steps see identical inputs) and
resumes from the last completed step. This follows the standard
checkpoint/rollback-recovery pattern for long-running distributed work
[@elnozahy2002survey], specialised here for deterministic single-node
execution.

## 2.4 Provenance

For every outcome — each executed plan step and each debrief — the runner
emits a `ProvenanceRecord` (`src/bond_orchestrator/provenance.py`) carrying a
deterministic run id (sha256 over mission name + package ids), the package and
provider, the phase, the outcome, artifact references, and numeric metrics.
Records are written as `outcomes.json` and a flat `provenance.csv`. This is
the mission_io-equivalent of `bond-utilities`; the integration point is
tracked in `TODO.md`.

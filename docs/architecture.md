# Architecture — bond-orchestrator

## Layers and dependency direction

```
scripts/  (thin: sys.path bootstrap + argv forwarding)
   │  calls
   ▼
src/bond_orchestrator/  (pure core: protocol, graph, runner, missions,
   │                     providers, provenance, manuscript_variables, cli)
   │
   ▼
stdlib + pyyaml only — NO infrastructure.* imports, ever
```

The dependency arrow is one-directional: `scripts/` → `src/`; `tests/` →
`src/`. Nothing imports upward. The pure core is standalone-clean:
copy-pasteable into any Python environment (this is what makes the
bond-api/bond-utilities integration points trivial later).

## The mission DAG

A `Mission` (`src/bond_orchestrator/protocol.py`) is an ordered collection of
`MissionPackage`s. Each package declares `depends_on` — package ids whose
recon outputs feed its recon. `build_film_graph()`
(`src/bond_orchestrator/graph.py`) validates (no self-dependency, no unknown
nodes, acyclic) and produces a `FilmGraph`. Execution order is the
**deterministic topological order**: Kahn's algorithm with a sorted
ready-worklist, so the order is canonical for a given package set regardless
of declaration order.

**Cycle-path detection.** `FilmGraph.find_cycle()` runs a DFS over sorted ids
and returns the ordered closed dependency path (e.g.
`("goldeneye", "goldfinger", "goldeneye")`). A cyclic mission is rejected
*before any provider runs*; the raised `CycleError` carries the path so the
message names the loop.

## Parallel-stage planning (`src/bond_orchestrator/planning.py`)

`plan_stages(graph)` decomposes the DAG into wavefronts: stage 1 = packages
with no dependencies; stage `k` = packages whose deps all sit in stages `< k`
(packages sorted within a stage). `StagePlan` reports `max_parallelism()`
(widest stage) and `critical_path_length()` (stage count), rendered by the
`plan` CLI command and carried on every `MissionReport`. Planning does NOT
change execution (sequential by design) — it is the artifact that makes a
future parallel executor provably safe.

## Deterministic retry policy (`src/bond_orchestrator/retry.py`)

`RetryPolicy(max_attempts, retry_outcomes)` bounds how many times a failing
`execute` step is re-run. Retries are immediate — **no wall-clock backoff**,
so reports/checkpoints/provenance stay byte-deterministic. The runner
re-executes until success or `max_attempts`; the attempt count is persisted in
the checkpoint record, and steps needing >1 attempt record a `RetryRecord` in
the report.

## The five-phase lifecycle

`MissionRunner.run()` (`src/bond_orchestrator/runner.py`) executes
**phase-major, package-minor**:

```
for phase in (brief, recon, plan, execute, debrief):
    for package_id in graph.topological_order():
        run_step(phase, package_id)          # or replay from checkpoint
```

One `MissionContext` accumulates recon reports; a downstream package's `recon`
reads its dependencies' `outputs` (DAG edge semantics), and `plan` /
`execute` / `debrief` see the full recon picture. Execution is sequential and
deterministic; the topological order is what makes a later parallel
implementation safe.

The consolidated `MissionReport` carries every phase's records in topological
order plus `consolidated_debrief()` — the single debrief per mission.

## Checkpoint / resume schema

```
<checkpoint_dir>/<mission>/
├── manifest.json                     # {"mission": ..., "steps": [sorted step ids]}
├── <phase>_<package>.json            # {"step", "phase", "package", "payload": ...}
└── report.json                       # full MissionReport at completion
```

Execute step files additionally carry `"attempts": N` so a retried step
resumes with an identical `RetryRecord`. Resume: steps present in the manifest
are replayed from their step files (recon reports restored into the context),
then execution continues from the last completed step. Delete the state dir to
force a fresh run.

## Provenance

`src/bond_orchestrator/provenance.py` — one `ProvenanceRecord` per executed
plan step and per debrief: deterministic run id (sha256 over mission name +
package ids), orchestrator identity (BOND-ORCHESTRATOR / DAG 00), schema
version, package/provider/phase/outcome/detail, artifact refs, metrics.
Written as `outcomes.json` + flat `provenance.csv`. This is the
mission_io-equivalent until `bond-utilities` ships.

## Missions and providers

- `src/bond_orchestrator/missions.py` — the registry: OPERATION OMNIBUS
  (chain), OPERATION DIAMOND (diamond), OPERATION SINGLET.
- `src/bond_orchestrator/providers.py` — deterministic reference providers
  (real classes implementing the real protocol, fixed spec). Registry keys
  are package ids for the reference missions; real film packages will bind
  via an entry-point registry later.

## Manuscript variables

`src/bond_orchestrator/manuscript_variables.py::generate_variables()` reads
`manuscript/config.yaml` (identity + mission parameters) and, when present,
`output/data/mission_report.json` (measured results), producing the
`{{TOKEN}}` map. Strict mode raises when the report is absent; `--allow-draft`
uses `"N/A"` fallbacks. Prose never hand-authors metrics.

## CLI

`src/bond_orchestrator/cli.py` — `run <mission> [--checkpoint-dir DIR]
[--output-dir DIR]`, `list`. `run` persists `mission_report.json` +
provenance and prints the consolidated debrief; exit code 0 iff all verdicts
pass.

## Adding a new module

1. Pure logic belongs in `src/bond_orchestrator/` — no infrastructure
   imports, full type hints, docstrings.
2. I/O-bearing logic must go through the runner's checkpoint layer, the
   provenance writer, or the manuscript-variables writer — not raw I/O
   scattered in providers.
3. Scripts stay thin; test the new module with real deterministic providers;
   keep ≥90% line+branch coverage.
4. Update `docs/AGENTS.md` inventory, `README.md`, and `TODO.md` if the
   public surface changes.

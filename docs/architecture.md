# Architecture — bond-orchestrator

## Layers and dependency direction

```
scripts/  (thin: sys.path bootstrap + argv forwarding)
   │  calls
   ▼
src/bond_orchestrator/cli.py          (argparse only; delegates immediately)
   ▼
src/bond_orchestrator/  PURE CORE
   protocol · graph · planning · retry · runner · missions · providers ·
   provenance · manuscript_variables
   ▼
stdlib + pyyaml only — NO infrastructure.* imports, ever

src/bond_orchestrator/film_providers.py   ADAPTER EDGE
   the one module allowed to touch bond_api — and only via a LAZY import
   inside the function bodies, so the pure core above still imports and runs
   in an environment where bond-api is not installed.
```

The dependency arrow is one-directional: `scripts/` → `src/`; `tests/` →
`src/`. Nothing imports upward. The pure core is standalone-clean:
copy-pasteable into any Python environment.

## Module inventory

Every module in `src/bond_orchestrator/`, and what it actually computes:

| Module | Owns | Key surface |
|---|---|---|
| `protocol.py` | The runner-side mission data model and the `MissionProvider` Protocol. All records are frozen dataclasses with `as_dict()` for byte-stable serialization. | `Mission`, `MissionPackage`, `MissionContext`, `BriefRecord`, `ReconReport`, `Plan`/`PlanStep`, `ExecutionResult`, `Debrief`, `MissionProvider` |
| `graph.py` | DAG construction from `depends_on` edges; validation (self-dependency, unknown node, acyclicity); canonical topological order via Kahn's algorithm with a sorted ready-worklist; DFS cycle-path recovery over sorted ids. | `build_film_graph`, `FilmGraph.topological_order`, `FilmGraph.find_cycle`, `CycleError.cycle`, `UnknownNodeError` |
| `planning.py` | Wavefront decomposition of the DAG into stages; achievable parallelism (widest stage) and critical path (stage count). Guards cycles independently of `graph.py`. | `plan_stages`, `build_stage_plan`, `Stage`, `StagePlan.max_parallelism`, `StagePlan.critical_path_length`, `StagePlan.render` |
| `retry.py` | The bounded, backoff-free retry policy and its decision function. Validates its own arguments at construction (`max_attempts >= 1`, non-empty retry outcomes). | `RetryPolicy`, `RetryRecord`, `should_retry`, `DEFAULT_RETRY_OUTCOMES` |
| `runner.py` | Phase-major execution over the topological order; the shared `MissionContext`; the checkpoint/resume layer (manifest + per-step files + report); retry application; report assembly and the consolidated debrief. | `MissionRunner.run`, `MissionReport`, `PHASES`, `_RunState`, `ProviderNotFoundError`, `MissionError` |
| `missions.py` | The canned mission registry: the three DAG shapes the package ships. | `OPERATION_OMNIBUS`, `OPERATION_DIAMOND`, `OPERATION_SINGLET`, `get_mission`, `MISSION_NAMES` |
| `providers.py` | Deterministic reference providers — real classes implementing the real protocol with fixed specs, used by the canned missions and by tests. Not mocks: no framework, no recorded expectations, real lifecycle logic. | `DeterministicProvider`, six film-named subclasses, `REFERENCE_PROVIDERS`, `get_provider` |
| `film_providers.py` | The adapter edge: binds REAL film packages written against the frozen `bond_api.MissionProvider` to the runner-side contract. Strict discovery. | `FilmProviderAdapter`, `load_film_providers`, `load_mission_providers`, `FilmProviderError` |
| `provenance.py` | One record per executed step and per debrief; deterministic run id; JSON + flat CSV writers; the full-report writer. | `ProvenanceRecord`, `derive_run_id`, `collect_outcome_records`, `write_outcome_records`, `write_mission_report` |
| `manuscript_variables.py` | The `{{TOKEN}}` map: identity/mission parameters from `manuscript/config.yaml` plus measured results from `output/data/mission_report.json` (execution order, step count, verdicts, retries, stage plan, DAG hand-off edges). | `generate_variables`, `load_project_config`, `_stage_plan_tokens`, `_handoff_tokens` |
| `cli.py` | Argument parsing and command dispatch only — `run`, `plan`, `list` — plus the exit-code rule. | `build_parser`, `main`, `run_mission_command`, `plan_mission_command`, `list_missions_command`, `exit_code_for` |

## How the pieces compose

One mission run threads them in a fixed sequence:

```
missions.get_mission(name)            → Mission (packages + depends_on)
  └─ graph.build_film_graph(...)      → FilmGraph, validated acyclic
       └─ .topological_order()        → the execution order
  └─ planning.build_stage_plan(...)   → StagePlan (parallelism + critical path)
runner.MissionRunner(providers, checkpoint_dir, retry_policy).run(mission)
  └─ for phase in PHASES: for package in order: _RunState.run_step(...)
       ├─ providers.get_provider(id)  → a reference provider,   or
       │  film_providers.load_*       → a REAL film behind an adapter
       ├─ retry.should_retry(...)     → bounded re-execution of `execute`
       └─ checkpoint step file + manifest.json
  └─ MissionReport (+ consolidated_debrief, + stage_plan, + retries)
       ├─ provenance.write_mission_report / write_outcome_records
       └─ manuscript_variables.generate_variables → {{TOKEN}} map
```

`providers.py` and `film_providers.py` are interchangeable at the `run_step`
boundary — that is the whole point of the protocol. The runner never learns
which kind it is holding.

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
an independent provenance writer (delegation to `bond-utilities.mission_io` is pending).

## Missions and providers

- `src/bond_orchestrator/missions.py` — the registry: OPERATION OMNIBUS
  (chain), OPERATION DIAMOND (diamond), OPERATION SINGLET.
- `src/bond_orchestrator/providers.py` — deterministic reference providers
  (real classes implementing the real protocol, fixed spec), keyed by package
  id. These are what the canned missions and the pure-core tests run on.
- `src/bond_orchestrator/film_providers.py` — the REAL fleet binding (below).

## Real-film binding: the frozen `bond_api` protocol

There is no `mission.py` in this package — that file is the *film-side*
artifact. Each film package ships `src/<slug>/mission.py` exposing a
`MissionProvider` class implementing the **frozen** `bond_api` protocol
(`brief() -> MissionBrief`, `recon(ReconRequest) -> ReconReport`,
`plan(MissionBrief) -> MissionPlan`, `execute(MissionPlan) -> MissionOutcome`,
`debrief(MissionOutcome) -> Debrief`). Note what those signatures do *not*
carry: no `MissionPackage`, no `MissionContext` — a film knows nothing about
DAGs, and the frozen protocol may not be changed to teach it.

`FilmProviderAdapter` is the object adapter that reconciles the two contracts.
Both sides are load-bearing and immovable — 27 films consume the frozen
protocol; `bond-cli` and `bond-coordinator` consume the runner-side shapes —
so translation is the only structure available.

| Runner-side call | What the adapter does | Frozen-protocol call |
|---|---|---|
| `brief(package)` | Renders `codename: objective \| objective ...` from the film's own brief | `provider.brief()` (cached) |
| `recon(package, context)` | `_citation_text` folds every `depends_on` dependency's recon `outputs` into the goal text; a dependency with no outputs contributes nothing | `provider.recon(ReconRequest(goal=...))` |
| `plan(package, context)` | Renumbers the film's steps from 1; stringifies `step.params` into `detail` | `provider.plan(brief)` (cached) |
| `execute(package, plan, context)` | Fans the single `MissionOutcome` out to one `ExecutionResult` per plan step; `success` → `"success"` | `provider.execute(plan)` (cached) |
| `debrief(package, context, plan, results)` | Joins the film's `lessons` into an assessment; keeps only non-`bool` numeric results as metrics (`bool` is an `int` in Python and must not be reported as a measurement) | `provider.debrief(outcome)` |

Coming back the other way, the film's `Finding` list becomes the adapter's
`ReconReport`: findings with a `detail` also become `outputs`, which is what
downstream DAG edges read. That is how a film with no DAG awareness still
feeds one.

**Caching.** `_brief`/`_plan_for`/`_outcome_for` memoize per adapter instance
because the runner is phase-major: `plan`, `execute`, and `debrief` each need
the prior stage's object, and recomputing is only safe (and only cheap)
because the frozen protocol requires film providers to be deterministic.

**Strictness.** `load_film_providers(slugs, bond_root)` raises
`FilmProviderError` when a film directory or its `mission.py` is missing, and
translates `bond_api.discovery.DiscoveryError` into the same type. It never
skips a package — a silently short mission would still report
all-verdicts-pass, which is exactly the failure a strict loader exists to
prevent. `load_mission_providers(mission, bond_root)` binds every package a
`Mission` declares.

**Naming.** A film's two names differ, and `film_package_dir(bond_root, slug)`
is the one place that knows it: the **repository** directory carries the
`bond-` prefix (`<bond_root>/bond-goldfinger`) while the **package** inside its
`src/` keeps the bare slug (`src/goldfinger/mission.py`). The loader and the
film-binding gate both resolve through that helper, so they cannot disagree
about where a film lives; a bare `<slug>` directory is still accepted for a
checkout that stages the package without the prefix, and when neither is present
the error names the canonical `bond-<slug>` path. Before this helper existed the
slug was joined straight onto `bond_root`, which named a directory that has never
existed in the suite and made the gate report all four required films as absent.

**Laziness.** `from bond_api... import ...` appears only inside function
bodies. Importing `bond_orchestrator` never imports `bond_api`, so the pure
core stays liftable.

## Manuscript variables

`src/bond_orchestrator/manuscript_variables.py::generate_variables()` reads
`manuscript/config.yaml` (identity + mission parameters) and, when present,
`output/data/mission_report.json` (measured results), producing the
`{{TOKEN}}` map. Strict mode raises when the report is absent; `--allow-draft`
uses `"N/A"` fallbacks. Prose never hand-authors metrics.

Two helpers derive the harder tokens. `_stage_plan_tokens` reads the report's
`stage_plan` block into `RESULT_NUM_STAGES` / `RESULT_MAX_PARALLELISM` /
`RESULT_CRITICAL_PATH_LENGTH` / `RESULT_STAGE_PLAN`. `_handoff_tokens` joins
the report's `mission.packages[*].depends_on` against the recorded `recon`
outputs to render every DAG hand-off edge and its measured payload
(`RESULT_NUM_HANDOFF_EDGES`, `RESULT_HANDOFF_SUMMARY`) — this is what keeps
the edge evidence in §3 of the manuscript out of an author's hands.

`tests/test_manuscript_variables.py::TestLiveCrossReference` scans every
rendered manuscript section for `{{TOKEN}}` references and fails on any token
without a generator, so adding prose that cites a nonexistent token breaks the
suite rather than rendering a literal brace.

## CLI

`src/bond_orchestrator/cli.py` is argparse plus dispatch — no mission
semantics.

| Command | Arguments | Behaviour |
|---|---|---|
| `list` | — | Prints each canned mission and its package chain; exit 0 |
| `plan <mission>` | — | Prints the wavefront stage plan, achievable parallelism, and critical path; exit 0 |
| `run <mission>` | `--checkpoint-dir DIR`, `--output-dir DIR`, `--retry-max-attempts N` | Runs the mission over the reference providers, prints the consolidated debrief, writes `mission_report.json` + `provenance/`; exit 0 iff every verdict is `"pass"`, else 1 |

`--output-dir` defaults to `<package root>/output/data` (resolved by
`_project_root()` from the module's own location, never from the current
working directory). `--retry-max-attempts` defaults to 1, which means *no
retry* — a `RetryPolicy` is constructed only when the value exceeds 1.
An unknown mission name is reported through `parser.error` (exit 2), not a
traceback.

## Frozen surfaces — do not change

Three surfaces are consumed across package boundaries in the BOND suite and
must not be altered here:

1. **`MissionProvider`'s five methods** (`brief`/`recon`/`plan`/`execute`/
   `debrief`) and their signatures. Every provider and adapter depends on them.
2. **`MissionPackage` and `MissionContext` field shapes.** `bond-cli`'s `run`
   command and `bond-coordinator` construct and read these directly.
3. **The frozen `bond_api` protocol** consumed in `film_providers.py`. It is
   owned by `bond-api`, not by this package; adapt to it, never around it.

Additive change is fine (a new module, a new token, a new CLI flag with a
backwards-compatible default). Renaming or re-typing any of the above is a
suite-wide break.

## Adding a new module

1. Pure logic belongs in `src/bond_orchestrator/` — no infrastructure
   imports, full type hints, docstrings.
2. I/O-bearing logic must go through the runner's checkpoint layer, the
   provenance writer, or the manuscript-variables writer — not raw I/O
   scattered in providers.
3. `bond_api` may be imported **only** inside `film_providers.py`, **only**
   inside a function body. An import at module scope silently makes the pure
   core un-liftable and no existing test would catch it.
4. Scripts stay thin; test the new module with real deterministic providers;
   keep ≥90% line+branch coverage.
5. If the module contributes a manuscript number, add a token generator in
   `manuscript_variables.py` and cite the token — never write the number into
   prose.
6. Update the module inventory above, `docs/AGENTS.md`, `README.md`, and
   `TODO.md` if the public surface changes.

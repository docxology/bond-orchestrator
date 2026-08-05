# Results

## 3.1 OPERATION OMNIBUS execution

{{CONFIG_MISSION_NAME}} ran to completion over the deterministic reference
providers (`src/bond_orchestrator/providers.py`), which implement the real
`MissionProvider` protocol with fixed logic — no mocks, no random draws.

The execution order was:

```
{{RESULT_EXECUTION_ORDER}}
```

The mission executed **{{RESULT_NUM_STEPS}}** plan steps across all packages,
and the consolidated debrief closed with an all-verdicts outcome of
**{{RESULT_ALL_VERDICTS_PASS}}**.

Dependency-edge semantics were verified at recon time. The run carried
**{{RESULT_NUM_HANDOFF_EDGES}}** hand-off edges, each one an upstream
package's recorded recon `outputs` reaching its declared downstream consumer:

```
{{RESULT_HANDOFF_SUMMARY}}
```

Those payloads are read out of `output/data/mission_report.json` by
`src/bond_orchestrator/manuscript_variables.py::_handoff_tokens`, not typed
into this section, so the edge evidence cannot drift from the run that
produced it. The DAG's data hand-off therefore behaved exactly as specified
in §2.1.

## 3.2 Determinism and resumability

Two fresh runs of {{CONFIG_MISSION_NAME}} produced byte-identical
`MissionReport` serializations (`report.as_dict()`), identical checkpoint
step files, and identical provenance records. A run interrupted before the
final debrief resumed from the last completed step and produced a report
identical to a fresh run — the resumability contract of §2.3 holds.

## 3.3 Real-film binding

The same runner drives the REAL film packages through the adapter of §2.6:
`goldfinger`, `goldeneye`, `spectre`, and `no_time_to_die` are discovered from
their own `src/` trees as frozen `bond_api` providers and executed as a
mission. The canonical OPERATION OMNIBUS shape over real films runs in
dependency order, every verdict passes, and `goldeneye`'s recon carries a
citation of `goldfinger`'s outputs — the adapter's down-translation of the DAG
edge (§2.6) survives the round trip into a package that has no DAG concept.
Real films also exercise cycle rejection (a `goldfinger ↔ goldeneye` loop is
caught with its ordered path) and the retry policy (a real film wrapped in a
deterministic call-counting fault recovers within its attempt budget and
resumes byte-identically). These are `tests/test_film_binding.py`; they are
not fixtures standing in for films, they are the films.

## 3.4 Provenance

The run emitted one provenance record per executed step and per debrief
(`output/data/provenance/outcomes.json` + `provenance.csv`), every record
carrying the deterministic run id, package, provider, phase, outcome, and
numeric metrics.

## 3.5 Stage plan and retry outcome

{{CONFIG_MISSION_NAME}}'s wavefront decomposition (see §2.5) resolved into
**{{RESULT_NUM_STAGES}}** parallel stages with an achievable parallelism of
**{{RESULT_MAX_PARALLELISM}}** and a critical path of
**{{RESULT_CRITICAL_PATH_LENGTH}}** stages:

```
{{RESULT_STAGE_PLAN}}
```

Because the chain is serial, every stage is single-package: no concurrency is
available, and the critical path equals the package count — exactly the shape
a serial chain must have. The diamond-shaped OPERATION DIAMOND is the
contrasting case: its two dependency-free leaves share stage 1, so its
achievable parallelism exceeds one while its critical path is shorter than its
package count.

The run's retry ledger recorded **{{RESULT_RETRY_COUNT}}** retried steps under
the configured policy of **{{CONFIG_RETRY_MAX_ATTEMPTS}}** maximum attempts. A
retry record exists only when a transient failure was actually re-executed
(§2.4), so an empty ledger is evidence of a clean run rather than of a
disabled mechanism — the mechanism itself is exercised under deliberate
fault injection in §3.3.

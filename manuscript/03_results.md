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
**{{RESULT_ALL_VERDICTS_PASS}}**. Dependency-edge semantics were verified at
recon time: GOLDENEYE's recon cited GOLDFINGER's recon outputs
(`market_index=0.92`), and NO TIME TO DIE's recon cited GOLDENEYE's
(`emp_shield_rating=0.87`) — the DAG's data hand-off worked exactly as
specified in §2.1.

## 3.2 Determinism and resumability

Two fresh runs of {{CONFIG_MISSION_NAME}} produced byte-identical
`MissionReport` serializations (`report.as_dict()`), identical checkpoint
step files, and identical provenance records. A run interrupted before the
final debrief resumed from the last completed step and produced a report
identical to a fresh run — the resumability contract of §2.3 holds.

## 3.3 Provenance

The run emitted one provenance record per executed step and per debrief
(`output/data/provenance/outcomes.json` + `provenance.csv`), every record
carrying the deterministic run id, package, provider, phase, outcome, and
numeric metrics.

## 3.4 Stage plan and retry outcome

{{CONFIG_MISSION_NAME}}'s wavefront decomposition (see §2.5) resolved into
**{{RESULT_NUM_STAGES}}** parallel stages with an achievable parallelism of
**{{RESULT_MAX_PARALLELISM}}** and a critical path of
**{{RESULT_CRITICAL_PATH_LENGTH}}** stages:

```
{{RESULT_STAGE_PLAN}}
```

Because the chain is serial, every stage is single-package: no concurrency is
available, and the critical path equals the package count — exactly the shape
a serial chain must have.

The run's retry ledger recorded **{{RESULT_RETRY_COUNT}}** retried steps. With
the configured policy (max {{CONFIG_RETRY_MAX_ATTEMPTS}} attempt), no step
needed a re-execution; retry records exist only when a transient failure was
actually retried (§2.4).

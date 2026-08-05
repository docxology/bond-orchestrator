# The MissionProvider Protocol (bond-orchestrator canonical spec)

This is the **runner-side** provider contract — what `MissionRunner` calls.

Source of truth: `src/bond_orchestrator/protocol.py`.

## Two protocols, one adapter

Do not confuse this with the frozen `bond_api.MissionProvider` that the 27
film packages implement in their own `src/<slug>/mission.py`. They differ by
design:

| | Runner-side (this doc) | Frozen `bond_api` |
|---|---|---|
| `brief` | `brief(package) -> str` | `brief() -> MissionBrief` |
| `recon` | `recon(package, context) -> ReconReport` | `recon(ReconRequest) -> ReconReport` |
| `plan` | `plan(package, context) -> Plan` | `plan(MissionBrief) -> MissionPlan` |
| `execute` | `execute(package, plan, context) -> tuple[ExecutionResult, ...]` | `execute(MissionPlan) -> MissionOutcome` |
| `debrief` | `debrief(package, context, plan, results) -> Debrief` | `debrief(MissionOutcome) -> Debrief` |
| Knows about the DAG | Yes — every call carries `MissionPackage` + `MissionContext` | No — a film knows nothing about other films |

Both are frozen: the `bond_api` protocol is implemented by 27 films and owned
by `bond-api`; the runner-side shapes are consumed by `bond-cli` and
`bond-coordinator`. `src/bond_orchestrator/film_providers.py` translates
between them (see `docs/architecture.md`). Implement this contract when you
are writing an orchestrator-native provider; implement the frozen one when you
are writing a film.

## Data model

| Type | Fields | Notes |
|---|---|---|
| `MissionPackage` | `id`, `title`, `objective`, `depends_on: tuple[str, ...]` | `depends_on` = package ids whose recon outputs feed this package's recon |
| `Mission` | `name`, `packages: tuple[MissionPackage, ...]` | Declaration order; execution order comes from the DAG |
| `BriefRecord` | `provider`, `package_id`, `text` | Per-package briefing |
| `ReconReport` | `provider`, `package_id`, `findings`, `outputs: dict[str, str]` | `outputs` is the DAG hand-off channel |
| `MissionContext` | `recon_reports: dict[str, ReconReport]` | Populated in topological order; `outputs_for(package_id)` reads a dependency's outputs |
| `Plan` | `provider`, `package_id`, `steps: tuple[PlanStep, ...]` | `PlanStep`: `index`, `action`, `detail` |
| `ExecutionResult` | `provider`, `package_id`, `step_index`, `action`, `outcome`, `detail` | `outcome` ∈ `{"success", "failure"}` |
| `Debrief` | `provider`, `package_id`, `assessment`, `verdict`, `metrics: dict[str, float]` | `verdict` ∈ `{"pass", "fail", "conditional"}` |

All types are frozen dataclasses with `as_dict()` for byte-stable
serialization.

## The protocol

```python
@runtime_checkable
class MissionProvider(Protocol):
    name: str

    def brief(self, package: MissionPackage) -> str: ...
    def recon(self, package: MissionPackage, context: MissionContext) -> ReconReport: ...
    def plan(self, package: MissionPackage, context: MissionContext) -> Plan: ...
    def execute(self, package: MissionPackage, plan: Plan,
                context: MissionContext) -> tuple[ExecutionResult, ...]: ...
    def debrief(self, package: MissionPackage, context: MissionContext,
                plan: Plan, results: tuple[ExecutionResult, ...]) -> Debrief: ...
```

## Contract rules

1. **Determinism**: every method is pure with respect to its inputs. No RNG,
   no wall-clock, no hidden mutable state, no network. Identical inputs must
   produce identical outputs (byte-stable via `as_dict`).
2. **Recon reads dependencies**: when `package.depends_on` is non-empty, the
   `context` passed to `recon`/`plan`/`execute`/`debrief` contains recon
   reports for every dependency (the runner guarantees topological order).
   Read them via `context.outputs_for(dep_id)` — never assume a key exists;
   `outputs_for` returns `{}` when absent.
3. **Execute returns one result per plan step**; results are associated with
   the package by `package_id` and ordered by `step_index`.
4. **Debrief verdicts**: `"pass"` when the package succeeded, `"fail"`
   otherwise, `"conditional"` for qualified outcomes. `metrics` carries
   deterministic numeric evidence (floats only).
5. **No I/O**: providers must not write files or touch the network. All
   persistence is the runner's job (checkpoint layer, provenance writer).

## Conformance testing

`isinstance(provider, MissionProvider)` works at runtime
(`@runtime_checkable`). The test suite asserts protocol conformance and
determinism for every reference provider
(`tests/test_protocol.py::TestProtocolConformance`,
`tests/test_integration.py::TestProviderProtocolContract`).

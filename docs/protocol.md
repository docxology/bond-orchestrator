# The MissionProvider Protocol (bond-orchestrator canonical spec)

This is the protocol contract every film provider implements. It is the
orchestrator-side canonical definition; when `bond-api` ships its own
`MissionProvider` (see `TODO.md`), this package re-exports or mirrors that
contract so the rest of the package never changes.

Source of truth: `src/bond_orchestrator/protocol.py`.

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

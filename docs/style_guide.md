# Style Guide — bond-orchestrator

Seven rules. Rules 1–3 govern code; 4–5 govern documentation; 6–7 govern type
hints and error messages.

## Rule 1: Zero Mocks

Never use `unittest.mock`, `MagicMock`, `@patch`, or `create_autospec` in
`tests/`. Deterministic fake providers implement the real protocol with real
logic. The only "patching" ever permitted is `pytest.MonkeyPatch` on module
attributes, and it should be avoidable — prefer injectable dependencies
(runner takes a providers mapping, CLI takes argv).

## Rule 2: Pure Core Boundary

`src/bond_orchestrator/` never imports `infrastructure.*`. The package runs
standalone (stdlib + pyyaml). I/O is confined to the runner's checkpoint
layer, `provenance.py`, and `manuscript_variables.py`. Providers are pure with
respect to their inputs.

## Rule 3: Thin Orchestrator

`scripts/` contain only `sys.path` bootstrap + argv forwarding. Mission
semantics — order, phases, checkpoints, verdicts — live in `src/` and are
tested.

## Rule 4: Show, Not Tell

Reference exact modules/functions in prose: "`src/bond_orchestrator/runner.py::MissionRunner.run`
executes PHASES in topological order", not "the runner runs things in order".
Manuscript metrics come from `{{TOKEN}}` hydration — never hand-author numbers.

## Rule 5: Explicit Paths

Prefer `Path` objects and explicit relative paths over string concatenation.
Checkpoint/provenance/manuscript-variable writers own their path layouts;
callers pass directories, not file contents.

## Rule 6: Type Hints

Full type annotations on all public functions and methods; `dict[str, ...]`
/ `tuple[...]` generics (PEP 585); `from __future__ import annotations`.
`mypy` runs clean on `src/` and `scripts/`. JSON round-trips use explicit
`cast` at the boundary — no `Any` leakage into typed dataclasses.

## Rule 7: Error Messages

Actionable error messages that name the offending value and, where
applicable, the available options:

- `UnknownMissionError("unknown mission 'OPERATION_GHOST'; available: OPERATION_DIAMOND, OPERATION_OMNIBUS, OPERATION_SINGLET")`
- `ProviderNotFoundError("no provider registered for package 'goldeneye'")`
- `CycleError("cycle detected among packages: ['a', 'b']")`
- `FileNotFoundError("mission report missing at ...; run scripts/run_mission.py first (or pass --allow-draft)")`

Exceptions chain with `from` when re-raised.

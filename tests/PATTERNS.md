# Test Patterns — bond-orchestrator

Zero-mock patterns for exercising the mission runner with real classes.

## Pattern 1: Deterministic reference providers

`src/bond_orchestrator/providers.py::DeterministicProvider` is a real base
class: subclasses declare a fixed spec (findings, outputs, plan actions,
verdict, metrics) as class attributes; every lifecycle method is pure. Tests
use these directly or subclass them.

## Pattern 2: Tripwire providers (prove resume skips work)

A real provider whose lifecycle methods raise if invoked. Passing tripwire
providers to a resumed run proves that completed steps are replayed from
checkpoint files, not re-executed:

```python
class TripwireProvider(DeterministicProvider):
    name = "tripwire"
    def brief(self, package): raise AssertionError("brief called during resume")
    # ...same for recon/plan/execute/debrief
```

## Pattern 3: Recording providers (count executed steps)

A real provider that appends `"<phase>:<package_id>"` to an instance list
per lifecycle call. After a resumed run, empty call lists prove those steps
were replayed; a single `"debrief:no_time_to_die"` proves resume continued
from exactly the last completed step.

## Pattern 4: Interrupted providers (simulate mid-run crash)

Subclass a real reference provider and override one lifecycle method to
raise (e.g. `InterruptedNoTimeToDieProvider` crashes on debrief). Wrap the
first run in `pytest.raises`, then re-run with recording providers + the same
checkpoint dir.

## Pattern 5: Error-path assertions

`pytest.raises(ErrorType, match="...")` for graph validation errors, unknown
missions/providers, strict-mode manuscript variables, and runner errors.
`pytest.raises(SystemExit)` + `capsys` for CLI error paths.

## Rules

- No `unittest.mock` / `MagicMock` / `@patch` / `create_autospec` — ever.
- No RNG, no wall-clock assertions; determinism is asserted by byte-equality
  (`as_dict()` comparison) across runs.
- Prefer `tmp_path` real state/output dirs over in-memory stand-ins.

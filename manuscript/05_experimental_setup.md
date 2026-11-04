# Experimental Setup

## 5.1 Identity and configuration

This manuscript was produced for **{{CONFIG_TITLE}}**
({{CONFIG_SUBTITLE}}). The package identity is **{{CONFIG_IDENTITY}}**,
codename **{{CONFIG_CODENAME}}**, version **{{CONFIG_VERSION}}**, first author
{{CONFIG_FIRST_AUTHOR}}. All identity, publication, and mission parameters are
declared in `manuscript/config.yaml` and injected into this document through
the manuscript-variable pipeline (`scripts/generate_manuscript_variables.py`
→ `src/bond_orchestrator/manuscript_variables.py`; syntax reference in
`manuscript/SYNTAX.md`) — no metric is hand-authored in prose.

## 5.2 Mission parameters

| Parameter | Value |
|---|---|
| Mission name | `{{CONFIG_MISSION_NAME}}` |
| Package count | `{{CONFIG_NUM_PACKAGES}}` |
| Package chain | `{{CONFIG_PACKAGE_CHAIN}}` |
| Lifecycle phases | `{{CONFIG_PHASES}}` |
| Retry max attempts (configured) | `{{CONFIG_RETRY_MAX_ATTEMPTS}}` |

## 5.3 Software environment

- Python: the supported floor is `requires-python = ">=3.10"`
  (`pyproject.toml`). The interpreter each gate run actually used is recorded
  alongside the measured results in
  [`docs/_generated/COUNTS.md`](../docs/_generated/COUNTS.md) rather than
  asserted here, so this section cannot drift from the machine that ran it.
- `pytest` + `pytest-cov` for the enforced ≥90% line+branch coverage gate on
  `src/` (`pyproject.toml`: `fail_under = 90`, `branch = true`,
  `source = ["src"]`)
- `ruff` (lint + format check) and `mypy` clean on `src/` and `scripts/`
- Runtime dependencies of the pure core: the standard library plus `pyyaml`
  (config parsing only). `bond-api` is a declared path dependency (the recorded
  copy at `vendor/bond-api`), imported lazily and required only when real
  film packages are bound (§2.6). This sentence is enforced, not asserted:
  `tests/test_packaging.py` parses `pyproject.toml`, walks the import
  statements of `src/` and `scripts/` with the AST, and fails if a declared
  dependency is imported nowhere or an import is undeclared. Earlier revisions
  declared `numpy`, `matplotlib` and `defusedxml`, none of which this package
  imports; they were inherited from the exemplar it was forked from and have
  been removed.
- No external runtime services and no network access: the reference providers
  are in-process deterministic classes, and the real film packages are
  imported from their own `src/` trees.

## 5.4 Mission surface under test

Every number in this table is a token computed from the mission registry
(`src/bond_orchestrator/missions.py`) through the same
`build_stage_plan` the runner uses — see
`src/bond_orchestrator/manuscript_variables.py::_mission_surface_tokens`.
Earlier revisions typed these counts by hand, contradicting §5.1 four lines
above.

| Mission | Shape | Packages | Hand-off edges | Stages | Max parallelism | Critical path |
|---|---|---|---|---|---|---|
| `OPERATION_OMNIBUS` | serial chain | {{SURFACE_OPERATION_OMNIBUS_PACKAGES}} | {{SURFACE_OPERATION_OMNIBUS_HANDOFF_EDGES}} | {{SURFACE_OPERATION_OMNIBUS_STAGES}} | {{SURFACE_OPERATION_OMNIBUS_MAX_PARALLELISM}} | {{SURFACE_OPERATION_OMNIBUS_CRITICAL_PATH}} |
| `OPERATION_DIAMOND` | two leaves joining one sink | {{SURFACE_OPERATION_DIAMOND_PACKAGES}} | {{SURFACE_OPERATION_DIAMOND_HANDOFF_EDGES}} | {{SURFACE_OPERATION_DIAMOND_STAGES}} | {{SURFACE_OPERATION_DIAMOND_MAX_PARALLELISM}} | {{SURFACE_OPERATION_DIAMOND_CRITICAL_PATH}} |
| `OPERATION_SINGLET` | single package | {{SURFACE_OPERATION_SINGLET_PACKAGES}} | {{SURFACE_OPERATION_SINGLET_HANDOFF_EDGES}} | {{SURFACE_OPERATION_SINGLET_STAGES}} | {{SURFACE_OPERATION_SINGLET_MAX_PARALLELISM}} | {{SURFACE_OPERATION_SINGLET_CRITICAL_PATH}} |

- `OPERATION_OMNIBUS` is the flagship: a serial chain, so its critical path
  equals its package count and no concurrency is available.
- `OPERATION_DIAMOND` is the only shape whose achievable parallelism exceeds
  one; it exercises a multi-dependency join.
- `OPERATION_SINGLET` is the degenerate case, isolating retry and verdict
  behaviour from DAG effects.

The same three shapes are re-run over the REAL film packages through the
adapter of §2.6, so the DAG results are not an artifact of the reference
providers alone.

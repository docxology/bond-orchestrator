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
  (config parsing only). `bond-api` is a declared path dependency, imported
  lazily and required only when real film packages are bound (§2.6).
- No external runtime services and no network access: the reference providers
  are in-process deterministic classes, and the real film packages are
  imported from their own `src/` trees.

## 5.4 Mission surface under test

| Mission | Shape | Packages | Why it is in the suite |
|---|---|---|---|
| `OPERATION_OMNIBUS` | serial chain | 3 | The flagship; exercises two hand-off edges and a 3-stage critical path |
| `OPERATION_DIAMOND` | two leaves joining one sink | 3 | The only shape with achievable parallelism > 1; exercises a multi-dependency join |
| `OPERATION_SINGLET` | single package | 1 | Degenerate case; isolates retry and verdict behaviour from DAG effects |

The same three shapes are re-run over the REAL film packages through the
adapter of §2.6, so the DAG results are not an artifact of the reference
providers alone.

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

- Python >= 3.10 (developed and verified under Python 3.13)
- `pytest` + `pytest-cov` for the enforced ≥90% line+branch coverage gate on
  `src/` (`pyproject.toml`)
- `ruff` (lint/format) and `mypy` clean on `src/` and `scripts/`
- No external runtime services: the reference providers are in-process,
  deterministic classes

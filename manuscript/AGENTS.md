---
title: "Manuscript directory: bond-orchestrator"
type: "manuscript_guide"
version: "2.5.2"
---

# Manuscript (`manuscript/`)

Repository-wide agent rules live in [`../docs/agent_instructions.md`](../docs/agent_instructions.md).
This file covers **manuscript-specific** editing: file roles, `{{VARIABLE}}`
token protocol, and the section modification workflow.

## File Inventory

| File / Pattern | Role | `{{VARIABLE}}` Tokens |
|---|---|---|
| `00_abstract.md` | Abstract: identity, mission, measured outcome | `CONFIG_IDENTITY`, `CONFIG_CODENAME`, `CONFIG_MISSION_NAME`, `CONFIG_PACKAGE_CHAIN`, `RESULT_EXECUTION_ORDER`, `RESULT_ALL_VERDICTS_PASS` |
| `01_introduction.md` | BOND suite context, guarantees, reader's guide | None |
| `02_methodology.md` | §2.1 DAG model + cycle-path detection · §2.2 five-phase lifecycle · §2.3 checkpoint/resume · §2.4 retry policy · §2.5 parallel-stage planning · §2.6 real-film binding to the frozen `bond_api` protocol · §2.7 provenance | `CONFIG_MISSION_NAME`, `CONFIG_NUM_PACKAGES`, `CONFIG_PHASES`, `CONFIG_RETRY_MAX_ATTEMPTS` |
| `03_results.md` | §3.1 OMNIBUS execution + measured DAG hand-off edges · §3.2 determinism/resumability · §3.3 real-film runs · §3.4 provenance · §3.5 stage plan + retry ledger | `CONFIG_MISSION_NAME`, `CONFIG_RETRY_MAX_ATTEMPTS`, `RESULT_EXECUTION_ORDER`, `RESULT_NUM_STEPS`, `RESULT_ALL_VERDICTS_PASS`, `RESULT_NUM_HANDOFF_EDGES`, `RESULT_HANDOFF_SUMMARY`, `RESULT_RETRY_COUNT`, `RESULT_NUM_STAGES`, `RESULT_MAX_PARALLELISM`, `RESULT_CRITICAL_PATH_LENGTH`, `RESULT_STAGE_PLAN`, `RESULT_PACKAGE_RESULTS`, `RESULT_DAG_FIGURE` |
| `04_conclusion.md` | What the Layer 3 contract delivered, what real-film binding proved, and the two deliberate deferrals (no backoff, no parallel execution) | None |
| `05_experimental_setup.md` | §5.1 identity/config · §5.2 mission parameters · §5.3 software environment (interpreter recorded in `docs/_generated/COUNTS.md`, never asserted here) · §5.4 mission shapes under test | `CONFIG_TITLE`, `CONFIG_SUBTITLE`, `CONFIG_VERSION`, `CONFIG_IDENTITY`, `CONFIG_CODENAME`, `CONFIG_FIRST_AUTHOR`, `CONFIG_MISSION_NAME`, `CONFIG_NUM_PACKAGES`, `CONFIG_PACKAGE_CHAIN`, `CONFIG_PHASES`, `CONFIG_RETRY_MAX_ATTEMPTS` |
| `06_reproducibility.md` | Determinism policy, verification commands, artifact inventory | `CONFIG_MISSION_NAME`, `CONFIG_VERSION`, `CONFIG_FIRST_AUTHOR`, `RESULT_ALL_VERDICTS_PASS` |
| `07_scope_and_related_work.md` | Scope limits, related literature, integration points (wired vs declared) | None |
| `99_references.md` | Bibliography | None |
| `config.yaml` | Identity, paper metadata, publication, mission parameters | — |
| `config.yaml.example` | Reference copy for new projects | — |
| `preamble.md` | LaTeX injections shared by PDF output | — |
| `references.bib` | BibTeX bibliography — Kahn 1962, CLRS 2009, Elnozahy 2002, Chandy & Lamport 1985, Kwok & Ahmad 1999, Avižienis et al. 2004, Gamma et al. 1994, plus the software self-citation. Every entry is a real, verifiable publication with a DOI or ISBN; never add one you cannot check | — |
| `SYNTAX.md` | Citation + token reference (illustrative tokens excluded from the live cross-ref test) | — |
| `README.md` | Human quick-reference | — |
| `AGENTS.md` | This file | — |

## {{VARIABLE}} Protocol

Numeric/identity values from config or mission outputs **must** use
`{{VARIABLE_NAME}}` syntax. The token pipeline:

1. `scripts/run_mission.py OPERATION_OMNIBUS` → `output/data/mission_report.json`
2. `scripts/generate_manuscript_variables.py` → `generate_variables()` →
   `output/data/manuscript_variables.json`
3. Rendering substitutes `{{TOKEN}}` in manuscript templates

Adding a token: (1) add a key to `generate_variables()` in
`src/bond_orchestrator/manuscript_variables.py`; (2) the live cross-reference
test `tests/test_manuscript_variables.py::test_all_manuscript_tokens_are_generated`
enforces that every manuscript token is generated (SYNTAX.md excluded — it
illustrates with literal placeholders).

## Infrastructure Coupling

`src/bond_orchestrator/manuscript_variables.py` is the only manuscript-facing
source module and stays infrastructure-free (stdlib + pyyaml). Scripts under
`../scripts/` are thin wrappers.

## Section Modification Protocol

1. Change the generator first: `config.yaml` for config-derived tokens,
   `src/bond_orchestrator/*` for result-derived tokens.
2. Re-run `scripts/run_mission.py` + `scripts/generate_manuscript_variables.py`.
3. Update the token table above and `SYNTAX.md` when tokens change.
4. Run the manuscript-variables tests; never hand-author a metric in prose.

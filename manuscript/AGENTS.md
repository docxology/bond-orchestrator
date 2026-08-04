---
title: "Manuscript directory: bond-orchestrator"
type: "manuscript_guide"
version: "2.5.2"
---

# Manuscript (`projects/working/bond/bond-orchestrator/manuscript/`)

Repository-wide agent rules live in [`../docs/agent_instructions.md`](../docs/agent_instructions.md).
This file covers **manuscript-specific** editing: file roles, `{{VARIABLE}}`
token protocol, and the section modification workflow.

## File Inventory

| File / Pattern | Role | `{{VARIABLE}}` Tokens |
|---|---|---|
| `00_abstract.md` | Abstract: identity, mission, measured outcome | `CONFIG_IDENTITY`, `CONFIG_CODENAME`, `CONFIG_MISSION_NAME`, `CONFIG_PACKAGE_CHAIN`, `RESULT_EXECUTION_ORDER`, `RESULT_ALL_VERDICTS_PASS` |
| `01_introduction.md` | BOND suite context, guarantees, reader's guide | None |
| `02_methodology.md` | DAG model, topological order, five-phase lifecycle, checkpoint/resume, provenance | `CONFIG_MISSION_NAME`, `CONFIG_NUM_PACKAGES`, `CONFIG_PHASES` |
| `03_results.md` | OPERATION OMNIBUS execution results | `CONFIG_MISSION_NAME`, `RESULT_EXECUTION_ORDER`, `RESULT_NUM_STEPS`, `RESULT_ALL_VERDICTS_PASS` |
| `04_conclusion.md` | Summary of the Layer 3 contract | None |
| `05_experimental_setup.md` | Identity/config parameters, mission table, software environment | `CONFIG_TITLE`, `CONFIG_SUBTITLE`, `CONFIG_VERSION`, `CONFIG_IDENTITY`, `CONFIG_CODENAME`, `CONFIG_FIRST_AUTHOR`, `CONFIG_MISSION_NAME`, `CONFIG_NUM_PACKAGES`, `CONFIG_PACKAGE_CHAIN`, `CONFIG_PHASES` |
| `06_reproducibility.md` | Determinism policy, verification commands, artifact inventory | `CONFIG_MISSION_NAME`, `CONFIG_VERSION`, `CONFIG_FIRST_AUTHOR`, `RESULT_ALL_VERDICTS_PASS` |
| `07_scope_and_related_work.md` | Scope limits, related literature, integration points | None |
| `99_references.md` | Bibliography | None |
| `config.yaml` | Identity, paper metadata, publication, mission parameters | — |
| `config.yaml.example` | Reference copy for new projects | — |
| `preamble.md` | LaTeX injections shared by PDF output | — |
| `references.bib` | BibTeX bibliography (Kahn 1962, CLRS 2009, Elnozahy 2002, self) | — |
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

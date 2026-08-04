# Manuscript Syntax Reference (bond-orchestrator)

Project-specific overlay for manuscript editing. Repository-wide semantics:
`docs/guides/manuscript-semantics.md` (template root). This file documents the
**bond-orchestrator** `{{TOKEN}}` table and citation syntax.

## Citation Syntax (Pandoc)

```markdown
<!-- Single citation -->
[@kahn1962topological]

<!-- Multiple citations -->
[@kahn1962topological; @cormen2009introduction]

<!-- Narrative citation -->
@kahn1962topological showed that topological sorting scales to large networks.
```

All citation keys must exist in [`references.bib`](references.bib). Pandoc
with `--citeproc`/`--natbib` converts `[@key]` to the right LaTeX cite
command; **never** write raw `\cite{}` in Markdown.

## {{VARIABLE}} Token Protocol

Numeric/identity values **must** use `{{TOKEN}}` syntax — never hand-author
metrics in prose. The token pipeline:

1. `scripts/run_mission.py OPERATION_OMNIBUS` writes
   `output/data/mission_report.json` + provenance.
2. `scripts/generate_manuscript_variables.py` calls
   `src/bond_orchestrator/manuscript_variables.py::generate_variables()`,
   which reads `manuscript/config.yaml` + the mission report and writes the
   full `{TOKEN: value}` map to `output/data/manuscript_variables.json`.
3. Rendering substitutes every `{{TOKEN}}` in the manuscript templates.

Strict mode (default) fails when the mission report is absent; `--allow-draft`
uses `"N/A"` fallbacks for `RESULT_*` tokens.

### Live token table (authoritative source: `generate_variables()`)

| Token | Meaning | Source |
|---|---|---|
| `CONFIG_TITLE` | Paper title | `config.yaml` → `paper.title` |
| `CONFIG_SUBTITLE` | Paper subtitle | `config.yaml` → `paper.subtitle` |
| `CONFIG_VERSION` | Package version | `config.yaml` → `paper.version` |
| `CONFIG_IDENTITY` | Package identity | `config.yaml` → `identity.name` |
| `CONFIG_CODENAME` | Codename (DAG 00) | `config.yaml` → `identity.codename` |
| `CONFIG_FIRST_AUTHOR` | First author name | `config.yaml` → `authors[0].name` |
| `CONFIG_MISSION_NAME` | Mission name | `config.yaml` → `mission.name` |
| `CONFIG_NUM_PACKAGES` | Package count | `config.yaml` → `mission.packages` |
| `CONFIG_PACKAGE_CHAIN` | Package chain (→) | `config.yaml` → `mission.packages` |
| `CONFIG_PHASES` | Lifecycle phases | `src/bond_orchestrator/runner.py::PHASES` |
| `CONFIG_RETRY_MAX_ATTEMPTS` | Configured retry policy | `config.yaml` → `mission.retry.max_attempts` |
| `RESULT_EXECUTION_ORDER` | Measured order (→) | `output/data/mission_report.json` → `order` |
| `RESULT_NUM_STEPS` | Executed plan steps | `output/data/mission_report.json` → `executions` |
| `RESULT_ALL_VERDICTS_PASS` | PASS/FAIL | `output/data/mission_report.json` → `debriefs` |
| `RESULT_RETRY_COUNT` | Retried steps | `output/data/mission_report.json` → `retries` |
| `RESULT_NUM_STAGES` | Parallel stages | `.../mission_report.json` → `stage_plan` |
| `RESULT_MAX_PARALLELISM` | Widest stage | `.../mission_report.json` → `stage_plan` |
| `RESULT_CRITICAL_PATH_LENGTH` | Stage count | `.../mission_report.json` → `stage_plan` |
| `RESULT_STAGE_PLAN` | Stage plan (index: pkgs...) | `.../mission_report.json` → `stage_plan` |

The live cross-reference test
(`tests/test_manuscript_variables.py::test_all_manuscript_tokens_are_generated`)
fails automatically if a manuscript token has no generator. To add a token:
add a key to `generate_variables()`, then reference it in a manuscript file.

### Detecting unresolved tokens

```bash
grep -r "{{" output/manuscript/ 2>/dev/null \
  && echo "UNRESOLVED TOKENS — re-run scripts/generate_manuscript_variables.py" \
  || echo "All tokens resolved"
```

## Equations

This manuscript defines no numbered equations; if one is added, use the
Pandoc-crossref bracket form `$$...$$ {#eq:label}` and reference with
`[@eq:label]`. Never use raw `\ref`/`\eqref`.

## Figures

The orchestrator manuscript currently defines no figure registry. If figures
are added, every figure must use the Pandoc image + `{#fig:label}` form and be
referenced via `[@fig:label]`.

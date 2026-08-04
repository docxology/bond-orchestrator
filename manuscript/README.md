# manuscript/

Source templates for the BOND-ORCHESTRATOR (codename DAG 00) manuscript.

| File | Purpose |
|---|---|
| `config.yaml` | Identity, paper metadata, publication records, mission parameters |
| `00_abstract.md` … `99_references.md` | Manuscript sections (Pandoc + `{{TOKEN}}` hydration) |
| `references.bib` | BibTeX bibliography |
| `preamble.md` | LaTeX preamble injected at PDF render time |
| `SYNTAX.md` | Citation + token syntax reference |
| `layer_contract.yaml` | Layer-boundary declaration for drift checks |

Regeneration: `scripts/run_mission.py OPERATION_OMNIBUS` then
`scripts/generate_manuscript_variables.py` (strict by default; `--allow-draft`
for drafts). See [`AGENTS.md`](AGENTS.md) for the full protocol.

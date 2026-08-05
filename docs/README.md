# docs/ — bond-orchestrator

Agent-facing documentation hub for BOND-ORCHESTRATOR (codename DAG 00), the
Layer 3 mission DAG runner of the BOND suite.

## What lives here

| File | Holds |
|---|---|
| [`AGENTS.md`](AGENTS.md) | The index and technical conventions for this directory; reading order; REQUIRED-vs-convention path table |
| [`agent_instructions.md`](agent_instructions.md) | Seven hard rules for any agent modifying this package, plus the verification checklist |
| [`architecture.md`](architecture.md) | Module-by-module inventory of `src/`, how the pieces compose in one run, the frozen `bond_api` binding, checkpoint schema, CLI surface, frozen-surface list |
| [`protocol.md`](protocol.md) | The runner-side `MissionProvider` contract: data model, five methods, conformance rules |
| [`testing_philosophy.md`](testing_philosophy.md) | Why there are no mocks and what the stand-ins actually are; coverage mechanics; per-file coverage map |
| [`style_guide.md`](style_guide.md) | Seven code/doc style rules governing `src/`, `scripts/`, `tests/` |
| [`output_conventions.md`](output_conventions.md) | The `output/` layout, regeneration sequence, producer/consumer map |
| [`_generated/COUNTS.md`](_generated/COUNTS.md) | Measured test count, coverage split, lint/type results — the only place numbers are recorded |

## Audience-targeted entry points

| Reader | Start here |
|---|---|
| AI agents | [`agent_instructions.md`](agent_instructions.md) |
| New developers | [`../README.md`](../README.md) then [`architecture.md`](architecture.md) |
| Film-provider authors | [`protocol.md`](protocol.md), then the binding section of [`architecture.md`](architecture.md) |
| Test maintainers | [`testing_philosophy.md`](testing_philosophy.md) |
| Manuscript editors | [`../manuscript/SYNTAX.md`](../manuscript/SYNTAX.md) |
| Anyone quoting a number | [`_generated/COUNTS.md`](_generated/COUNTS.md) — never a figure typed into prose |

## The one rule this directory enforces on itself

No measured quantity — test count, coverage percentage, timing — is written
into any file here except `_generated/COUNTS.md`. Everywhere else, describe
the gate and link the counts file. A stale number in a doc is worse than no
number, because it reads as evidence.

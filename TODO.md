# bond-orchestrator TODO

Forward-only backlog for **BOND-ORCHESTRATOR (DAG 00)** — Layer 3, the
multi-package mission DAG runner. Delivered work is summarised in one line per
capability; the narrative history lives in the git log and the manuscript.

## Delivered

The package currently ships, all gated:

| Capability | Where |
|---|---|
| Mission DAG: build, validate, canonical topological order, ordered cycle-path recovery | `src/bond_orchestrator/graph.py` |
| Wavefront stage planning: achievable parallelism + critical path | `src/bond_orchestrator/planning.py` |
| Bounded, backoff-free retry policy with per-step `RetryRecord`s | `src/bond_orchestrator/retry.py` |
| Phase-major runner with checkpoint/resume (manifest + per-step files + report, attempt counts persisted) | `src/bond_orchestrator/runner.py` |
| Canned missions: OMNIBUS (chain), DIAMOND (join), SINGLET (degenerate) | `src/bond_orchestrator/missions.py` |
| Deterministic reference providers implementing the real protocol | `src/bond_orchestrator/providers.py` |
| REAL film binding to the frozen `bond_api` protocol, strict discovery, lazy import | `src/bond_orchestrator/film_providers.py` |
| Provenance records (deterministic run id, JSON + CSV) | `src/bond_orchestrator/provenance.py` |
| `{{TOKEN}}` hydration incl. stage, retry, and DAG hand-off tokens | `src/bond_orchestrator/manuscript_variables.py` |
| Thin CLI: `run` / `plan` / `list` | `src/bond_orchestrator/cli.py` |

Current measured gate results — test count, coverage split, lint and type
status — are in [`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md).
They are deliberately not repeated here; a number in a backlog file goes stale
the next time anyone touches a test.

## BOND-suite integration points

| # | Integration | Dependency | Status / acceptance criteria |
| --- | --- | --- | --- |
| 1 | Real film providers bound via the `film_providers.py` adapter | `bond-api` | **WIRED.** `load_film_providers` / `load_mission_providers` discover and run real films; `tests/test_film_binding.py` drives goldfinger / goldeneye / spectre / no_time_to_die through the runner. The module has no `skipif`: if those packages are missing the tests fail rather than skip, so this row cannot read WIRED against an empty tree |
| 2 | `provenance.py` delegates to `mission_io` | `bond-utilities` | **OPEN.** Acceptance: records written via `bond_utilities.mission_io.record_provenance_outcome`, byte-identical schema, existing provenance tests unchanged and green |
| 3 | Mission hand-off from the coordinator | `bond-coordinator` | **OPEN.** Acceptance: a coordinator-produced `Mission` (same shape) executes through `MissionRunner` with no orchestrator change |
| 4 | `protocol.py` re-exports the frozen `bond_api.MissionProvider` instead of mirroring it | `bond-api` | **DEFERRED — not obviously desirable.** The two contracts differ by design: runner-side calls carry `MissionPackage` + `MissionContext`; the frozen protocol carries neither. Adapting is correct; re-export would force DAG concepts into a protocol 27 films already implement. Revisit only if bond-api grows a package-aware variant |

Until #2 and #3 land, the package runs on its own pure core — no stalls.

## Backlog (ordered)

1. **`--list-providers` CLI view.** Report which providers a mission binds and
   which film capabilities each exercises. Acceptance: new subcommand, exit 0,
   output covered by `tests/test_cli.py`.
2. **Parallel execution flag (`--parallel`).** Run the packages within one
   stage concurrently while preserving stage order; sequential stays the
   default. The stage planner already proves this is safe. Acceptance: report
   byte-identical to the sequential run for every canned mission, determinism
   tests green under both modes, no wall-clock value in any artifact.
3. **Mission manifest checksum.** Record a hash of the mission definition in
   `manifest.json`; on resume, refuse (or loudly warn) when the definition has
   changed since the checkpoint was written. Acceptance: a modified mission
   run against an existing state dir fails rather than silently resuming a
   different mission — today it *would* resume, which is the sharpest
   remaining correctness gap in checkpoint/resume.
4. **One-shot regeneration orchestrator.** A thin script running mission →
   provenance → manuscript variables in sequence, so `output/` is rebuilt by a
   single documented command.
5. **Optional wall-clock diagnostics.** Per-phase, per-package durations,
   runtime-only. They must never reach a persisted artifact; that constraint
   is the whole reason this is item 5 rather than item 1.
6. **Reference-provider coverage for the wider fleet.** The canned missions
   bind six reference providers; extend once `bond-coordinator` declares the
   authoritative 27-film roster, rather than hand-maintaining a second roster
   here.

## Known non-goals

- **Backoff between retries.** Rejected permanently: a sleep puts a
  non-reproducible quantity inside artifacts whose byte-stability is the
  package's core claim.
- **Film business logic.** Belongs to the film packages behind the protocol.
- **Mission selection.** Belongs to `bond-coordinator`.

## Quality gates (never regress)

- ≥90% line+branch coverage on `src/` (`pyproject.toml` gate).
- Zero mocks in `tests/`; deterministic providers implement the REAL protocol.
- `ruff check` + `ruff format --check` + `mypy` clean on `src/` and `scripts/`.
- No module-scope `bond_api` import anywhere in `src/`; the pure core stays
  importable without bond-api installed.
- Determinism: no wall-clock or RNG in any persisted artifact.
  `tests/test_determinism_bytes.py` enforces the boundary by running each
  mission twice into separate dirs and comparing every artifact with
  `read_bytes()`; it ships a positive control proving the comparison can
  detect a one-byte difference.
- Real-film evidence: `tests/test_film_binding.py` has no `skipif`. If the
  sibling film packages are absent the suite goes RED, because manuscript
  §3.3 claims real-film binding unconditionally.
- Packaging honesty: `tests/test_packaging.py` fails if a declared runtime
  dependency is imported nowhere, if an import is undeclared, if the
  `bond-api` path source becomes absolute, or if the forked-exemplar slug
  appears in any declared value or `.py` source.
- Publication metadata stays empty until a real deposit exists. This package
  has no DOI, no public repository, and no archived copies; see
  `STANDALONE.md`.
- Manuscript metrics injected via `{{TOKEN}}` only — never hand-authored.
  This includes the §5.4 mission-surface table, whose counts are derived from
  the mission registry by `_mission_surface_tokens`.
- The public shapes listed under "Frozen cross-package surfaces" in
  `AGENTS.md` change additively or not at all.

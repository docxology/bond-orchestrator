# TODO — bond-orchestrator (DAG 00)

`bond-orchestrator` is the Layer 3 mission DAG runner of the BOND suite: it
executes a DAG of film packages through five lifecycle phases
(`brief → recon → plan → execute → debrief`) in canonical topological order over
the `MissionProvider` protocol, with checkpoint/resume, a bounded backoff-free
retry policy, wavefront stage planning, provenance records, and `{{TOKEN}}`
hydration for the manuscript. Measured figures for the enforced gate live in
[`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md) — the package rule is
that no measured number is restated in prose, and this header had gone stale,
quoting a pre-round-2 test count that both the round-2 table below and
`COUNTS.md` had already superseded. Everything the
phase-6 adversarial audit flagged as SEVERE or MODERATE is closed on disk —
the false DOI, the non-existent repository, the inherited archival locations,
the `skipif`-gated film tests, the un-forked `STANDALONE.md`, the hand-authored
§5.4 table, the undeclared-dependency drift, and the `rg` lineage one-liner
that could never print `Clean`. What remains is below.

## Open work

### Correctness

**C1 — Checkpoint resume never checks which mission it is resuming.**
`src/bond_orchestrator/runner.py:294-297` writes `{"mission": <name>, "steps":
[...]}` into `manifest.json`, but the load path at
`src/bond_orchestrator/runner.py:197-200` reads only `manifest.get("steps")`.
The `mission` key it wrote is never compared, and no hash of the mission
definition (packages, `depends_on` edges, phase set) is recorded at all. Edit a
mission's dependency edges or swap a package and re-run against the same
`--checkpoint-dir`: every step id that still matches by name is replayed from
the old run's step files, and the consolidated report describes a mission that
was never executed. Nothing in `tests/test_runner.py` or
`tests/test_determinism_bytes.py` covers a *changed* definition — the resume
tests all re-run the identical mission.
*Done when:* running a mutated mission against an existing state directory
fails loudly (or refuses to resume) rather than replaying stale steps, driven
by a recorded definition hash rather than the name alone, with a test that
mutates a mission's `depends_on` between two runs and asserts the failure.
*Command:* `uv run --extra dev pytest tests/test_runner.py tests/test_determinism_bytes.py -v`

### Verification

**V1 — "schema-identical to `mission_io`" is asserted and is false.**
`bond-utilities` now ships the helper:
`../bond-utilities/src/bond_utilities/mission_io.py:153` defines
`record_provenance_outcome`, whose record keys are `mission_id`, `codename`,
`seed`, `version`, `started_at`, `parameters`, `outcomes`,
`provenance{input_hash, schema_version, seed}` (built at lines 190-206). This
package's `ProvenanceRecord.as_dict()`
(`src/bond_orchestrator/provenance.py:55-70`) emits `run_id`, `orchestrator`,
`codename`, `schema_version`, `mission`, `package_id`, `provider`, `phase`,
`outcome`, `detail`, `artifact_refs`, `metrics`. Only `codename` and
`schema_version` appear in both, carrying different values. Yet
`manuscript/04_conclusion.md:19` calls `provenance.py` the "schema-identical
stand-in", `manuscript/07_scope_and_related_work.md:53` calls it a "drop-in
equivalent", and "mission_io-equivalent" appears unqualified at
`README.md:13`, `AGENTS.md:47`, `src/AGENTS.md:25`,
`manuscript/00_abstract.md:16`, `manuscript/02_methodology.md:138`,
`docs/architecture.md:147` and `src/bond_orchestrator/provenance.py:1`. No test
compares the two schemas, so the strongest of these claims has no falsifier.
*Done when:* either a test imports `bond_utilities.mission_io`, compares the two
key sets, and fails when they diverge — in which case the prose must be
rewritten to name the mapping, not an identity — or every site above is
softened to what is true ("an independent, non-delegating provenance writer").
Whichever is chosen, the claim and the gate must agree.
*Command:* `uv run --extra dev pytest tests/test_provenance.py -v`

**V2 — the `requires-python = ">=3.10"` floor has never been exercised.**
`pyproject.toml:16` declares the floor. Every gate this package has ever run
used CPython 3.14.6 (recorded in `docs/_generated/COUNTS.md`); no 3.10, 3.11,
3.12 or 3.13 run exists. `manuscript/05_experimental_setup.md` §5.3 defers the
actual interpreter to `COUNTS.md` rather than asserting it, which limits the
damage, but the floor itself is an untested declaration. Carried over from the
phase-6 unresolved list; the note there proposed a multi-version CI matrix,
which is out of scope for this package, but a single local run on the oldest
supported interpreter is not.
*Done when:* the full gate passes on 3.10 (the conditional `tomli` dev
dependency in `pyproject.toml` already exists for exactly this), or the floor is
raised to a version that has actually been run, with the interpreter matrix
recorded in `docs/_generated/COUNTS.md`.
*Command:* `uv run --python 3.10 pytest tests/ --cov=src --cov-fail-under=90`

**V3 — `docs/_generated/COUNTS.md` is hand-maintained and ungated.**
It opens by claiming "Everything below was read out of an actual gate run — no
figure here is estimated", and `README.md:169-172`,
`manuscript/05_experimental_setup.md` §5.3 and `manuscript/06_reproducibility.md`
§6.3 all deliberately defer their numbers to it *instead of* quoting them. But
its path says `_generated` and nothing generates it:
`grep -rn "COUNTS" tests/ scripts/ src/` returns one documentation link in
`tests/AGENTS.md:46` and nothing else. A stale COUNTS.md silently falsifies
every file that defers to it — the deferral chain is only as honest as its one
unverified leaf. (Its current contents do match this session's run; that is
luck, not a gate.)
*Done when:* a script or test derives tests-passed, statement/branch counts, the
coverage split and the interpreter from `coverage json` output and fails when
the committed file disagrees — the same treatment the manuscript's `{{TOKEN}}`
metrics already get.
*Command:* `uv run --extra dev pytest tests/ -k counts` (once the gate exists)

### Documentation

**D1 — five sites still condition the `mission_io` integration on a package
that already exists.** `../bond-utilities/src/bond_utilities/mission_io.py` is
on disk with `record_provenance_outcome` at line 153, but
`manuscript/07_scope_and_related_work.md:53` says "will delegate to it once it
ships", `manuscript/04_conclusion.md:19` says "until it ships",
`docs/architecture.md:147` says "until `bond-utilities` ships",
`src/bond_orchestrator/provenance.py:3-4` says "once that package lands", and
`manuscript/layer_contract.yaml:33` says "not yet wired". The real blocker is
that nobody has written the delegation, plus the schema mismatch in V1 — not
the sibling's absence. Stating a discharged blocker hides the live one.
*Done when:* none of those five sites conditions the integration on the
package's existence, and each names the actual blocker.
*Command:* `grep -rn "ships\|package lands\|not yet wired" manuscript/ docs/ src/` — the
only surviving hits should be the two unrelated senses at `docs/architecture.md:38`
and `docs/architecture.md:161` ("the three DAG shapes the package ships", "Each
film package ships `src/<slug>/mission.py`"). Today it also returns the five sites
above.

**D2 — `AGENTS.md:163` lists `bond-utilities` with status "declared".**
It is not declared anywhere: `[project].dependencies` in `pyproject.toml` is
`pyyaml` + `bond-api`, `[tool.uv.sources]` names only `bond-api`, and neither
`bond-utilities` nor `bond_utilities` appears in `pyproject.toml` or `uv.lock`.
The true status is "not declared, not imported, not wired". "Declared" reads as
a stronger integration state than exists, in the same table whose other two
rows say **wired** on real evidence.
*Done when:* the row states the true status, or the dependency is actually
declared as part of E6.
*Command:* `grep -n "bond.utilities" pyproject.toml uv.lock AGENTS.md`

### Extension

Genuine future work. None of these is a defect; the package is complete and
green without them.

**E1 — `--list-providers` CLI view.** Report which providers a mission binds and
which film capabilities each exercises. `src/bond_orchestrator/cli.py:38-71`
registers exactly three subcommands today (`run`, `plan`, `list`).
*Done when:* the subcommand exists, exits 0, and its output is asserted in
`tests/test_cli.py`. *Command:* `uv run --extra dev pytest tests/test_cli.py -v`

**E2 — `--parallel` execution flag.** Run the packages within one wavefront
stage concurrently while preserving stage order; sequential stays the default.
`src/bond_orchestrator/planning.py` already computes the stages and proves this
is safe; `run_parser` (`src/bond_orchestrator/cli.py:48-65`) is where the flag
goes.
*Done when:* every canned mission's report and checkpoint files are
byte-identical under both modes, `tests/test_determinism_bytes.py` is
parametrised over both, and no wall-clock value enters any artifact.
*Command:* `uv run --extra dev pytest tests/test_determinism_bytes.py tests/test_cli.py -v`

**E3 — One-shot regeneration orchestrator.** `scripts/` holds only
`run_mission.py` and `generate_manuscript_variables.py`; rebuilding `output/`
takes two commands in the right order, and the second fails confusingly if the
first was skipped.
*Done when:* a single thin script runs mission → provenance → manuscript
variables and is covered by `tests/test_scripts_smoke.py`.
*Command:* `uv run --extra dev pytest tests/test_scripts_smoke.py -v`

**E4 — Optional wall-clock diagnostics.** Per-phase, per-package durations,
runtime-only. Deliberately last: the constraint that they must never reach a
persisted artifact is the whole reason this ranks below everything else.
*Done when:* durations are printable at runtime and
`tests/test_determinism_bytes.py` still passes unchanged with diagnostics on.
*Command:* `uv run --extra dev pytest tests/test_determinism_bytes.py -v`

**E5 — Reference-provider coverage for the wider fleet.** The three canned
missions in `src/bond_orchestrator/missions.py` bind six distinct packages. The
blocker recorded in earlier revisions is now discharged: `bond-coordinator`
declares the authoritative roster at
`../bond-coordinator/src/bond_coordinator/registry.py:386` (`FILM_SLUGS`,
measured 27 slugs this session). Extend from that roster — never by
hand-maintaining a second one here.
*Done when:* mission coverage is derived from the coordinator roster and a test
fails when the two disagree. *Command:* `uv run --extra dev pytest tests/test_missions.py -v`

**E6 — `provenance.py` delegates to `bond_utilities.mission_io`** (BOND-suite
integration point 2). Blocked on V1: the two schemas differ, so "delegate" means
writing a mapping and deciding which record shape is canonical. One hard
constraint — `record_provenance_outcome` defaults `started_at` to
`datetime.now(timezone.utc)`
(`../bond-utilities/src/bond_utilities/mission_io.py:190-196`); it must be
called with the `started_at`/`now` overrides pinned, or a wall-clock value lands
in a persisted artifact and the package's core determinism claim dies.
*Done when:* records are written through `mission_io`, `bond-utilities` is a
declared dependency, and `tests/test_provenance.py` +
`tests/test_determinism_bytes.py` are green unchanged.
*Command:* `uv run --extra dev pytest tests/test_provenance.py tests/test_determinism_bytes.py -v`

**E7 — Mission hand-off from `bond-coordinator`** (integration point 3).
Blocked upstream, not here: the coordinator's public surface
(`../bond-coordinator/src/bond_coordinator/__init__.py:60-100`) exports
`ROSTER`, `FILM_SLUGS`, `PackageRecord`, `MissionPhase` and status/ledger types
— there is no `Mission`, no DAG type, and no `depends_on` anywhere under
`bond-coordinator/src/`. Nothing exists yet for the runner to accept.
*Done when:* a coordinator-produced `Mission` (same shape as
`src/bond_orchestrator/protocol.py`) executes through `MissionRunner` with no
orchestrator change, proven by a test that imports it from `bond_coordinator`.
*Command:* `uv run --extra dev pytest tests/test_integration.py -v`

## Known limitations (not bugs)

- **No backoff between retries.** Permanently rejected. A sleep puts a
  non-reproducible quantity inside artifacts whose byte-stability is this
  package's core claim; bounded immediate re-attempts recover from a transient
  fault without that cost (`src/bond_orchestrator/retry.py`).
- **Film business logic stays in the film packages**, behind the protocol.
  **Mission selection stays in `bond-coordinator`.** Neither belongs here.
- **`protocol.py` does not re-export `bond_api.MissionProvider`.** Deferred as
  not obviously desirable, not as pending work: the two contracts differ by
  design — runner-side calls carry `MissionPackage` + `MissionContext`, the
  frozen `bond-api` protocol carries neither. The adapter in
  `src/bond_orchestrator/film_providers.py` is the correct structure; a
  re-export would force DAG concepts into a protocol 27 films already implement.
  Revisit only if `bond-api` grows a package-aware variant.
- **The lineage gate does not scan Markdown prose or config comments.**
  `tests/test_packaging.py:179-193` scans the declared *values* of the eight
  structured identity files and every `.py` under `src/`, `scripts/` and
  `tests/` — deliberately not narrative text, because this package's own
  remediation notes name the fork source on purpose and an exclusion list would
  make the gate hollow in a worse way. Honest scope: un-forked *narrative* text
  — exactly the class of defect that produced the old `STANDALONE.md` fork guide
  — is **not** gated and remains a review responsibility. This is stated in
  `manuscript/06_reproducibility.md` §6.2 and in the test module docstring rather
  than letting the narrower gate read as equivalent to the broken `rg` one-liner
  it replaced.
- **Four files still contain the retracted DOI and repository strings inside
  explanatory comments**, as a deliberate audit trail of what was removed and
  why: `manuscript/config.yaml:34-36`, `CITATION.cff:4-5`,
  `manuscript/references.bib:87`, `STANDALONE.md:33-35`. No *declared value*
  carries them, and the machine-readable sidecars (`codemeta.json`,
  `.zenodo.json`) were stripped of the literals so nothing can re-ingest them. A
  naive full-text `grep 20417136` therefore returns four hits that are **not**
  unfinished remediation. Do not "clean" them without replacing the audit trail.
- **This package is unpublished.** No DOI, no standalone repository, no PyPI or
  TestPyPI release, no archival copy anywhere. `publication:` fields stay empty
  until a real deposit exists and its identifier has been checked against the
  live registry — see `STANDALONE.md`.

## Verification

Run from this directory. These are the gates. They were re-measured on
2026-11-04 at the bond-api vendoring tip (the 2026-08-05 figures below them had
drifted): the suite, the format gate, the types gate and the honesty gates are
green; the lint gate reports 28 pre-existing findings and is recorded as such in
[`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md) (W2).

```bash
# 1. The enforced gate: full suite + >=90% line+branch coverage on src/
uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90
#    expected: 180 passed, 0 skipped; "Required test coverage of 90% reached"

# 2. Lint + format + types
uvx ruff check src/ scripts/ tests/          # expected: 28 findings (all pre-existing) —
                                             # reads the committed [tool.ruff] table
uvx ruff format --check --line-length 120 src/ scripts/   # expected: 21 files already formatted
uvx mypy src/ scripts/                       # expected: no issues in 16 source files

# 3. Honesty gates, individually
uv run --extra dev pytest tests/test_packaging.py -v         # declared-vs-imported deps, relative
                                                 # bond-api path, no fork slug in values/.py
uv run --extra dev pytest tests/test_determinism_bytes.py -v # two fresh runs byte-identical, plus a
                                                 # positive control for 1-byte drift
uv run --extra dev pytest tests/test_film_binding.py -v      # REAL sibling films; no skipif — RED if absent

# 4. Layer contract (the pure core must stay liftable)
grep -rnE "^(from|import) infrastructure" src/bond_orchestrator/ || echo "Clean — pure core"
grep -rnE "^(from|import) bond_api" src/bond_orchestrator/ || echo "Clean — no module-scope bond_api"

# 5. Regenerate evidence before quoting any output artifact
uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state
uv run python scripts/generate_manuscript_variables.py
```

Measured counts, the coverage split and lint/type results live in
[`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md) — read V3 above before
trusting them.


---

## Round-2 (2026-08-06) — improvement pass

### Findings → fixes (each with a regression / negative-control test)

- **C1 — checkpoint resume never checked the mission definition (closed).**
  The runner loaded `manifest["steps"]` without comparing the mission that
  wrote them. Now `protocol.mission_fingerprint` hashes the full definition
  (name + every package and its `depends_on` edges); `_RunState` records it as
  `definition_hash` in `manifest.json` and refuses (`MissionError`) to load a
  checkpoint dir written for a different definition — including an older dir
  that has no hash at all. Tests: `test_manifest_records_definition_hash`,
  `test_resume_rejects_changed_mission_definition` (mutates `depends_on`),
  `test_resume_accepts_unchanged_definition` (positive control). Fresh-run
  byte-determinism is preserved because both runs write the same hash.
- **Empty-mission fail-open (closed).** `build_film_graph(())` returned an
  empty graph, so a zero-package `Mission` ran zero steps and reported a
  vacuously green all-verdicts-pass. It now raises
  `GraphError("mission has no packages; ...")`. Test:
  `test_empty_mission_rejected` in `tests/test_graph.py`.
- **Provenance run id ignored the DAG structure (closed).** `derive_run_id`
  hashed only mission name + package ids, so two missions with the same name
  and package set but different `depends_on` edges shared one run id. It now
  hashes the full mission fingerprint (`mission_fingerprint(m)[:12]`, still 12
  hex chars, still distinct per canned mission). Test:
  `test_run_id_fingerprints_dependency_structure` in `tests/test_provenance.py`.
- **Documentation honesty — D1 / D2 / V1 prose (closed).** Every
  "mission_io-equivalent", "schema-identical stand-in", "drop-in equivalent",
  and "until it ships / once that package lands / will delegate once it ships"
  site in `README.md`, `AGENTS.md`, `src/AGENTS.md`, `src/__init__.py`,
  `src/provenance.py`, `manuscript/00_abstract.md`, `manuscript/02_methodology.md`,
  `manuscript/04_conclusion.md` and `docs/architecture.md` now states the
  truth: `provenance.py` is an independent, **non-delegating** writer whose
  schema differs from `mission_io`'s, and the schema mapping is the real
  blocker (V1/E6). `AGENTS.md`'s `bond-utilities` integration row now reads
  "not declared / not wired" (D2). Took the prose-softening branch of V1's
  two-option done-when (a schema-comparison test would require declaring the
  `bond-utilities` dependency, which this package should not take on).

### Gates (measured 2026-08-06, CPython 3.14.6, darwin)

| Gate | Result |
|---|---|
| `uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90` | **178 passed, 0 skipped, 0 failed; 99.03%** combined line+branch (baseline 173 / 98.96%) |
| `uvx ruff check src/ scripts/ tests/` | clean |
| `uvx ruff format --check src/ scripts/` | clean (15 files) |
| `uvx mypy src/ scripts/` | no issues in 15 source files |
| honesty greps (no mocks, pure core, no module-scope `bond_api`) | clean |

Live counts updated in [`docs/_generated/COUNTS.md`](docs/_generated/COUNTS.md)
to the measured split: 840 stmts / 0 missed (100% line), 190 branches /
10 partial (94.74% branch), 99.03% combined.

### Gates (re-measured 2026-11-04, CPython 3.15.1, darwin) — supersedes the block above

| Gate | Measured at the vendoring tip |
|---|---|
| `uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90` | **180 passed, 0 skipped, 0 failed; 99.04%** combined line+branch (846 stmts / 0 missed, 194 branches / 10 partial) |
| `uvx ruff check src/ scripts/ tests/` | **28 findings, all pre-existing** (16 RUF012, 8 RUF100, 3 I001, 1 RUF022) — not `clean`. The 2026-08-06 row was measured with whatever `uvx ruff` resolved that day; this one with `uvx ruff 0.17.3` (the tools are fetched, not locked) |
| `uvx ruff format --check --line-length 120 src/ scripts/` | clean (21 files already formatted) |
| `uvx mypy src/ scripts/` | no issues in 16 source files (`uvx mypy 2.4.1`) |
| honesty greps (no mocks, pure core, no module-scope `bond_api`) | clean, and each `|| echo` branch is reachable (measured: rc=1, 0 hits in every scope) |

### Regenerated evidence
`output/data/mission_report.json`, `output/data/provenance/`, `output/state/`
and `output/data/manuscript_variables.json` (38 tokens, including two new live
tokens) regenerated via:
`uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state`
then `uv run python scripts/generate_manuscript_variables.py`.

### Manuscript (round-2 additions)
- §3.1 per-package debrief table, bound to a new live `RESULT_PACKAGE_RESULTS`
  token (debrief scan of the report; `%g` formatting matches the runner).
- §3.6 "The measured DAG" — a deterministic text figure bound to a new live
  `RESULT_DAG_FIGURE` token (stages + verdicts + measured hand-off payloads).
- §7.4 "Limitations and uncertainty" — honest limits: provenance not yet
  `mission_io`; single-interpreter evidence for the `>=3.10` floor (V2);
  hand-maintained `COUNTS.md` (V3); the strict new checkpoint semantics;
  why real-film retry cannot rescue a deterministic film; parallel execution
  planned not performed; empty-plan packages passing vacuously; single-node,
  single-interpreter determinism.
- §2.3 updated to describe the definition-hash resume guard; §7.3 and the
  manuscript `AGENTS.md` token table updated to match.

### Left for a future round
- V2 (no 3.10–3.13 run of the `>=3.10` floor) and V3 (COUNTS.md ungated) remain
  open from the pre-round-2 backlog.
- E1–E7 extension items (list-providers CLI, `--parallel`, one-shot
  regeneration, wall-clock diagnostics, roster-derived missions,
  `mission_io` delegation, coordinator hand-off) remain as documented.
- The new empty-mission guard rejects zero-package missions; a future round
  could also decide whether a *zero-step provider* (empty plan) should be
  rejected instead of passing vacuously.

## Vendoring wave (2026-11-04)

`bond-api` resolved from a sibling checkout (`[tool.uv.sources] bond-api = { path = "../bond-api" }`),
so a clone of this repository resolved nothing: a sibling-free export fails
`uv sync` with `Distribution not found at …/bond-api` (rc=2, measured). The upstream bytes are now
recorded at `vendor/bond-api` (upstream commit `c0362ff0c9d7`, a sha256 per copied file in
`PROVENANCE.json`, `VENDOR.md` beside it), `[tool.uv.sources]` points at that copy, and `uv.lock`
was regenerated from that declaration: `uv lock --check` rc=1 → rc=0, two runs byte-identical
`af2bce2f6aadbcf0`, `--refresh` leaves the file untouched, four changed lines of which two moved,
and no `../bond-api` remains. All 16 patch blobs match their recorded post-images and
`scripts/vendor.py --check` reports `vendor/bond-api: ok`, 0 findings.

**W1 — "Inherits workspace settings from root pyproject.toml" was false, twice, and the table this
change creates now declares the width the tree is written to.** No ancestor `pyproject.toml` declares
`[tool.ruff]` or `[tool.mypy]` for this checkout, and `uvx ruff check --show-settings` reported
ruff's default 88 before the change and 120 after it — the file's table is the effective
configuration. Two-arm control with the table kept in this same file and only its body varying: with
`line-length = 120` the documented format gate reports 21 files already formatted and the documented
check reports 28 findings; with that line removed, 11 files would be reformatted and the check
reports 31 findings. The width is the house rule (`src/STYLE.md` rule 6) and the tree is written to
it, which is why it is committed rather than passed on every command line.

**W2 — the documented expectations did not hold and are corrected where they are printed.** The
verification block in this file said `All checks passed!` and `15 files already formatted`; measured
at this head they are 28 findings (at the committed 120; 31 at the default) and 21 files already
formatted, with the suite at 180 passed and `mypy src/ scripts/` clean in 16 files. The dated
2026-08-06 gate table above is left as the record it is and superseded by a re-measured block.
`docs/_generated/COUNTS.md` is refreshed from the same run and now names the tool versions
(`uvx ruff 0.17.3`, `uvx mypy 2.4.1`) beside the figures, because neither tool is a declared
dependency: `uvx` fetches the current release, so a future release can move the finding count with no
change to this tree.

**W3 — the bundled checker needed re-conforming to the declared width, and the record was
re-sealed.** `scripts/vendor.py` arrives formatted at 88; at the declared 120 it was the only one of
21 scoped files the format gate wanted to reformat. It was reformatted (21 insertions / 65 deletions,
line-joins only) and `scripts/vendor.py --refresh` re-sealed exactly one field —
`checker_sha256 e7b56b3e…` → `0372e5d8…`, the same value the other 120-width repository in this wave
produced for the same bytes, so the re-conforming is reproducible, not repository-specific. The
payload's `aggregate_sha256 2e8fa087be…` is untouched; `--check` is green after the re-seal.

**W4 — recorded, not swept.** (a) Nine prose/command copies of the template-era path
`projects/working/bond/bond-orchestrator/` are corrected to true statements (`AGENTS.md` ×2,
`.agents/skills/bond-orchestrator/SKILL.md`, `README.md`'s film-package snippet, `STANDALONE.md` ×2,
`docs/AGENTS.md`, `docs/testing_philosophy.md`, `manuscript/AGENTS.md`); the README snippet's
replacement (`Path("..").resolve()`) is verified against the live tree, where it resolves the three
film packages this suite binds. (b) The eight `source:` records in `data/claim_ledger.yaml` keep that
path deliberately: each names the tree its claim was measured against, so they are provenance
records, not instructions — a sweep for the literal path now returns only those eight and
`scripts/vendor.py`'s docstring. (c) The 28-finding lint debt and the whole-tree formatter red
outside the documented scoped gate — `tests/test_runner.py` plus five Markdown files with fenced
blocks (`AGENTS.md`, `README.md`, `docs/protocol.md`, `docs/style_guide.md`, `tests/PATTERNS.md`) —
are pre-existing at both ends and stay as recorded debt.

Measured at the vendoring tip (CPython 3.15.1, darwin): suite 179 → **180 passed** at 99.04% combined
(846 statements / 194 branches, 10 partial, unchanged by this pass — the added test is the provenance
check and `--cov=src` does not measure `scripts/`); `tests/test_film_binding.py` 16 passed (real
film packages, no `skipif`); `test_packaging.py` 15 passed; `test_determinism_bytes.py` 10 passed;
the three honesty greps rc=1 with 0 hits each, so every `|| echo "Clean"` branch is reachable;
`uvx mypy src/` clean in 12 files and `uvx mypy src/ scripts/` in 16; regeneration digest
`0e914ef1f70e4d18` identical before and after (the mission and token outputs count no files, so
nothing here moves by design); 21 files under `output/`.

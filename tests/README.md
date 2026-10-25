# tests/

Zero-mock test suite for BOND-ORCHESTRATOR (codename DAG 00): protocol
conformance, DAG order, checkpoint/resume, provenance, CLI, manuscript
variables, and end-to-end integration over real deterministic providers.

- [`AGENTS.md`](AGENTS.md) — test map + commands
- [`PATTERNS.md`](PATTERNS.md) — deterministic fake provider patterns

Gate: `uv run --extra dev pytest tests/ --cov=src --cov-fail-under=90`.

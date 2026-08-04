"""Thin orchestrator: hydrate manuscript {{TOKEN}}s from config.yaml + mission report.

Strict by default: fails when ``output/data/mission_report.json`` is absent
(run ``scripts/run_mission.py`` first).  Pass ``--allow-draft`` to use
``"N/A"`` fallbacks for result-derived tokens during early drafting.

Example:
    uv run python scripts/generate_manuscript_variables.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bond_orchestrator.manuscript_variables import generate_variables  # noqa: E402


def main() -> int:
    """Thin wrapper around :func:`generate_variables`; writes the token map."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="use N/A fallbacks when output/data/mission_report.json is absent",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    variables = generate_variables(project_root, require_outputs=not args.allow_draft)
    out_path = project_root / "output" / "data" / "manuscript_variables.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(variables, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(variables)} manuscript variables -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

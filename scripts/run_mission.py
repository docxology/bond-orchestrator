"""Thin orchestrator: run a canned mission through the bond-orchestrator CLI.

Business logic lives in ``src/bond_orchestrator``; this script only wires
``sys.path`` and defaults the subcommand to ``run`` (a script named
``run_mission.py`` should not need to spell it out).

Examples:
    uv run python scripts/run_mission.py list
    uv run python scripts/run_mission.py OPERATION_OMNIBUS --checkpoint-dir output/state
    uv run python scripts/run_mission.py run OPERATION_OMNIBUS   # explicit form
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bond_orchestrator.cli import main  # noqa: E402

COMMANDS = ("run", "list")


def _with_default_command(argv: list[str]) -> list[str]:
    """Default to the ``run`` subcommand when the first argument is not one."""
    if not argv or argv[0] not in COMMANDS:
        return ["run", *argv]
    return argv


if __name__ == "__main__":
    raise SystemExit(main(_with_default_command(sys.argv[1:])))

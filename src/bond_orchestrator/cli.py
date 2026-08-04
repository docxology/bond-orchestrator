"""Thin command-line interface: run canned missions, list missions.

Commands
--------
``list``
    Print the canned mission registry (name + package chain).
``run <mission> [--checkpoint-dir DIR] [--output-dir DIR]``
    Execute the mission end-to-end over the reference providers, persist the
    consolidated report + provenance, and print the consolidated debrief.
    Exit code 0 when every debrief verdict is ``"pass"``, 1 otherwise.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .missions import MISSIONS, MISSION_NAMES, UnknownMissionError, get_mission
from .protocol import MissionProvider
from .provenance import write_mission_report, write_outcome_records
from .providers import get_provider
from .runner import MissionReport, MissionRunner

DEFAULT_REPORT_FILENAME = "mission_report.json"


def _project_root() -> Path:
    """Package root: this file lives at <root>/src/bond_orchestrator/cli.py."""
    return Path(__file__).resolve().parent.parent.parent


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI (thin: argument parsing only)."""
    parser = argparse.ArgumentParser(
        prog="bond-orchestrator",
        description="BOND-ORCHESTRATOR (DAG 00): run multi-package film missions "
        "over the MissionProvider protocol with checkpoint/resume and provenance.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="execute a canned mission end-to-end")
    run_parser.add_argument("mission", help=f"mission name; one of {', '.join(MISSION_NAMES)}")
    run_parser.add_argument(
        "--checkpoint-dir",
        default=None,
        help="state dir for checkpoint/resume (resumes from the last completed step)",
    )
    run_parser.add_argument(
        "--output-dir",
        default=None,
        help="where to write mission_report.json + provenance/ (default: <root>/output/data)",
    )

    subparsers.add_parser("list", help="list canned missions")
    return parser


def exit_code_for(report: MissionReport) -> int:
    """Process exit code: 0 when every debrief verdict is ``"pass"``, else 1."""
    return 0 if report.all_verdicts_pass() else 1


def run_mission_command(args: argparse.Namespace) -> int:
    """Execute one mission and return the process exit code (0 = all pass)."""
    mission = get_mission(args.mission)
    providers: dict[str, MissionProvider] = {
        package_id: get_provider(package_id) for package_id in mission.package_ids()
    }
    checkpoint_dir = Path(args.checkpoint_dir) if args.checkpoint_dir else None
    runner = MissionRunner(providers, checkpoint_dir=checkpoint_dir)
    report: MissionReport = runner.run(mission)

    print(report.consolidated_debrief())

    output_dir = Path(args.output_dir) if args.output_dir else _project_root() / "output" / "data"
    write_mission_report(report, output_dir / DEFAULT_REPORT_FILENAME)
    write_outcome_records(report, output_dir / "provenance")
    return exit_code_for(report)


def list_missions_command(args: argparse.Namespace) -> int:
    """Print the mission registry and return 0."""
    del args  # unused; kept for a uniform command signature
    for name in MISSION_NAMES:
        chain = " → ".join(MISSIONS[name].package_ids())
        print(f"{name:<20} {chain}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point (also used by scripts/run_mission.py)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        try:
            return run_mission_command(args)
        except UnknownMissionError as exc:
            parser.error(str(exc))
    if args.command == "list":
        return list_missions_command(args)
    parser.print_help()  # pragma: no cover - argparse enforces a subcommand
    return 2  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())

"""Named canned missions (pure core).

OPERATION OMNIBUS is the flagship: a three-film chain whose dependency edges
carry recon outputs forward —

    goldfinger (recon market) -> goldeneye (EMP resilience) -> no_time_to_die (bioweapon countermeasure)

— and which produces a single consolidated debrief (see
:meth:`bond_orchestrator.runner.MissionReport.consolidated_debrief`).
"""

from __future__ import annotations

from .protocol import Mission, MissionPackage

OPERATION_OMNIBUS = Mission(
    name="OPERATION_OMNIBUS",
    packages=(
        MissionPackage(
            id="goldfinger",
            title="GOLDFINGER",
            objective="recon the gold market",
        ),
        MissionPackage(
            id="goldeneye",
            title="GOLDENEYE",
            objective="assess EMP resilience",
            depends_on=("goldfinger",),
        ),
        MissionPackage(
            id="no_time_to_die",
            title="NO TIME TO DIE",
            objective="develop bioweapon countermeasure",
            depends_on=("goldeneye",),
        ),
    ),
)

OPERATION_DIAMOND = Mission(
    name="OPERATION_DIAMOND",
    packages=(
        MissionPackage(
            id="thunderball",
            title="THUNDERBALL",
            objective="salvage lost warheads",
        ),
        MissionPackage(
            id="from_russia_with_love",
            title="FROM RUSSIA WITH LOVE",
            objective="map the Orient Express network",
        ),
        MissionPackage(
            id="spectre",
            title="SPECTRE",
            objective="synthesize counterintelligence",
            depends_on=("thunderball", "from_russia_with_love"),
        ),
    ),
)

OPERATION_SINGLET = Mission(
    name="OPERATION_SINGLET",
    packages=(
        MissionPackage(
            id="goldfinger",
            title="GOLDFINGER",
            objective="recon the gold market",
        ),
    ),
)

MISSIONS: dict[str, Mission] = {
    mission.name: mission for mission in (OPERATION_OMNIBUS, OPERATION_DIAMOND, OPERATION_SINGLET)
}

MISSION_NAMES: tuple[str, ...] = tuple(sorted(MISSIONS))


class UnknownMissionError(KeyError):
    """Raised when a mission name is not in the registry."""


def get_mission(name: str) -> Mission:
    """Return the canned mission registered under ``name``.

    Raises:
        UnknownMissionError: No mission is registered under ``name``.
    """
    mission = MISSIONS.get(name)
    if mission is None:
        available = ", ".join(MISSION_NAMES)
        raise UnknownMissionError(f"unknown mission {name!r}; available: {available}")
    return mission

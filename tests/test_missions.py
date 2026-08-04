"""Tests for the canned mission registry."""

from __future__ import annotations

from typing import cast

import pytest

from bond_orchestrator.missions import (
    MISSION_NAMES,
    MISSIONS,
    OPERATION_DIAMOND,
    OPERATION_OMNIBUS,
    OPERATION_SINGLET,
    UnknownMissionError,
    get_mission,
)


class TestOperationOmnibus:
    """OPERATION OMNIBUS: goldfinger -> goldeneye -> no_time_to_die chain."""

    def test_three_packages_in_chain(self) -> None:
        assert OPERATION_OMNIBUS.package_ids() == (
            "goldfinger",
            "goldeneye",
            "no_time_to_die",
        )
        assert OPERATION_OMNIBUS.package("goldfinger").depends_on == ()
        assert OPERATION_OMNIBUS.package("goldeneye").depends_on == ("goldfinger",)
        assert OPERATION_OMNIBUS.package("no_time_to_die").depends_on == ("goldeneye",)

    def test_objectives(self) -> None:
        assert "recon the gold market" in OPERATION_OMNIBUS.package("goldfinger").objective
        assert "EMP resilience" in OPERATION_OMNIBUS.package("goldeneye").objective
        assert "bioweapon countermeasure" in OPERATION_OMNIBUS.package("no_time_to_die").objective

    def test_unknown_package_raises(self) -> None:
        with pytest.raises(KeyError):
            OPERATION_OMNIBUS.package("moonraker")


class TestOtherMissions:
    def test_diamond_shape(self) -> None:
        assert OPERATION_DIAMOND.package_ids() == (
            "thunderball",
            "from_russia_with_love",
            "spectre",
        )
        assert OPERATION_DIAMOND.package("spectre").depends_on == (
            "thunderball",
            "from_russia_with_love",
        )

    def test_singlet_shape(self) -> None:
        assert OPERATION_SINGLET.package_ids() == ("goldfinger",)

    def test_registry_contains_all_three(self) -> None:
        assert set(MISSION_NAMES) == {
            "OPERATION_OMNIBUS",
            "OPERATION_DIAMOND",
            "OPERATION_SINGLET",
        }
        assert len(MISSIONS) == 3

    def test_get_mission_roundtrip(self) -> None:
        assert get_mission("OPERATION_OMNIBUS") is OPERATION_OMNIBUS

    def test_get_mission_unknown(self) -> None:
        with pytest.raises(UnknownMissionError, match="OPERATION_GHOST"):
            get_mission("OPERATION_GHOST")

    def test_mission_serialization(self) -> None:
        as_dict = OPERATION_OMNIBUS.as_dict()
        assert as_dict["name"] == "OPERATION_OMNIBUS"
        packages = cast("list[dict[str, object]]", as_dict["packages"])
        assert [p["id"] for p in packages] == [
            "goldfinger",
            "goldeneye",
            "no_time_to_die",
        ]

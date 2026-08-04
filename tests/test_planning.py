"""Tests for parallel-stage planning over the film DAG."""

from __future__ import annotations

from typing import cast

import pytest

from bond_orchestrator.graph import CycleError
from bond_orchestrator.missions import OPERATION_DIAMOND, OPERATION_OMNIBUS, OPERATION_SINGLET
from bond_orchestrator.planning import (
    Stage,
    StagePlan,
    build_stage_plan,
    plan_stages,
)
from bond_orchestrator.protocol import Mission, MissionPackage


class TestPlanStages:
    def test_omnibus_chain_is_three_serial_stages(self) -> None:
        plan = build_stage_plan(OPERATION_OMNIBUS)
        assert plan.mission_name == "OPERATION_OMNIBUS"
        assert [stage.packages for stage in plan.stages] == [
            ("goldfinger",),
            ("goldeneye",),
            ("no_time_to_die",),
        ]
        assert plan.max_parallelism() == 1
        assert plan.critical_path_length() == 3

    def test_diamond_has_two_stages_with_parallel_leaves(self) -> None:
        plan = build_stage_plan(OPERATION_DIAMOND)
        assert plan.stages[0].packages == ("from_russia_with_love", "thunderball")
        assert plan.stages[1].packages == ("spectre",)
        assert plan.max_parallelism() == 2
        assert plan.critical_path_length() == 2

    def test_singlet_is_one_stage(self) -> None:
        plan = build_stage_plan(OPERATION_SINGLET)
        assert len(plan.stages) == 1
        assert plan.stages[0].packages == ("goldfinger",)
        assert plan.max_parallelism() == 1

    def test_stage_indices_are_one_based(self) -> None:
        plan = build_stage_plan(OPERATION_DIAMOND)
        assert [stage.index for stage in plan.stages] == [1, 2]

    def test_empty_graph_plans_to_no_stages(self) -> None:
        from bond_orchestrator.graph import FilmGraph

        assert plan_stages(FilmGraph(nodes=(), edges=())) == ()

    def test_deterministic_across_plans(self) -> None:
        assert build_stage_plan(OPERATION_DIAMOND).as_dict() == build_stage_plan(OPERATION_DIAMOND).as_dict()

    def test_declaration_order_independent(self) -> None:
        reversed_mission = Mission(
            name="OPERATION_DIAMOND",
            packages=tuple(reversed(OPERATION_DIAMOND.packages)),
        )
        assert build_stage_plan(reversed_mission).as_dict() == build_stage_plan(OPERATION_DIAMOND).as_dict()

    def test_cycle_raises_with_path(self) -> None:
        mission = Mission(
            name="OPERATION_LOOP",
            packages=(
                MissionPackage(id="a", title="A", objective="x", depends_on=("b",)),
                MissionPackage(id="b", title="B", objective="x", depends_on=("a",)),
            ),
        )
        with pytest.raises(CycleError) as excinfo:
            build_stage_plan(mission)
        assert excinfo.value.cycle == ("a", "b", "a")


class TestStagePlanSerialization:
    def test_as_dict_roundtrip(self) -> None:
        plan = build_stage_plan(OPERATION_DIAMOND)
        as_dict = plan.as_dict()
        assert as_dict["mission_name"] == "OPERATION_DIAMOND"
        assert as_dict["max_parallelism"] == 2
        assert as_dict["critical_path_length"] == 2
        stages = cast("list[dict[str, object]]", as_dict["stages"])
        assert stages[0] == {
            "index": 1,
            "packages": ["from_russia_with_love", "thunderball"],
        }

    def test_stage_as_dict(self) -> None:
        stage = Stage(index=1, packages=("goldfinger", "goldeneye"))
        assert stage.as_dict() == {"index": 1, "packages": ["goldfinger", "goldeneye"]}

    def test_render_contains_stages_and_parallelism(self) -> None:
        text = build_stage_plan(OPERATION_DIAMOND).render()
        assert "OPERATION_DIAMOND stage plan" in text
        assert "stage 1: from_russia_with_love | thunderball" in text
        assert "stage 2: spectre" in text
        assert "max parallelism: 2 | critical path: 2 stages" in text


class TestStagePlanEmpty:
    def test_empty_plan_metrics(self) -> None:
        plan = StagePlan(mission_name="EMPTY", stages=())
        assert plan.max_parallelism() == 0
        assert plan.critical_path_length() == 0
        assert plan.as_dict()["stages"] == []

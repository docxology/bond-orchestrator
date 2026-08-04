"""Tests for film DAG construction and deterministic topological ordering."""

from __future__ import annotations

import pytest

from bond_orchestrator.graph import (
    CycleError,
    FilmGraph,
    GraphError,
    UnknownNodeError,
    build_film_graph,
)
from bond_orchestrator.missions import OPERATION_DIAMOND, OPERATION_OMNIBUS
from bond_orchestrator.protocol import MissionPackage


class TestBuildFilmGraph:
    def test_omnibus_chain(self) -> None:
        graph = build_film_graph(OPERATION_OMNIBUS.packages)
        assert graph.nodes == ("goldfinger", "goldeneye", "no_time_to_die")
        assert ("goldfinger", "goldeneye") in graph.edges
        assert ("goldeneye", "no_time_to_die") in graph.edges

    def test_diamond_edges(self) -> None:
        graph = build_film_graph(OPERATION_DIAMOND.packages)
        assert ("thunderball", "spectre") in graph.edges
        assert ("from_russia_with_love", "spectre") in graph.edges

    def test_self_dependency_rejected(self) -> None:
        packages = (MissionPackage(id="a", title="A", objective="x", depends_on=("a",)),)
        with pytest.raises(GraphError, match="depends on itself"):
            build_film_graph(packages)

    def test_unknown_dependency_rejected(self) -> None:
        packages = (MissionPackage(id="a", title="A", objective="x", depends_on=("ghost",)),)
        with pytest.raises(UnknownNodeError, match="ghost"):
            build_film_graph(packages)

    def test_cycle_rejected(self) -> None:
        packages = (
            MissionPackage(id="a", title="A", objective="x", depends_on=("b",)),
            MissionPackage(id="b", title="B", objective="x", depends_on=("a",)),
        )
        with pytest.raises(CycleError, match="cycle"):
            build_film_graph(packages)

    def test_duplicate_nodes_deduplicated(self) -> None:
        a = MissionPackage(id="a", title="A", objective="x")
        graph = build_film_graph((a, a))
        assert graph.nodes == ("a",)


class TestTopologicalOrder:
    def test_omnibus_order(self) -> None:
        graph = build_film_graph(OPERATION_OMNIBUS.packages)
        assert graph.topological_order() == ("goldfinger", "goldeneye", "no_time_to_die")

    def test_diamond_order_leaves_before_join(self) -> None:
        graph = build_film_graph(OPERATION_DIAMOND.packages)
        order = graph.topological_order()
        assert order[0] in ("thunderball", "from_russia_with_love")
        assert order[1] in ("thunderball", "from_russia_with_love")
        assert order[2] == "spectre"

    def test_order_is_declaration_order_independent(self) -> None:
        """Reversed declaration yields the same canonical topological order."""
        packages = tuple(reversed(OPERATION_DIAMOND.packages))
        graph = build_film_graph(packages)
        assert graph.topological_order() == (
            "from_russia_with_love",
            "thunderball",
            "spectre",
        )

    def test_dependencies_and_dependents(self) -> None:
        graph = build_film_graph(OPERATION_OMNIBUS.packages)
        assert graph.dependencies("goldeneye") == ("goldfinger",)
        assert graph.dependents("goldfinger") == ("goldeneye",)
        assert graph.dependencies("goldfinger") == ()

    def test_serialization(self) -> None:
        graph = build_film_graph(OPERATION_OMNIBUS.packages)
        as_dict = graph.as_dict()
        assert as_dict["nodes"] == ["goldfinger", "goldeneye", "no_time_to_die"]
        assert as_dict["topological_order"] == [
            "goldfinger",
            "goldeneye",
            "no_time_to_die",
        ]

    def test_empty_graph(self) -> None:
        graph = FilmGraph(nodes=(), edges=())
        assert graph.topological_order() == ()

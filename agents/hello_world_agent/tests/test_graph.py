"""Pure graph-execution tests (spec 0016, AC-0016-06; INV-0016-01, 02)."""

from __future__ import annotations

import pytest
from hello_world_agent.domain.models import AgentState
from hello_world_agent.graph import build_graph
from pydantic import ValidationError


def test_graph_runs_both_nodes_in_order() -> None:
    graph = build_graph()

    result = graph.invoke(AgentState(name="Ada"))

    assert result["greeting"] == "Hello, Ada!"
    assert result["node_path"] == ["validate_input", "compose_greeting"]


def test_graph_default_name() -> None:
    graph = build_graph()

    result = graph.invoke(AgentState(name="world"))

    assert result["greeting"] == "Hello, world!"


def test_graph_is_deterministic() -> None:
    graph = build_graph()

    first = graph.invoke(AgentState(name="Ada"))
    second = graph.invoke(AgentState(name="Ada"))

    assert first == second


@pytest.mark.parametrize("name", ["", "a" * 101])
def test_state_rejects_out_of_bounds_name(name: str) -> None:
    with pytest.raises(ValidationError):
        AgentState(name=name)

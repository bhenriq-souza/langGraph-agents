"""Graph factory for the hello-world agent (spec 0016, INV-0016-01).

Builds a fixed, acyclic two-node `StateGraph`: `validate_input` ->
`compose_greeting`. No cycles, no conditional branching.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from hello_world_agent.domain.models import AgentState
from hello_world_agent.domain.nodes import compose_greeting, validate_input


def build_graph() -> CompiledStateGraph:
    """Compile the hello-world agent graph."""
    builder = StateGraph(AgentState)
    builder.add_node("validate_input", validate_input)
    builder.add_node("compose_greeting", compose_greeting)
    builder.add_edge(START, "validate_input")
    builder.add_edge("validate_input", "compose_greeting")
    builder.add_edge("compose_greeting", END)
    return builder.compile()

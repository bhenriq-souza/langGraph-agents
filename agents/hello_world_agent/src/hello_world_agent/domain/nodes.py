"""Pure node functions for the hello-world agent graph (spec 0016, INV-0016-02).

No I/O, no network calls: each node reads `AgentState` and returns a partial
update. `AgentState.name` bounds are already enforced by the schema itself at
the graph boundary, so `validate_input` marks that checkpoint as passed rather
than re-implementing the check.
"""

from __future__ import annotations

from hello_world_agent.domain.models import AgentState


def validate_input(state: AgentState) -> dict[str, object]:
    """First node in the DAG: records that the validated-input checkpoint ran."""
    return {"node_path": [*state.node_path, "validate_input"]}


def compose_greeting(state: AgentState) -> dict[str, object]:
    """Second node in the DAG: builds the greeting from the validated name."""
    return {
        "greeting": f"Hello, {state.name}!",
        "node_path": [*state.node_path, "compose_greeting"],
    }

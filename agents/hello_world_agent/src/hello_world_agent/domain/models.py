"""Graph state contract for the hello-world agent (spec 0016)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """State threaded through the `hello_world_agent` graph."""

    name: str = Field(min_length=1, max_length=100)
    greeting: str | None = None
    node_path: list[str] = Field(default_factory=list)

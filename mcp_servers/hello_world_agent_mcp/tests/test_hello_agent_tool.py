"""AC-0016-01, 02, 05 and INV-0016-05 — `hello_agent` tool over an in-memory session."""

from datetime import datetime
from typing import Any

import pytest
from hello_world_agent_mcp.server import INVALID_INPUT, create_server
from hello_world_agent_mcp.settings import ServerSettings
from mcp.server.lowlevel.server import Server
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import CallToolResult

pytestmark = pytest.mark.anyio


def _lowlevel_server() -> Server[Any, Any]:
    return create_server(ServerSettings())._mcp_server  # pyright: ignore[reportPrivateUsage]


def _assert_invalid_input(result: CallToolResult) -> None:
    # INV-0016-05: tool errors carry a stable code and no success fields.
    assert result.isError is True
    assert result.structuredContent is None
    assert result.content[0].type == "text"
    assert result.content[0].text.startswith(INVALID_INPUT)


async def test_tools_list_exposes_exactly_hello_agent_with_documented_schema() -> None:
    async with create_connected_server_and_client_session(_lowlevel_server()) as session:
        listed = await session.list_tools()
        assert [tool.name for tool in listed.tools] == ["hello_agent"]
        schema = listed.tools[0].inputSchema
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        name_schema = schema["properties"]["name"]
        assert name_schema["type"] == "string"
        assert name_schema["default"] == "world"
        assert name_schema["minLength"] == 1
        assert name_schema["maxLength"] == 100


async def test_hello_agent_with_name_returns_greeting_and_node_path() -> None:
    async with create_connected_server_and_client_session(_lowlevel_server()) as session:
        result = await session.call_tool("hello_agent", {"name": "Ada"})
        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent["greeting"] == "Hello, Ada!"
        # Evidence the graph executed, not a direct response.
        assert result.structuredContent["node_path"] == ["validate_input", "compose_greeting"]
        assert result.structuredContent["server_version"]
        # ISO-8601 UTC timestamp, e.g. 2026-07-06T14:00:00.000000Z
        parsed = datetime.fromisoformat(result.structuredContent["timestamp"])
        assert parsed.tzinfo is not None


async def test_hello_agent_without_arguments_defaults_to_world() -> None:
    async with create_connected_server_and_client_session(_lowlevel_server()) as session:
        result = await session.call_tool("hello_agent", {})
        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent["greeting"] == "Hello, world!"


async def test_empty_name_returns_invalid_input() -> None:
    async with create_connected_server_and_client_session(_lowlevel_server()) as session:
        _assert_invalid_input(await session.call_tool("hello_agent", {"name": ""}))


async def test_name_longer_than_100_chars_returns_invalid_input() -> None:
    async with create_connected_server_and_client_session(_lowlevel_server()) as session:
        _assert_invalid_input(await session.call_tool("hello_agent", {"name": "x" * 101}))


async def test_unknown_field_returns_invalid_input() -> None:
    async with create_connected_server_and_client_session(_lowlevel_server()) as session:
        result = await session.call_tool("hello_agent", {"name": "Ada", "shout": True})
        _assert_invalid_input(result)

"""AC-0016-03 — streamable HTTP transport exercised over ASGI, no network."""

from typing import Any

import httpx
import pytest
from hello_world_agent_mcp.server import create_server
from hello_world_agent_mcp.settings import ServerSettings

pytestmark = pytest.mark.anyio

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-06-18",
}

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "0.0.0"},
    },
}


async def _post(client: httpx.AsyncClient, payload: dict[str, Any]) -> httpx.Response:
    return await client.post("/mcp", json=payload, headers=HEADERS)


async def test_http_transport_serves_initialize_tools_list_and_tools_call() -> None:
    settings = ServerSettings.from_env({"AGENTS_MCP_TRANSPORT": "http"})
    server = create_server(settings)
    app = server.streamable_http_app()
    async with server.session_manager.run():
        transport = httpx.ASGITransport(app=app)
        base_url = f"http://{settings.host}:{settings.port}"
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
            init = await _post(client, INITIALIZE)
            assert init.status_code == 200
            assert init.json()["result"]["serverInfo"]["name"] == "hello-world-agent"

            listed = await _post(
                client, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            )
            assert listed.status_code == 200
            tools = listed.json()["result"]["tools"]
            assert [tool["name"] for tool in tools] == ["hello_agent"]

            called = await _post(
                client,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "hello_agent", "arguments": {"name": "Ada"}},
                },
            )
            assert called.status_code == 200
            result = called.json()["result"]
            assert result["isError"] is False
            assert result["structuredContent"]["greeting"] == "Hello, Ada!"
            assert result["structuredContent"]["node_path"] == [
                "validate_input",
                "compose_greeting",
            ]

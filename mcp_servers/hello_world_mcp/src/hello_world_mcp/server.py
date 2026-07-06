"""Hello World MCP server — remote-hosting reference (spec 0015).

Thin adapter per INV-0015-01: request validation → greeting construction → response.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import UTC, datetime
from importlib.metadata import version
from typing import Any

import structlog
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from hello_world_mcp.settings import ServerSettings

SERVER_NAME = "hello-world"
INVALID_INPUT = "INVALID_INPUT"
INTERNAL_ERROR = "INTERNAL_ERROR"

_logger = structlog.get_logger("hello_world_mcp")


class HelloInput(BaseModel):
    """Input contract of the `hello` tool (spec 0015)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="world", min_length=1, max_length=100)


class HelloResponse(BaseModel):
    """Output contract of the `hello` tool (spec 0015)."""

    greeting: str
    server_version: str
    timestamp: str


def build_hello_response(params: HelloInput) -> HelloResponse:
    """Construct the greeting — the only logic this server owns (INV-0015-01)."""
    return HelloResponse(
        greeting=f"Hello, {params.name}!",
        server_version=version("hello-world-mcp"),
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    )


def _invalid_input_message(error: ValidationError) -> str:
    unknown = sorted(
        {str(item["loc"][0]) for item in error.errors() if item["type"] == "extra_forbidden"}
    )
    if unknown:
        fields = ", ".join(f"'{field}'" for field in unknown)
        return f"{INVALID_INPUT}: Unknown parameter(s) {fields}."
    return f"{INVALID_INPUT}: Parameter 'name' must be between 1 and 100 characters."


def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        isError=True,
    )


def create_server(settings: ServerSettings) -> FastMCP:
    """Create the FastMCP server with transports and the `hello` tool wired."""
    transport_security: TransportSecuritySettings | None = None
    if settings.allowed_hosts:
        transport_security = TransportSecuritySettings(allowed_hosts=list(settings.allowed_hosts))

    server = FastMCP(
        name=SERVER_NAME,
        host=settings.host,
        port=settings.port,
        stateless_http=settings.stateless,
        json_response=True,
        transport_security=transport_security,
    )

    # Handlers go on the underlying lowlevel server: FastMCP's default tool
    # pipeline neither rejects unknown input fields (AC-0015-05) nor returns
    # the stable error codes required by INV-0015-04.
    lowlevel = server._mcp_server  # pyright: ignore[reportPrivateUsage]

    @lowlevel.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="hello",
                description="Return a greeting for the given name.",
                inputSchema=HelloInput.model_json_schema(),
                outputSchema=HelloResponse.model_json_schema(),
            )
        ]

    @lowlevel.call_tool(validate_input=False)
    async def call_tool(tool_name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        correlation_id = uuid.uuid4().hex
        log = _logger.bind(correlation_id=correlation_id, tool=tool_name)
        if tool_name != "hello":
            log.info("tool_call", outcome="invalid_input", reason="unknown_tool")
            return _error_result(f"{INVALID_INPUT}: Unknown tool '{tool_name}'.")
        try:
            params = HelloInput.model_validate(arguments)
        except ValidationError as exc:
            log.info("tool_call", outcome="invalid_input", argument_keys=sorted(arguments))
            return _error_result(_invalid_input_message(exc))
        try:
            response = build_hello_response(params)
        except Exception:
            log.exception("tool_call", outcome="internal_error")
            return _error_result(
                f"{INTERNAL_ERROR}: An unexpected error occurred (correlation id {correlation_id})."
            )
        payload = response.model_dump()
        log.info("tool_call", outcome="success", name_length=len(params.name))
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(payload, indent=2))],
            structuredContent=payload,
        )

    return server


def _configure_logging() -> None:
    # Logs must go to stderr: in stdio mode stdout is the MCP protocol channel.
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


def main() -> None:
    """Script entrypoint (`hello-world-mcp`)."""
    _configure_logging()
    settings = ServerSettings.from_env()
    server = create_server(settings)
    server.run(transport="streamable-http" if settings.transport == "http" else "stdio")

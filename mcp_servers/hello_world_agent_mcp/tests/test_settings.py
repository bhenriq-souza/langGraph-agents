"""AC-0016-04, INV-0016-03 and INV-0016-06 — environment-driven settings resolution."""

import pytest
from hello_world_agent_mcp.server import create_server
from hello_world_agent_mcp.settings import ServerSettings


def test_defaults_bind_loopback_stdio() -> None:
    settings = ServerSettings.from_env({})
    assert settings.transport == "stdio"
    assert settings.host == "127.0.0.1"  # INV-0016-03
    assert settings.port == 8767
    assert settings.stateless is True
    assert settings.allowed_hosts == ()


def test_port_env_var_overrides_agents_mcp_port() -> None:
    settings = ServerSettings.from_env({"PORT": "9000", "AGENTS_MCP_PORT": "9001"})
    assert settings.port == 9000


def test_agents_mcp_port_used_when_port_unset() -> None:
    settings = ServerSettings.from_env({"AGENTS_MCP_PORT": "9001"})
    assert settings.port == 9001


def test_http_transport_selected_from_env() -> None:
    settings = ServerSettings.from_env({"AGENTS_MCP_TRANSPORT": "http"})
    assert settings.transport == "http"


def test_unknown_transport_rejected() -> None:
    with pytest.raises(ValueError, match="AGENTS_MCP_TRANSPORT"):
        ServerSettings.from_env({"AGENTS_MCP_TRANSPORT": "carrier-pigeon"})


def test_non_loopback_host_accepted() -> None:
    settings = ServerSettings.from_env({"AGENTS_MCP_HOST": "0.0.0.0"})
    assert settings.host == "0.0.0.0"


def test_non_loopback_host_with_stateful_mode_rejected() -> None:
    # INV-0016-06: horizontal-scaling safety.
    with pytest.raises(ValueError, match="INV-0016-06"):
        ServerSettings.from_env({"AGENTS_MCP_HOST": "0.0.0.0", "AGENTS_MCP_STATELESS": "false"})


def test_stateful_mode_allowed_on_loopback() -> None:
    settings = ServerSettings.from_env({"AGENTS_MCP_STATELESS": "false"})
    assert settings.stateless is False


def test_allowed_hosts_parsed_from_comma_separated_list() -> None:
    settings = ServerSettings.from_env(
        {"AGENTS_MCP_ALLOWED_HOSTS": "tunnel.example, mcp.example.dev"}
    )
    assert settings.allowed_hosts == ("tunnel.example", "mcp.example.dev")


def test_allowed_hosts_reach_transport_security_settings() -> None:
    server = create_server(ServerSettings(allowed_hosts=("tunnel.example",)))
    security = server.settings.transport_security
    assert security is not None
    assert security.allowed_hosts == ["tunnel.example"]


def test_settings_reach_fastmcp_transport_configuration() -> None:
    server = create_server(ServerSettings(transport="http", host="0.0.0.0", port=9000))
    assert server.settings.host == "0.0.0.0"
    assert server.settings.port == 9000
    assert server.settings.stateless_http is True
    assert server.settings.json_response is True
    assert server.settings.streamable_http_path == "/mcp"

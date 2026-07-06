"""Environment-driven transport configuration for the hello-world-agent MCP server (spec 0016)."""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8767

Transport = Literal["stdio", "http"]

_TRANSPORTS: tuple[Transport, ...] = ("stdio", "http")
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _parse_bool(raw: str, env_var: str) -> bool:
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ValueError(f"{env_var} must be a boolean value, got {raw!r}.")


@dataclass(frozen=True)
class ServerSettings:
    """Resolved transport settings, per the spec 0016 configuration table."""

    transport: Transport = "stdio"
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    stateless: bool = True
    allowed_hosts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.transport not in _TRANSPORTS:
            raise ValueError(
                f"AGENTS_MCP_TRANSPORT must be one of {_TRANSPORTS}, got {self.transport!r}."
            )
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {self.port}.")
        # INV-0016-06: a non-loopback bind must run stateless so multi-instance
        # deployments never rely on in-memory session affinity.
        if not _is_loopback(self.host) and not self.stateless:
            raise ValueError(
                f"Binding to non-loopback host {self.host!r} requires stateless mode "
                "(AGENTS_MCP_STATELESS=true); see INV-0016-06."
            )

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ServerSettings:
        """Resolve settings from the environment. Port precedence: PORT > AGENTS_MCP_PORT > 8767."""
        source: Mapping[str, str] = os.environ if env is None else env
        transport = source.get("AGENTS_MCP_TRANSPORT", "stdio").strip().lower()
        if transport not in _TRANSPORTS:
            raise ValueError(
                f"AGENTS_MCP_TRANSPORT must be one of {_TRANSPORTS}, got {transport!r}."
            )
        raw_port = source.get("PORT", "").strip() or source.get("AGENTS_MCP_PORT", "").strip()
        allowed_hosts = tuple(
            item.strip()
            for item in source.get("AGENTS_MCP_ALLOWED_HOSTS", "").split(",")
            if item.strip()
        )
        return cls(
            transport=transport,
            host=source.get("AGENTS_MCP_HOST", DEFAULT_HOST).strip(),
            port=int(raw_port) if raw_port else DEFAULT_PORT,
            stateless=_parse_bool(
                source.get("AGENTS_MCP_STATELESS", "true"), "AGENTS_MCP_STATELESS"
            ),
            allowed_hosts=allowed_hosts,
        )

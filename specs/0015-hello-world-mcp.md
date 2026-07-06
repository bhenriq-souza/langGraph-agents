---
id: "0015"
title: Hello World MCP server
status: draft
depends_on: ["0002", "0013", "0014"]
---

# 0015 — Hello World MCP Server

## Goal

A minimal, permanent reference MCP server proving the remote-hosting path for this monorepo: streamable HTTP transport exposed through an HTTPS tunnel, registration in Gemini Enterprise (or any MCP-compatible AI workspace), and containerised deployment on Cloud Run as a PoC. The server exposes one tool (`hello`) that returns a greeting, exercising the full transport stack without introducing business logic. It serves as the living template for future remotely-hosted MCP members and as a learning vehicle before the production server (T-0002-02).

## Scope / Non-goals

- **In scope:** `mcp_servers/hello_world_mcp` workspace member; one `hello` tool; stdio (default) and streamable HTTP transports with env-configurable bind address, port, allowed hosts and statelessness; HTTPS tunnel runbook for Gemini Enterprise registration; Cloud Run container PoC.
- **Non-goals:**
  - **Authentication / authorization** — explicitly an accepted risk while the only tool is a constant greeting with no data access or side effects. Auth must be revisited before any real tool is added to this server.
  - IaC beyond a `Dockerfile` and manual `gcloud run deploy` commands.
  - Business logic of any kind.
  - Persistence or session state.

## Contracts

### Server metadata

- Package: `mcp_servers/hello_world_mcp`, dist `hello-world-mcp`, import `hello_world_mcp`.
- Server name: `hello-world`.
- Script entrypoint: `hello-world-mcp = "hello_world_mcp.server:main"`.
- SDK: official MCP Python SDK (`FastMCP`), same as spec 0002.
- The server is a thin adapter: request validation → tool execution → response. No business logic in this package (INV-0015-01).

### Transport & configuration

| Env var | Default | Description |
|---|---|---|
| `AGENTS_MCP_TRANSPORT` | `stdio` | `http` enables streamable HTTP |
| `AGENTS_MCP_HOST` | `127.0.0.1` | bind address; set `0.0.0.0` for containerised deployment |
| `PORT` | — | Cloud Run injects this; takes precedence over `AGENTS_MCP_PORT` |
| `AGENTS_MCP_PORT` | `8766` | bind port (chosen to avoid conflict with spec 0002 port 8765) |
| `AGENTS_MCP_STATELESS` | `true` | stateless streamable HTTP; safe for horizontal scaling |
| `AGENTS_MCP_ALLOWED_HOSTS` | unset | comma-separated Host header values to allow through DNS-rebinding protection (e.g. tunnel hostname) |

Port precedence: `PORT` → `AGENTS_MCP_PORT` → `8766`. The streamable HTTP path is always `/mcp`. HTTP mode uses `json_response=True` (plain JSON replies, not SSE streams), simplifying integration with AI workspaces and `curl`.

**DNS-rebinding protection:** the MCP Python SDK automatically enables Host-header validation when the server binds to a loopback address. HTTPS tunnels forward the tunnel's public hostname in the Host header, causing the SDK to reject requests (HTTP 421) unless that hostname is listed in `AGENTS_MCP_ALLOWED_HOSTS` or the tunnel is configured to rewrite the Host header to `127.0.0.1`. The runbook (T-0015-02) documents the exact commands for ngrok and cloudflared.

### Tool: `hello`

**Input — `HelloInput` (Pydantic, `extra="forbid"`):**

| Field | Type | Default | Constraints |
|---|---|---|---|
| `name` | `str` | `"world"` | 1 ≤ len ≤ 100 |

**Output — `HelloResponse`:**

| Field | Type | Notes |
|---|---|---|
| `greeting` | `str` | `"Hello, {name}!"` |
| `server_version` | `str` | package version via `importlib.metadata` |
| `timestamp` | `str` | ISO-8601 UTC timestamp of the call |

**Example:**

```json
// Request
{"name": "Ada"}

// Response
{
  "greeting": "Hello, Ada!",
  "server_version": "0.1.0",
  "timestamp": "2026-07-06T14:00:00.000000Z"
}
```

Default invocation (no arguments): returns `"Hello, world!"`.

### Language policy note

The `greeting` field is a factual string with no probabilistic content. The spec-0000 cautious-language policy (estimate / signals, never certainty / proof) is trivially satisfied; this is stated explicitly so reviewers know it was considered.

### Logging

One structured log entry per invocation with correlation id, sanitized parameters, and outcome, following the pattern established in spec 0002. The server uses `structlog` directly as a dependency (not via `packages/core`, which is not yet implemented).

## Invariants

- **INV-0015-01** — thin server: `hello_world_mcp` contains no logic beyond greeting construction and transport wiring.
- **INV-0015-02** — bind safety: the default bind address is `127.0.0.1`; non-loopback binding requires an explicit `AGENTS_MCP_HOST` override. This invariant governs `hello_world_mcp` only and does not amend INV-0002-03, which remains scoped to `ai_repo_auditor_mcp`.
- **INV-0015-03** — horizontal-scaling safety: when bound to a non-loopback address, the server runs in stateless streamable-HTTP mode (`stateless_http=True`), ensuring no in-memory session affinity. Cloud Run multi-instance deployments are therefore safe.
- **INV-0015-04** — error separation: tool errors are returned as MCP tool errors with a stable machine-readable code; they are never mixed with success fields (mirrors INV-0002-01).

## Error cases

| Code | Trigger | Message style |
|---|---|---|
| `INVALID_INPUT` | schema / constraint violation (`name` empty or > 100 chars, unknown field) | "Parameter 'name' must be between 1 and 100 characters." |
| `INTERNAL_ERROR` | unexpected exception | generic message + correlation id; details in server logs only |

## Acceptance criteria

- **AC-0015-01** — `uv run hello-world-mcp` starts a stdio server; `tools/list` exposes exactly one tool named `hello` with the documented input schema.
- **AC-0015-02** — `hello({"name": "Ada"})` returns a `HelloResponse` with `greeting == "Hello, Ada!"`; calling with no arguments returns `greeting == "Hello, world!"`.
- **AC-0015-03** — with `AGENTS_MCP_TRANSPORT=http`, the server initialises and responds to `tools/list` and `tools/call` over streamable HTTP at the configured host/port with path `/mcp`.
- **AC-0015-04** — env precedence is honoured: `PORT` overrides `AGENTS_MCP_PORT`; `AGENTS_MCP_HOST=0.0.0.0` is accepted; `AGENTS_MCP_ALLOWED_HOSTS` reaches the SDK transport-security configuration.
- **AC-0015-05** — `name=""` and `name` longer than 100 characters return `INVALID_INPUT`; unknown input fields return `INVALID_INPUT`.
- **AC-0015-06** — the member passes `uv sync` and `uv run pytest`; code meets ruff/pyright/bandit standards of spec 0013.

## Test mapping

| Item | Test module |
|---|---|
| AC-0015-01, 02, 05; INV-0015-04 | `mcp_servers/hello_world_mcp/tests/test_hello_tool.py` (in-memory session via `create_connected_server_and_client_session`) |
| AC-0015-03 | `mcp_servers/hello_world_mcp/tests/test_http_transport.py` (ASGI via `httpx.AsyncClient` + `ASGITransport`, no network) |
| AC-0015-04; INV-0015-02, 03 | `mcp_servers/hello_world_mcp/tests/test_settings.py` |

## Open questions

None.

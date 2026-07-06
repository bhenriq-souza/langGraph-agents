---
id: "0016"
title: Hello World Agent
status: draft
depends_on: ["0013", "0014"]
---

# 0016 — Hello World Agent

## Goal

A minimal, permanent reference component proving that an MCP tool can mount and execute a real LangGraph graph — not just construct a response inline. `hello_world_mcp` (spec 0015) validated the remote-hosting/transport path with a business-logic-free tool; this spec is the next rung: a deterministic two-node `StateGraph`, compiled by a `build_graph()` factory and invoked end-to-end from an MCP tool call, registered and exercised from Odysseus exactly like spec 0015's `hello` tool. It is a learning vehicle for the graph-construction and thin-adapter patterns (specs 0003, 0002) at a scale small enough to need neither an LLM nor a DI container, ahead of the production `ai_repo_auditor` (Phase 1).

## Scope / Non-goals

- **In scope:** `agents/hello_world_agent` workspace member (pure `domain/` state + node functions, `build_graph()` factory building a `langgraph.graph.StateGraph`); `mcp_servers/hello_world_agent_mcp` workspace member exposing one tool that invokes the compiled graph per call; stdio (default) and streamable HTTP transports mirroring spec 0015's env-var contract; an Odysseus runbook extension proving the end-to-end path.
- **Non-goals:**
  - LLM/Ollama calls of any kind — nodes are pure and deterministic. A future spec revision may swap in a real LLM-backed node once `packages/core` and `agents_ollama_client` are implemented (Phase 1).
  - A `dependency-injector` container — unnecessary at two nodes with no external services to wire.
  - Persistence or session state.
  - Authentication/authorization — same accepted risk as spec 0015 (INV-0015 non-goal) while the only tool has no data access or side effects; must be revisited before any real tool is added.
  - Retry/error-recovery policy beyond input validation (no analogue to spec 0007's retry ladder — there is no unreliable external call here).

## Contracts

### Agent package

- Package: `agents/hello_world_agent`, dist `hello-world-agent`, import `hello_world_agent`.
- `domain/models.py` — `AgentState` (Pydantic):

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | `str` | — | 1 ≤ len ≤ 100, set at invocation |
| `greeting` | `str \| None` | `None` | written by `compose_greeting` |
| `node_path` | `list[str]` | `[]` | each node appends its own name on exit |

- `domain/nodes.py` — pure functions, no I/O:
  - `validate_input(state: AgentState) -> AgentState` — re-asserts the `name` invariant (defense in depth; the MCP layer already validated it), appends `"validate_input"` to `node_path`.
  - `compose_greeting(state: AgentState) -> AgentState` — sets `greeting = f"Hello, {state.name}!"`, appends `"compose_greeting"` to `node_path`.
- `graph.py` — `build_graph() -> CompiledStateGraph`: constructs a `StateGraph(AgentState)` with nodes `validate_input`, `compose_greeting` and the fixed edge path `START -> validate_input -> compose_greeting -> END`, then returns `.compile()`. Node names are reused verbatim as the values that appear in `node_path`.

### MCP server

- Package: `mcp_servers/hello_world_agent_mcp`, dist `hello-world-agent-mcp`, import `hello_world_agent_mcp`.
- Server name: `hello-world-agent`.
- Script entrypoint: `hello-world-agent-mcp = "hello_world_agent_mcp.server:main"`.
- SDK: official MCP Python SDK (`FastMCP`), same as specs 0002 and 0015.
- The server is a thin adapter: request validation → `build_graph().invoke(...)` → response mapping. No business logic in this package (INV-0016-04).

### Transport & configuration

Identical env-var contract to spec 0015, reused verbatim (INV-0000 cross-referencing rule), with its own default port to avoid collision with `ai_repo_auditor_mcp` (8765, spec 0002) and `hello_world_mcp` (8766, spec 0015):

| Env var | Default | Description |
|---|---|---|
| `AGENTS_MCP_TRANSPORT` | `stdio` | `http` enables streamable HTTP |
| `AGENTS_MCP_HOST` | `127.0.0.1` | bind address; set `0.0.0.0` for containerised deployment |
| `PORT` | — | takes precedence over `AGENTS_MCP_PORT` |
| `AGENTS_MCP_PORT` | `8767` | bind port |
| `AGENTS_MCP_STATELESS` | `true` | stateless streamable HTTP; safe for horizontal scaling |
| `AGENTS_MCP_ALLOWED_HOSTS` | unset | comma-separated Host header values allowed through DNS-rebinding protection |

Port precedence and Host-header behavior are identical to spec 0015 (`AGENTS_MCP_ALLOWED_HOSTS`/tunnel workaround); the runbook (T-0016-04) reuses the exact commands validated in T-0015-02 rather than re-deriving them.

### Tool: `hello_agent`

**Input — `AgentGreetInput` (Pydantic, `extra="forbid"`):**

| Field | Type | Default | Constraints |
|---|---|---|---|
| `name` | `str` | `"world"` | 1 ≤ len ≤ 100 |

**Output — `AgentGreetResponse`:**

| Field | Type | Notes |
|---|---|---|
| `greeting` | `str` | `"Hello, {name}!"`, produced by the graph, not by the server |
| `node_path` | `list[str]` | `["validate_input", "compose_greeting"]` — evidence that the graph executed, not a direct response |
| `server_version` | `str` | package version via `importlib.metadata` |
| `timestamp` | `str` | ISO-8601 UTC timestamp of the call |

**Example:**

```json
// Request
{"name": "Ada"}

// Response
{
  "greeting": "Hello, Ada!",
  "node_path": ["validate_input", "compose_greeting"],
  "server_version": "0.1.0",
  "timestamp": "2026-07-06T14:00:00.000000Z"
}
```

Default invocation (no arguments): returns `greeting == "Hello, world!"` and the same `node_path`.

### Language policy note

`greeting` and `node_path` are factual, non-probabilistic strings; the spec-0000 cautious-language policy is trivially satisfied (same reasoning as spec 0015).

### Logging

One structured log entry per invocation with correlation id, sanitized parameters, and outcome, following the pattern established in specs 0002 and 0015. Uses `structlog` directly (`packages/core` is not yet implemented).

## Invariants

- **INV-0016-01** — DAG only: `build_graph()` produces an acyclic graph with the fixed linear path `validate_input -> compose_greeting`; no cycles, no dynamic/conditional branching (mirrors INV-0003-01 at minimal scale).
- **INV-0016-02** — pure nodes: node functions perform no I/O, no network calls, no LLM calls; given the same `AgentState` input, the output is deterministic.
- **INV-0016-03** — bind safety: default bind address is `127.0.0.1`; non-loopback binding requires an explicit `AGENTS_MCP_HOST` override (mirrors INV-0015-02; scoped to `hello_world_agent_mcp` only).
- **INV-0016-04** — thin server: `hello_world_agent_mcp` contains no logic beyond input validation, invoking the compiled graph, and response mapping (mirrors INV-0015-01/INV-0002-04).
- **INV-0016-05** — error separation: tool errors are returned as stable MCP tool errors, never mixed with success fields (mirrors INV-0002-01/INV-0015-04).
- **INV-0016-06** — horizontal-scaling safety: when bound to a non-loopback address, the server runs stateless (`stateless_http=True`) (mirrors INV-0015-03).

## Error cases

| Code | Trigger | Message style |
|---|---|---|
| `INVALID_INPUT` | schema/constraint violation (`name` empty or > 100 chars, unknown field) | "Parameter 'name' must be between 1 and 100 characters." |
| `INTERNAL_ERROR` | unexpected exception (incl. graph invocation failure) | generic message + correlation id; details in server logs only |

## Acceptance criteria

- **AC-0016-01** — `uv run hello-world-agent-mcp` starts a stdio server; `tools/list` exposes exactly one tool named `hello_agent` with the documented input schema.
- **AC-0016-02** — `hello_agent({"name": "Ada"})` returns `greeting == "Hello, Ada!"` and `node_path == ["validate_input", "compose_greeting"]`; calling with no arguments returns `greeting == "Hello, world!"` with the same `node_path`.
- **AC-0016-03** — with `AGENTS_MCP_TRANSPORT=http`, the server initialises and responds to `tools/list` and `tools/call` over streamable HTTP at the configured host/port, path `/mcp`.
- **AC-0016-04** — env precedence is honoured identically to spec 0015: `PORT` overrides `AGENTS_MCP_PORT`; `AGENTS_MCP_HOST=0.0.0.0` is accepted; `AGENTS_MCP_ALLOWED_HOSTS` reaches the SDK transport-security configuration.
- **AC-0016-05** — `name=""` and `name` longer than 100 characters return `INVALID_INPUT`; unknown input fields return `INVALID_INPUT`.
- **AC-0016-06** — `agents/hello_world_agent`'s `build_graph().invoke({"name": ...})` is verifiable as a pure unit test, with no MCP layer involved, and returns an `AgentState` whose `node_path` lists both node names in call order.
- **AC-0016-07** — both new members pass `uv sync` and `uv run pytest`; code meets ruff/pyright/bandit standards of spec 0013.
- **AC-0016-08** — end-to-end: the tool is registered in Odysseus (reusing the tunnel/Inspector steps verified in T-0015-02), invoked from a real chat, and the response's `node_path` is documented as evidence that a LangGraph graph — not a direct string construction — produced the answer.

## Test mapping

| Item | Test module |
|---|---|
| AC-0016-06; INV-0016-01, 02 | `agents/hello_world_agent/tests/test_graph.py` |
| AC-0016-01, 02, 05; INV-0016-05 | `mcp_servers/hello_world_agent_mcp/tests/test_hello_agent_tool.py` (in-memory session via `create_connected_server_and_client_session`) |
| AC-0016-03 | `mcp_servers/hello_world_agent_mcp/tests/test_http_transport.py` (ASGI via `httpx.AsyncClient` + `ASGITransport`, no network) |
| AC-0016-04; INV-0016-03, 06 | `mcp_servers/hello_world_agent_mcp/tests/test_settings.py` |
| AC-0016-08 | Manual runbook verification (`mcp_servers/hello_world_agent_mcp/README.md`), not automated |

## Open questions

None.

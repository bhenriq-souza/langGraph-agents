# hello-world-agent-mcp

Runbook for spec 0016 (`hello-world-agent`): proves that an MCP tool call actually invokes a
real, compiled LangGraph `StateGraph` — not a response constructed directly in the server. One
tool (`hello_agent`) wraps `agents/hello_world_agent`'s `build_graph().invoke(...)`; the two
node names it appends to `node_path` (`validate_input`, `compose_greeting`) are the evidence
that the graph executed.

## Start the server

Stdio (default, for hosts that spawn a process):

```bash
uv run --package hello-world-agent-mcp hello-world-agent-mcp
```

HTTP (streamable HTTP, for hosts that connect over the network):

```bash
AGENTS_MCP_TRANSPORT=http AGENTS_MCP_HOST=127.0.0.1 AGENTS_MCP_PORT=8767 \
  uv run --package hello-world-agent-mcp hello-world-agent-mcp
```

The server listens on `http://127.0.0.1:8767/mcp`. See the env var table in spec 0016 (reused
verbatim from spec 0015) for `PORT` precedence, `AGENTS_MCP_STATELESS` and
`AGENTS_MCP_ALLOWED_HOSTS`.

## HTTPS tunnel (ngrok) — Host-header workaround

Same workaround as `hello_world_mcp` (T-0015-02): the MCP Python SDK's DNS-rebinding
protection rejects any request whose `Host` header isn't recognized (`HTTP 421 Invalid Host
header`) when the server binds to a loopback address. A tunnel forwards its own public
hostname in `Host`, so the server must be told to allow it via `AGENTS_MCP_ALLOWED_HOSTS`.

1. Start the server as above (HTTP mode, port 8767).
2. Start the tunnel: `ngrok http 8767`.
3. Restart the server with the tunnel hostname allow-listed:

   ```bash
   AGENTS_MCP_TRANSPORT=http AGENTS_MCP_HOST=127.0.0.1 AGENTS_MCP_PORT=8767 \
     AGENTS_MCP_ALLOWED_HOSTS='<hostname-ngrok>,127.0.0.1:8767,localhost:8767' \
     uv run --package hello-world-agent-mcp hello-world-agent-mcp
   ```

**Reproduced and verified end-to-end on 2026-07-07** against tunnel
`https://surrender-washday-ransack.ngrok-free.dev` (ephemeral; a new run gets a new hostname):

Without the allow-list, the tunnel is rejected:

```
$ curl -i -X POST https://surrender-washday-ransack.ngrok-free.dev/mcp ...
HTTP/2 421
Invalid Host header
```

With `AGENTS_MCP_ALLOWED_HOSTS` including the tunnel hostname, `tools/list` and `tools/call`
both return `HTTP/2 200` over the public HTTPS URL, matching the local response already
verified at `http://127.0.0.1:8767/mcp`.

### `curl` examples

```bash
curl -s -X POST https://surrender-washday-ransack.ngrok-free.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

curl -s -X POST https://surrender-washday-ransack.ngrok-free.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"hello_agent","arguments":{"name":"Ada"}}}'
```

`tools/list` exposed exactly the `hello_agent` tool. `tools/call` with `{"name": "Ada"}`
returned `greeting == "Hello, Ada!"` and `node_path == ["validate_input", "compose_greeting"]`.

### MCP Inspector equivalents

```bash
npx -y @modelcontextprotocol/inspector --cli "https://<tunnel-host>/mcp" \
  --transport http --method tools/list

npx -y @modelcontextprotocol/inspector --cli "https://<tunnel-host>/mcp" \
  --transport http --method tools/call --tool-name hello_agent --tool-arg name=Ada
```

## Odysseus registration

1. Register the server in Odysseus using the public HTTPS tunnel URL ending in `/mcp`
   (e.g. `https://surrender-washday-ransack.ngrok-free.dev/mcp`), the same pattern verified for
   `hello_world_mcp` in T-0015-02.
2. From a real Odysseus chat, invoke the `hello_agent` tool (e.g. with `{"name": "Ada"}`).
3. Confirm the response contains `node_path`. Its presence — and specifically the value
   `["validate_input", "compose_greeting"]` — is the evidence that a LangGraph graph produced
   the answer, not a string assembled directly in the MCP server: `node_path` is populated by
   each node function appending its own name on exit (`agents/hello_world_agent/domain/nodes.py`),
   so it can only be non-empty if `build_graph().invoke(...)` actually ran both nodes.

**Verified on 2026-07-07** against the ngrok tunnel above: registered in Odysseus, invoked
`hello_agent` from a real chat, and confirmed the response's `node_path` matched
`["validate_input", "compose_greeting"]` (AC-0016-08).

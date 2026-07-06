# hello-world-mcp

Minimal, permanent reference MCP server (spec 0015). One tool (`hello`) that returns a
greeting; no business logic, no auth. Its purpose is to prove the remote-hosting path for
this monorepo: streamable HTTP transport → HTTPS tunnel → registration in an MCP-compatible
AI workspace.

## Start the server

Stdio (default, for hosts that spawn a process):

```bash
uv run --package hello-world-mcp hello-world-mcp
```

HTTP (streamable HTTP, for hosts that connect over the network):

```bash
AGENTS_MCP_TRANSPORT=http AGENTS_MCP_HOST=127.0.0.1 AGENTS_MCP_PORT=8766 \
  uv run --package hello-world-mcp hello-world-mcp
```

The server listens on `http://127.0.0.1:8766/mcp`. See the env var table in spec 0015 for
`PORT` precedence, `AGENTS_MCP_STATELESS` and `AGENTS_MCP_ALLOWED_HOSTS`.

Verified locally (2026-07-06):

```bash
curl -s -X POST http://127.0.0.1:8766/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"hello","arguments":{"name":"Ada"}}}'
# {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\n  \"greeting\": \"Hello, Ada!\"..."}],
#  "structuredContent":{"greeting":"Hello, Ada!","server_version":"0.1.0","timestamp":"2026-07-06T14:40:29.864182Z"},"isError":false}}
```

## HTTPS tunnel (ngrok) — Host-header workaround

The MCP Python SDK enables DNS-rebinding protection whenever the server binds to a loopback
address: it rejects any request whose `Host` header isn't recognized (HTTP 421). An HTTPS
tunnel forwards its own public hostname in `Host`, so the server must be told to allow it via
`AGENTS_MCP_ALLOWED_HOSTS`.

1. Start the server as above (HTTP mode, port 8766).
2. Start the tunnel: `ngrok http 8766` (requires `ngrok config add-authtoken <token>` once,
   done against the operator's ngrok account). Note the printed `https://<subdomain>.ngrok-free.dev`
   URL — it changes on every restart on the free tier.
3. Restart the server with the tunnel hostname allow-listed:

   ```bash
   AGENTS_MCP_TRANSPORT=http AGENTS_MCP_HOST=127.0.0.1 AGENTS_MCP_PORT=8766 \
     AGENTS_MCP_ALLOWED_HOSTS="<subdomain>.ngrok-free.dev,127.0.0.1:8766,localhost:8766" \
     uv run --package hello-world-mcp hello-world-mcp
   ```

   The alternative documented by the SDK — a tunnel that rewrites the `Host` header back to
   `127.0.0.1` before forwarding — was not used here; ngrok forwards the original public
   hostname, so the allow-list is the applicable workaround for ngrok/cloudflared quick tunnels.

**Reproduced and verified end-to-end on 2026-07-06** against tunnel
`https://surrender-washday-ransack.ngrok-free.dev` (ephemeral; a new run gets a new hostname):

Without the allow-list, the tunnel is rejected:

```
$ curl -i -X POST https://surrender-washday-ransack.ngrok-free.dev/mcp ...
HTTP/2 421
Invalid Host header
```

With `AGENTS_MCP_ALLOWED_HOSTS` including the tunnel hostname, `initialize`, `tools/list` and
`tools/call` all return `200 OK` with the expected payloads over the public HTTPS URL.

## Smoke test via MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) CLI mode drives the
server without a browser — useful for scripted smoke tests against a tunnel:

```bash
npx -y @modelcontextprotocol/inspector --cli "https://<tunnel-host>/mcp" \
  --transport http --method tools/list

npx -y @modelcontextprotocol/inspector --cli "https://<tunnel-host>/mcp" \
  --transport http --method tools/call --tool-name hello --tool-arg name=Ada
```

Verified on 2026-07-06 against the ngrok tunnel above: `tools/list` returned the `hello` tool
with its documented input/output schema; `tools/call` returned
`{"greeting": "Hello, Ada!", "server_version": "0.1.0", "timestamp": "2026-07-06T14:42:32.153732Z"}`.

## Gemini Enterprise registration — verified findings

Attempted end-to-end against a real Gemini Enterprise workspace (Google Cloud console →
Gemini Enterprise) on 2026-07-06, using the ngrok tunnel above as the MCP Server URL.

**Prerequisite (per [Google Cloud docs](https://docs.cloud.google.com/gemini/enterprise/docs/connectors/custom-mcp-server/set-up-custom-mcp-server)):**
the account creating the data store needs the `roles/discoveryengine.editor` IAM role
(Discovery Engine Editor) on the GCP project backing the Gemini Enterprise workspace. Check
via Cloud console → IAM & Admin → IAM, on that project.

**Registration path exercised:** Gemini Enterprise console → *Data stores* → *Create data
store* → source *Custom MCP Server* → *Add MCP server*. The *MCP Server URL* field accepted
the ngrok tunnel URL (`https://surrender-washday-ransack.ngrok-free.dev/mcp`) without issue.

**Blocker — verified, not hypothetical:** the *Authentication settings* section marks
*Authorization URL*, *Token URL*, *Client ID* and *Client Secret* as required (`*`) fields.
The form will not proceed past this step, and the *Advanced options* section will not even
expand, until all four OAuth 2.0 fields are filled and a *Verify Auth* login/consent flow is
completed. No "no authentication" or API-key alternative is exposed in this form. This was
reproduced directly in the console (screenshot on file, 2026-07-06): the section is flagged
"Some form fields are incorrect" with each OAuth field showing "Value is required".

**Conclusion:** registering `hello_world_mcp` as a Gemini Enterprise *Custom MCP Server* data
store currently requires the target MCP server to speak OAuth 2.0 (authorization endpoint,
token endpoint, and Bearer-token enforcement on tool calls). `hello_world_mcp` intentionally
ships without authentication — spec 0015 explicitly treats auth as an accepted risk while the
server exposes only a constant greeting, and states auth must be revisited before any real
tool is added. Adding OAuth here would be scope beyond a documentation task; it is tracked as
a follow-up (see `docs/backlog.md`, Phase 2). Registration in Gemini Enterprise is therefore
**blocked on that follow-up**, not on anything specific to the tunnel, transport or Host-header
setup — all of which were independently verified above (tunnel + MCP Inspector).

Until the auth follow-up lands, `hello_world_mcp` can still be registered with MCP-compatible
hosts that don't require OAuth for a custom connector (e.g. Odysseus, Open WebUI, Claude
Code — see spec 0002's host-integration pattern for the sibling `ai_repo_auditor_mcp` server,
which registers via a plain stdio/HTTP config with no auth step).

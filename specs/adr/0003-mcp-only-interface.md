---
id: "ADR-0003"
title: MCP as the only external interface (stdio default, HTTP optional)
status: accepted
---

# ADR 0003 — MCP-Only Interface

## Context

The agent must be consumed from AI workspaces (Odysseus, Open WebUI, Claude Code). A CLI was explicitly excluded from this phase. MCP is the interoperability standard these hosts share.

## Decision

Expose the agent **exclusively as an MCP server** (official Python SDK / FastMCP) with a single tool, `analyze_repository_ai_authorship`. Support **both transports**: **stdio as the default** (hosts spawn the process; simplest and safest) and **streamable HTTP behind a settings flag** (`AGENTS_MCP_TRANSPORT=http`, bound to `127.0.0.1` only) for hosts that cannot spawn processes. The server is a thin adapter — validation, invocation, error mapping — with zero analysis logic.

## Consequences

- One contract to maintain; every MCP host gets the tool for free.
- No CLI surface to design, document or secure this phase; internal testing uses the MCP client SDK instead.
- HTTP mode adds a small network surface — mitigated by loopback-only binding and no-auth-needed local scope; authn becomes a requirement only if binding ever widens (would be a new ADR).

## Alternatives considered

- **stdio only:** almost sufficient, but some workspace deployments (containerized hosts) can only reach servers over HTTP; the flag costs little since FastMCP supports both.
- **CLI first, MCP later:** rejected by explicit project constraint.
- **REST API:** rejected — hosts would need bespoke integration; MCP already solves discovery and schema exchange.

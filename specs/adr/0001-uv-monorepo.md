---
id: "ADR-0001"
title: UV workspace monorepo
status: accepted
---

# ADR 0001 — UV Workspace Monorepo

## Context

The project will grow into multiple agents sharing contracts, an Ollama client, security policy and tooling. Development is agent-driven and needs reproducible environments, a single dependency resolution and fast iteration from day one.

## Decision

Use a single repository managed as a **UV workspace**: root `pyproject.toml` with `[tool.uv.workspace]`, one `uv.lock`, members under `packages/` (shared libs), `agents/` (LangGraph agents) and `mcp_servers/` (deployables). All members use `src/` layout, internal deps via `{ workspace = true }`, versions moving together at `0.x`.

Start with only two shared packages — `agents-core` and `agents-ollama-client`. Chunking, git collection and report rendering stay inside `ai-repo-auditor` behind protocols; they are extracted into `packages/` only when a second agent needs them.

## Consequences

- One `uv sync` gives a coherent environment; quality gates are plain `uv run` commands.
- Cross-member refactors are atomic (no internal publishing).
- Deferred extraction avoids premature package boundaries (YAGNI) while protocols keep extraction cheap.
- Single lockfile means one resolution for all members — a constraint if agents ever need conflicting dep versions (accepted; revisit only if it happens).

## Alternatives considered

- **Multi-repo:** rejected — heavy coordination overhead for a solo/agent-driven project.
- **Poetry/pip-tools monorepo:** rejected — UV's native workspaces are simpler and faster.
- **All packages from the initial draft (`langgraph_runtime`, `report_renderer`) upfront:** rejected as premature; documented as the extraction path instead.

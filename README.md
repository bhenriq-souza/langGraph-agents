# langgraph-agents

A Python monorepo (managed with [UV workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)) for building local AI agents orchestrated with **LangGraph** and exposed to AI workspaces (Odysseus, Open WebUI, Claude Code, …) exclusively through **MCP servers**. All inference runs locally via **Ollama**.

> **Status:** planning phase. This repository currently contains only specs, ADRs and the roadmap. No code has been written yet — implementation is driven by the specs (see [Spec Driven Development](#spec-driven-development) below).

## First agent: `ai-repo-auditor`

Analyzes a local Git repository and produces a **probabilistic estimate** of how much of its code may have been developed with AI assistance.

Important framing, repeated everywhere in this project: the output is an **estimate based on signals** (code patterns, Git history, structural homogeneity, local-LLM judgment). It is **not** a forensic detector and does not prove authorship. Limitations are always part of the report.

```
Odysseus / AI workspace
  ↓ MCP (stdio default; streamable HTTP optional)
MCP server (FastMCP, thin adapter)
  ↓
LangGraph agent (deterministic pipeline)
  ↓ HTTP (localhost)
Ollama → local model on RTX 5070
  ↓
Local Git repository (strictly read-only)
```

## Repository layout (target)

```
pyproject.toml            # UV workspace root
packages/
  core/                   # agents_core — shared contracts, settings, logging, security, errors
  ollama_client/          # agents_ollama_client — typed async Ollama HTTP client
agents/
  ai_repo_auditor/        # LangGraph agent (domain / application / infrastructure / graph)
mcp_servers/
  ai_repo_auditor_mcp/    # FastMCP server exposing analyze_repository_ai_authorship
tests/                    # cross-package integration and e2e tests
scripts/                  # dev utilities (fixture repo builder, quality pipeline)
reports/                  # default output dir for generated reports (gitignored)
specs/                    # functional & technical specs + ADRs
docs/                     # roadmap, backlog, usage docs
```

## Spec Driven Development

Development is performed mostly by AI dev agents, so every unit of work must be unambiguous, small and verifiable:

1. **Specs first.** Behavior lives in `specs/NNNN-*.md`. Each spec defines contracts, invariants, error cases, acceptance criteria and the tests that prove it.
2. **ADRs record decisions.** `specs/adr/` explains *why* the architecture is the way it is.
3. **Tasks trace to specs.** `docs/backlog.md` lists tasks with IDs like `T-0007-03` (task 03 of spec 0007). A task is *done* only when its spec's acceptance criteria and mapped tests pass.
4. **Conventions** for writing and evolving specs are in [`specs/0000-spec-process.md`](specs/0000-spec-process.md).
5. **Git workflow** ([`specs/0014-development-workflow.md`](specs/0014-development-workflow.md)): branch per task from a freshly pulled `develop`, Conventional Commits, standardized PR squash-merged only after owner approval. AI dev agents must read [`AGENTS.md`](AGENTS.md) before working here.

Start reading at [`specs/0001-ai-repo-auditor-overview.md`](specs/0001-ai-repo-auditor-overview.md), then [`docs/roadmap.md`](docs/roadmap.md).

## Spec index

| ID | Spec |
|----|------|
| 0000 | [Spec process & conventions](specs/0000-spec-process.md) |
| 0001 | [ai-repo-auditor overview](specs/0001-ai-repo-auditor-overview.md) |
| 0002 | [MCP contract](specs/0002-mcp-contract.md) |
| 0003 | [LangGraph flow](specs/0003-langgraph-flow.md) |
| 0004 | [Repository scanning](specs/0004-repository-scanning.md) |
| 0005 | [Git metadata analysis](specs/0005-git-metadata-analysis.md) |
| 0006 | [Code chunking](specs/0006-code-chunking.md) |
| 0007 | [LLM scoring](specs/0007-llm-scoring.md) |
| 0008 | [Score aggregation](specs/0008-score-aggregation.md) |
| 0009 | [Report generation](specs/0009-report-generation.md) |
| 0010 | [Security boundaries](specs/0010-security-boundaries.md) |
| 0011 | [Testing strategy](specs/0011-testing-strategy.md) |
| 0012 | [Configuration & dependency injection](specs/0012-configuration-and-di.md) |
| 0013 | [Monorepo & tooling](specs/0013-monorepo-and-tooling.md) |
| 0014 | [Development workflow](specs/0014-development-workflow.md) |
| 0015 | [Hello World MCP server](specs/0015-hello-world-mcp.md) |

ADRs: [`specs/adr/`](specs/adr/)

## Local requirements (when implementation starts)

- Ubuntu 26.04, Python ≥ 3.12, [uv](https://docs.astral.sh/uv/)
- Ollama running locally with `qwen2.5-coder:14b-instruct-q4_K_M` pulled (scorer) and optionally `deepseek-r1:14b` (phase-2 reviewer)
- No external network calls are made during analysis: the system is offline-first by design.

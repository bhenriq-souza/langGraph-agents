---
id: "0013"
title: Monorepo & tooling
status: approved
depends_on: ["0000"]
---

# 0013 — Monorepo & Tooling

## Goal

Define the UV workspace layout, package boundaries, dependency policy and the local quality pipeline (lint, format, types, security, tests) that gates every task's definition of done.

## Scope / Non-goals

- **In scope:** workspace structure, member pyprojects, tool configuration, quality commands, pre-commit.
- **Non-goals:** publishing to registries (internal workspace deps only this phase), remote CI (local-first; a CI workflow is a cheap later addition since gates are plain `uv run` commands).

## Contracts

### Workspace layout (ADR 0001)

```
langgraph-agents/
  pyproject.toml            # workspace root: [tool.uv.workspace] members, dev deps, tool config
  uv.lock                   # single lockfile for the whole workspace
  .python-version           # 3.12
  packages/
    core/                   #   dist name: agents-core        import: agents_core
    ollama_client/          #   dist name: agents-ollama-client import: agents_ollama_client
  agents/
    ai_repo_auditor/        #   dist name: ai-repo-auditor    import: ai_repo_auditor
  mcp_servers/
    ai_repo_auditor_mcp/    #   dist name: ai-repo-auditor-mcp import: ai_repo_auditor_mcp
  tests/integration/  tests/e2e/    # cross-package suites (root-level dev deps)
  scripts/                  # build_fixture_repo.py, check_specs.py, check_language.py
  reports/                  # runtime output, gitignored
  specs/  docs/
```

Every member uses `src/` layout (`src/<import_name>/`) plus its own `tests/`. Root `pyproject.toml` declares `[tool.uv.workspace] members = ["packages/*", "agents/*", "mcp_servers/*"]`; members depend on each other via `[tool.uv.sources] agents-core = { workspace = true }`. Internal versions stay `0.x` and move together (no independent release trains this phase).

**Deviation from the initial draft (recorded in ADR 0001):** `langgraph_runtime` and `report_renderer` are *not* separate packages yet. Chunking, git collection and report rendering live inside `ai_repo_auditor` behind protocols (spec 0012), with the extraction path documented — they graduate to `packages/` when a second agent needs them. This keeps the MVP surface small without sacrificing the boundary discipline that makes extraction trivial.

### Dependency policy

| Member | Runtime deps |
|--------|--------------|
| `agents-core` | `pydantic`, `pydantic-settings`, `structlog` |
| `agents-ollama-client` | `agents-core`, `httpx` |
| `ai-repo-auditor` | `agents-core`, `agents-ollama-client`, `langgraph`, `pathspec`, `dependency-injector` |
| `ai-repo-auditor-mcp` | `ai-repo-auditor`, `mcp` (official SDK) |

Rules: `packages/*` never depend on `agents/*` or `mcp_servers/*`; agents never depend on MCP servers; git access via subprocess wrapper (no `gitpython` — ADR 0006). Dev deps (root group): `pytest`, `pytest-cov`, `pytest-xdist`, `hypothesis`, `ruff`, `pyright`, `bandit`, `import-linter`, `pre-commit`.

### Entry point

`ai-repo-auditor-mcp` declares `[project.scripts] ai-repo-auditor-mcp = "ai_repo_auditor_mcp.server:main"` — the command hosts use for stdio registration (spec 0002).

### Quality pipeline (the local gate; each is a `uv run` command)

| Step | Command | Config highlights |
|------|---------|-------------------|
| Format | `uv run ruff format --check .` | line length 100 |
| Lint | `uv run ruff check .` | rule sets: `E,F,W,I,N,UP,B,S,SIM,PTH,RUF`; `S` (bandit-flavored) on src |
| Types | `uv run pyright` | `strict` on `packages/` and agent `domain/`+`application/`; `standard` elsewhere |
| Security | `uv run bandit -r packages agents mcp_servers -ll` | fails on `shell=True`, `eval`, etc. (INV-0010-04) |
| Imports | `uv run lint-imports` | layered contracts: domain ⇥ application ⇥ infrastructure; INV-0012-02 |
| Tests | `uv run pytest -m "not live_ollama" --cov --cov-fail-under=80` | per-package 90% targets via cov config (spec 0011) |
| Specs | `uv run python scripts/check_specs.py && uv run python scripts/check_language.py` | INV-0000-01..03; language policy grep |

Aggregate: `uv run poe check` (or a `scripts/check.sh` wrapper — decided at implementation, both acceptable) runs all steps; **all green = definition of done** (spec 0000).

### pre-commit

Hooks: ruff format, ruff check `--fix`, pyright (changed files), bandit (changed files), end-of-file/trailing-whitespace. Full pytest is not a pre-commit hook (too slow); it gates task completion instead.

## Invariants

- **INV-0013-01:** one `uv.lock` at the root; no member has its own lockfile.
- **INV-0013-02:** dependency-direction rules above hold (import-linter enforced).
- **INV-0013-03:** every member ships `py.typed`.
- **INV-0013-04:** the quality pipeline runs offline.

## Error cases

Not applicable (structure spec); pipeline failures are the error surface.

## Acceptance criteria

- **AC-0013-01:** `uv sync` from a clean clone succeeds and `uv run pytest` passes on the skeleton.
- **AC-0013-02:** each pipeline step fails on a deliberately planted violation (one canary test per gate during phase 0, then removed).
- **AC-0013-03:** `uv run ai-repo-auditor-mcp` starts the stdio server from the workspace root.

## Test mapping

| Item | Test |
|------|------|
| AC-0013-01..03 | phase-0 verification checklist (`docs/roadmap.md`), then exercised implicitly by every task's DoD |
| INV-0013-02 | `lint-imports` gate |

## Open questions

None.

# Roadmap

Phases are strictly ordered; a phase starts only when the previous phase's definition of done (DoD) is fully green. Tasks per phase live in [`backlog.md`](backlog.md); specs are in [`../specs/`](../specs/).

## Phase 0 — Foundation

Scaffolding and gates, no analysis logic.

- Initialize git repo + UV workspace (root `pyproject.toml`, `.python-version`, member skeletons with `src/` layout and empty test suites) — spec 0013.
- Configure quality pipeline: ruff, pyright, bandit, import-linter, pytest+cov, pre-commit; `scripts/check_specs.py` and `scripts/check_language.py`.
- `agents_core` skeleton: `AgentsSettings`, structlog setup, error types, `SecurityPolicy` (spec 0010, 0012).
- `agents_ollama_client` skeleton: typed httpx client with health check, chat call, `format=json` support (spec 0007's call contract).
- `scripts/build_fixture_repo.py` + shared conftest fixtures + fake Ollama transport (spec 0011).

**DoD:** `uv sync` from clean clone works; `uv run pytest`, `ruff`, `pyright`, `bandit`, `lint-imports` all green (AC-0013-01); SecurityPolicy tests pass (AC-0010-01, 02, 05); fixture repo deterministic (AC-0011-02).

## Phase 1 — MVP pipeline

Implementation order follows the dependency chain; each step is a backlog task block:

1. Contracts: `AnalysisRequest`/`AnalysisResponse` + internal models (specs 0002, 0003 state).
2. File scanner + filter rules + priority ordering (spec 0004).
3. `GitCollector` + signals + `git_prior` (spec 0005).
4. Chunker (spec 0006).
5. LLM scorer: prompt v1, JSON validation, retries, degradation (spec 0007).
6. Aggregation (spec 0008).
7. Report renderer + storage (spec 0009).
8. `AuditorContainer` + `build_graph` factory + all LangGraph nodes + budget enforcement (specs 0003, 0012).
9. MCP server: FastMCP tool, error mapping, stdio entrypoint, HTTP flag (spec 0002).
10. Integration + e2e suites; live smoke test against real Ollama on a real repo.

**DoD:** all MVP acceptance criteria of spec 0001 (AC-0001-01..06) pass; full quality pipeline green; a real analysis of one of the user's own repos completes end-to-end via an MCP client with plausible output.

## Phase 2 — Hardening

- PostgreSQL chunk cache replacing `NoopChunkCache` (ADR 0007) — DSN-configured, homelab server as primary target, any Postgres provider supported.
- `review_report_with_second_model` node using `deepseek-r1:14b` (spec 0003 extension).
- Streamable HTTP transport validated with a real host; Odysseus integration exercised and documented (spec 0002 host section).
- Budget/prompt calibration pass over several real repos of known provenance; adjust defaults with evidence.
- Timestamped report history option.

**DoD:** re-run of an unchanged repo hits ≥ 95% cache; review node produces a critique section in the report; the tool is registered and usable from the user's workspace (Odysseus or equivalent).

## Phase 3 — Extensions

- `build_author_baseline` + `compare_style_with_baseline` nodes (style-shift signal).
- Run-history persistence (`persist_results`) and cross-run comparison.
- Extraction of `chunking`/`git`/`report` modules into `packages/` when a second agent lands (ADR 0001 exit criterion).
- Optional: tree-sitter chunking upgrade (spec 0006 future note); `human_review_checkpoint` for HITL hosts.

**DoD:** defined per-item when phase 3 is scoped; each item gets a spec revision first (spec 0000 process).

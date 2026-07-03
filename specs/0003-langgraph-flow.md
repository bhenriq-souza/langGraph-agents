---
id: "0003"
title: LangGraph flow
status: approved
depends_on: ["0001", "0002"]
---

# 0003 — LangGraph Flow

## Goal

Define the LangGraph `StateGraph` that orchestrates the analysis: state model, nodes with inputs/outputs, error routing, retry policy, budget enforcement, and behavior on large repositories. LangGraph is the orchestrator of a **mostly deterministic** pipeline — not a wrapper around a single LLM call and not an autonomous agent loop.

## Scope / Non-goals

- **In scope:** graph topology, `AuditState`, node contracts, error/retry/budget policy, extension points.
- **Non-goals:** per-node algorithms (specs 0004–0009), DI wiring details (spec 0012).

## Contracts

### Graph topology (MVP)

```
START → validate_input → resolve_repository_context → discover_files → filter_files
      → collect_git_metadata → chunk_code → score_chunks_with_llm → aggregate_scores
      → generate_report → build_mcp_response → END
```

Every node has a conditional edge: on recorded fatal error → `build_error_response → END`. The graph is a **DAG — no cycles exist**, which structurally rules out infinite loops. All iteration (per-file, per-chunk, retries) happens *inside* nodes with bounded loops.

### State — `AuditState` (Pydantic model)

| Field | Type | Written by |
|-------|------|-----------|
| `request` | `AnalysisRequest` (spec 0002) | initial |
| `settings_snapshot` | `AnalysisSettings` (spec 0012) | `validate_input` |
| `repo` | `RepoContext {root: Path, name: str, head_commit: str, head_date: datetime}` | `resolve_repository_context` |
| `inventory` | `FileInventory` (spec 0004) | `discover_files` |
| `files` | `list[ClassifiedFile]` (spec 0004) | `filter_files` |
| `git_signals` | `dict[str, GitFileSignals]` keyed by relpath (spec 0005) | `collect_git_metadata` |
| `chunks` | `list[CodeChunk]` (spec 0006) | `chunk_code` |
| `chunk_scores` | `list[ChunkScore]` (spec 0007) | `score_chunks_with_llm` |
| `aggregate` | `AggregateResult` (spec 0008) | `aggregate_scores` |
| `report_paths` | `ReportPaths {markdown: Path, json: Path}` | `generate_report` |
| `response` | `AnalysisResponse` (spec 0002) | `build_mcp_response` / `build_error_response` |
| `budget` | `BudgetTracker {deadline_at, files_seen, chunks_scored, lines_scored, truncated: bool, truncation_reasons: list[str]}` | all nodes (read/update) |
| `errors` | `list[NodeError {node, code, message, recoverable: bool}]` | any node |

### Node contracts

| Node | Reads | Writes | Fatal errors it can raise |
|------|-------|--------|---------------------------|
| `validate_input` | `request` | `settings_snapshot`, `budget.deadline_at` | `INVALID_INPUT`, `INVALID_PATH`, `PATH_NOT_ALLOWED` |
| `resolve_repository_context` | `request` | `repo` | `NOT_A_GIT_REPOSITORY`, `OLLAMA_UNAVAILABLE` (health check + `MODEL_NOT_AVAILABLE`) |
| `discover_files` | `repo` | `inventory` | `REPOSITORY_TOO_LARGE` (hard pre-scan limits, spec 0004) |
| `filter_files` | `inventory` | `files` | — (empty analyzable set → fatal `INVALID_INPUT`-style message: nothing to analyze) |
| `collect_git_metadata` | `repo`, `files` | `git_signals` | — (per-file git failures are recoverable: signal marked `unavailable`) |
| `chunk_code` | `files` | `chunks` | — (unreadable file → skipped with reason) |
| `score_chunks_with_llm` | `chunks`, `budget` | `chunk_scores`, `budget` | `OLLAMA_UNAVAILABLE` (only if *zero* chunks scored); otherwise degrade |
| `aggregate_scores` | `chunk_scores`, `git_signals`, `files` | `aggregate` | — (pure function; programming errors → `INTERNAL_ERROR`) |
| `generate_report` | `aggregate`, `repo`, `request` | `report_paths` | `REPORT_WRITE_FAILED` |
| `build_mcp_response` | `aggregate`, `report_paths`, `budget` | `response` | — |
| `build_error_response` | `errors` | `response` (error form) | — |

## Retry policy

Retries never happen via graph edges — only inside nodes, with fixed bounds:

- **LLM scoring call:** up to **2 retries** per chunk on invalid/unparseable JSON, appending a strict format reminder; after that the chunk becomes `ChunkScore(status="unscored")`. Connection errors: 1 retry with backoff; repeated failure while some chunks are already scored → stop scoring, mark `truncated` with reason `ollama_degraded`.
- **Git subprocess:** 1 retry on transient failure; then per-file signals marked `unavailable` (recoverable).
- Nothing else retries.

## Budget & cost control

Configured in spec 0012, snapshotted into `budget` at `validate_input`:

| Budget | Default | Enforcement point |
|--------|---------|-------------------|
| `max_files_analyzed` | 2000 | `filter_files` (priority order below) |
| `max_total_lines_scored` | 200 000 | between scoring batches |
| `max_chunks_scored` | 1500 | between scoring batches |
| `analysis_deadline_seconds` | 600 | checked between scoring batches and before report generation |
| hard pre-scan limits (`max_repo_files=50 000`, `max_repo_bytes=2 GiB`) | spec 0004 | `discover_files` → fatal `REPOSITORY_TOO_LARGE` |

**Large-repo behavior:** exceeding a *soft* budget never fails the run. `filter_files` orders files by priority (source-code extensions first, then by size descending within reason, recency of last commit as tiebreaker) so the most informative files are scored before any cutoff. On breach: scoring stops at the batch boundary, `budget.truncated=true`, the reason is recorded, and aggregation/confidence account for reduced coverage (spec 0008). The response and report state clearly that the analysis was partial.

**Deadline breach before any scoring completed** → fatal `ANALYSIS_TIMEOUT` (spec 0002).

## Progress persistence

MVP: none — a run is atomic in memory; report files are written atomically (temp file + rename, spec 0009). Phase 2 adds the **PostgreSQL chunk-score cache** (ADR 0007, any Postgres provider via DSN): keyed by `(content_hash, model, prompt_version)`, consulted in `score_chunks_with_llm`, making re-runs after truncation/interruption incremental. LangGraph checkpointers are deliberately not used in the MVP (single-shot runs; cache gives cheaper resumability).

## Extension nodes (documented, not built in MVP)

| Node | Insertion point | Purpose |
|------|-----------------|---------|
| `build_author_baseline` | after `collect_git_metadata` | style profile from pre-AI-era commits |
| `compare_style_with_baseline` | after `score_chunks_with_llm` | style-shift signal into aggregation |
| `review_report_with_second_model` | after `generate_report` | `deepseek-r1:14b` critique pass over the report |
| `cache_chunk_scores` / `persist_results` | around scoring / after report | PostgreSQL cache & run history |
| `human_review_checkpoint` | before `build_mcp_response` | LangGraph interrupt for HITL hosts |

Adding any of them must not change existing node contracts (extension via new state fields only).

## Invariants

- **INV-0003-01:** the compiled graph contains no cycles.
- **INV-0003-02:** every node either completes, records a recoverable degradation, or records exactly one fatal `NodeError` and routes to `build_error_response`.
- **INV-0003-03:** `budget.truncated=true` ⇒ `response.truncated=true` and at least one `truncation_reason`.
- **INV-0003-04:** node execution order matches the topology above; no node reads a field written by a later node.
- **INV-0003-05:** total LLM calls ≤ `max_chunks_scored × 3` (retries included) — an absolute cost ceiling.

## Error cases

See node table. Mapping to MCP error codes is 1:1 with spec 0002; `build_error_response` performs the translation.

## Acceptance criteria

- **AC-0003-01:** graph compiles and a fixture-repo run visits all MVP nodes in order (fake Ollama).
- **AC-0003-02:** a fatal error in each node routes to `build_error_response` and yields the documented code (parametrized test).
- **AC-0003-03:** with `max_chunks_scored=5` against a larger fixture, the run succeeds with `truncated=true` and priority files scored first.
- **AC-0003-04:** invalid LLM JSON on every call yields `unscored` chunks after exactly 2 retries each, and the run still completes.
- **AC-0003-05:** deadline set to 0 with no scored chunks → `ANALYSIS_TIMEOUT`.

## Test mapping

| Item | Test |
|------|------|
| AC-0003-01..05 | `agents/ai_repo_auditor/tests/graph/test_flow.py`, `test_budgets.py`, `test_error_routing.py` |
| INV-0003-01 | topology assertion in `test_flow.py` |
| INV-0003-05 | fake-Ollama call counter in `test_budgets.py` |

## Open questions

None.

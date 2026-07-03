---
id: "0002"
title: MCP contract
status: approved
depends_on: ["0001", "0010"]
---

# 0002 — MCP Contract

## Goal

Define the single external interface of this phase: the MCP server `ai_repo_auditor_mcp` and its tool `analyze_repository_ai_authorship` — input schema, output schema, validations, error taxonomy, transports and host (Odysseus) integration.

## Scope / Non-goals

- **In scope:** tool schema, server metadata, transports (stdio default, streamable HTTP optional), error mapping, logging at the boundary.
- **Non-goals:** pipeline internals (spec 0003+), path-policy mechanics (spec 0010), CLI (excluded this phase).

## Contracts

### Server

- Package: `mcp_servers/ai_repo_auditor_mcp`, built with the official MCP Python SDK (`FastMCP`).
- Server name: `ai-repo-auditor`.
- Transports: **stdio (default)**; **streamable HTTP** enabled via settings (`AGENTS_MCP_TRANSPORT=http`, binds `127.0.0.1` only). See ADR 0003.
- The server is a thin adapter: parse/validate input → build DI container-backed graph (spec 0012) → invoke → map result/errors. No business logic in the server package.

### Tool: `analyze_repository_ai_authorship`

**Input — `AnalysisRequest` (Pydantic, `extra="forbid"`):**

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `repo_path` | `str` | required | absolute path; passes spec 0010 policy |
| `model` | `str` | `settings.default_model` | non-empty; must exist in Ollama (checked at run start) |
| `review_model` | `str \| None` | `None` | reserved for phase 2; accepted but unused in MVP |
| `max_lines_per_chunk` | `int` | `180` | `40 ≤ x ≤ 400` |
| `respect_gitignore` | `bool` | `true` | |
| `output_format` | `Literal["markdown_and_json"]` | `"markdown_and_json"` | only value in MVP |

**Output — `AnalysisResponse`:**

| Field | Type | Notes |
|-------|------|-------|
| `estimated_ai_percentage` | `float` | 0–100, one decimal; line-weighted (spec 0008) |
| `confidence` | `Literal["low","medium","high"]` | banding rule in spec 0008 |
| `confidence_score` | `float` | 0–1 |
| `total_lines_analyzed` | `int` | lines actually scored |
| `total_files_analyzed` | `int` | |
| `truncated` | `bool` | `true` if any budget was hit (spec 0003) |
| `report_markdown_path` | `str` | absolute path inside reports dir |
| `report_json_path` | `str` | absolute path inside reports dir |
| `summary` | `str` | 2–4 cautious sentences (language policy, spec 0000) |
| `top_files` | `list[TopFile]` | ≤ 10 items: `{path, ai_probability, confidence}` |
| `limitations` | `list[str]` | standard block from spec 0009, verbatim |
| `analysis_metadata` | `AnalysisMetadata` | `{model, prompt_version, head_commit, started_at, duration_seconds, parameters}` |

**Example response:**

```json
{
  "estimated_ai_percentage": 37.4,
  "confidence": "medium",
  "confidence_score": 0.62,
  "total_lines_analyzed": 18420,
  "total_files_analyzed": 142,
  "truncated": false,
  "report_markdown_path": "/home/bhs/code/Personal/langgraph-agents/reports/meu-repo-ai-authorship-report.md",
  "report_json_path": "/home/bhs/code/Personal/langgraph-agents/reports/meu-repo-ai-authorship-report.json",
  "summary": "The repository shows moderate signals consistent with AI-assisted development, concentrated in service and controller layers. This is a probabilistic estimate, not a determination of authorship.",
  "top_files": [
    {"path": "src/services/report_generator.py", "ai_probability": 0.82, "confidence": 0.74},
    {"path": "src/controllers/user_controller.ts", "ai_probability": 0.61, "confidence": 0.52}
  ],
  "limitations": [
    "This analysis does not prove AI authorship.",
    "Well-structured human code can resemble AI-generated code.",
    "AI-generated code edited by humans can resemble human-written code."
  ],
  "analysis_metadata": {
    "model": "qwen2.5-coder:14b-instruct-q4_K_M",
    "prompt_version": "scoring-prompt/v1",
    "head_commit": "a1b2c3d",
    "started_at": "2026-07-03T14:00:00-03:00",
    "duration_seconds": 412.7,
    "parameters": {"max_lines_per_chunk": 180, "respect_gitignore": true}
  }
}
```

## Validations (at the MCP boundary, before the graph runs)

1. Schema validation via Pydantic (`extra="forbid"` → unknown fields are errors).
2. `repo_path`: absolute, exists, is a directory, passes the spec 0010 path policy.
3. `repo_path/.git` exists (else `NOT_A_GIT_REPOSITORY`).
4. Requested `model` present in Ollama's local model list (else `MODEL_NOT_AVAILABLE`).

## Error cases

Errors are returned as MCP tool errors with a stable machine-readable code plus a friendly, actionable message. Messages never echo filesystem contents beyond the offending path.

| Code | Trigger | Message style |
|------|---------|---------------|
| `INVALID_INPUT` | schema/constraint violation | "Parameter 'max_lines_per_chunk' must be between 40 and 400." |
| `INVALID_PATH` | path missing/not absolute/not a directory | "The path '…' does not exist or is not a directory." |
| `PATH_NOT_ALLOWED` | outside `allowed_base_dirs` (incl. traversal/symlink escape) | "Analysis is restricted to: /home/bhs/code. The given path is outside the allowed directories." |
| `NOT_A_GIT_REPOSITORY` | no `.git` | "The directory is not a Git repository. Point to the repository root." |
| `REPOSITORY_TOO_LARGE` | pre-scan exceeds hard limits (spec 0004) | "The repository exceeds the configured analysis limits (files/size). Adjust limits or analyze a subdirectory." |
| `MODEL_NOT_AVAILABLE` | model not pulled in Ollama | "Model '…' is not available in Ollama. Run: ollama pull …" |
| `OLLAMA_UNAVAILABLE` | connection/refused/timeout on health check | "Could not reach Ollama at …. Is the service running?" |
| `ANALYSIS_TIMEOUT` | wall-clock deadline exceeded *before* any scoring completed | "Analysis exceeded the …s limit before producing results." |
| `REPORT_WRITE_FAILED` | reports dir not writable / outside allowlist | "Could not write reports to '…'." |
| `INTERNAL_ERROR` | anything unexpected | generic message + correlation id; details only in server logs |

Note: budget exhaustion *after* scoring has started is **not** an error — it returns a successful, `truncated: true` response (spec 0003).

## Logging at the boundary

Structured (structlog, spec 0012): one entry per invocation with correlation id, sanitized parameters, duration, outcome code. Chunk content is never logged at INFO level (INV-0010-05).

## Host integration (Odysseus / Open WebUI / any MCP host)

stdio registration example (host config):

```json
{
  "mcpServers": {
    "ai-repo-auditor": {
      "command": "uv",
      "args": ["run", "--project", "/home/bhs/code/Personal/langgraph-agents", "ai-repo-auditor-mcp"],
      "env": { "AGENTS_ALLOWED_BASE_DIRS": "/home/bhs/code" }
    }
  }
}
```

HTTP mode (for hosts that cannot spawn processes): run `AGENTS_MCP_TRANSPORT=http uv run ai-repo-auditor-mcp` and register `http://127.0.0.1:8765/mcp`. The host discovers the tool via MCP `tools/list`; the LLM in the workspace fills the arguments; the structured response lets the workspace render the summary, top files and report links directly to the user.

## Invariants

- **INV-0002-01:** the tool never returns a response that mixes success fields with an error; errors are MCP tool errors exclusively.
- **INV-0002-02:** every successful response includes non-empty `limitations` and `analysis_metadata`.
- **INV-0002-03:** HTTP transport binds only to `127.0.0.1`.
- **INV-0002-04:** the server package contains no analysis logic (imports the agent's public API only).

## Acceptance criteria

- **AC-0002-01:** `tools/list` over stdio exposes exactly one tool with the documented input schema.
- **AC-0002-02:** a valid request against a fixture repo returns a response matching the `AnalysisResponse` schema.
- **AC-0002-03:** each error case in the table above is reproducible in tests and returns its documented code.
- **AC-0002-04:** unknown input fields are rejected (`INVALID_INPUT`).

## Test mapping

| Item | Test |
|------|------|
| AC-0002-01, 02 | `tests/e2e/test_mcp_analysis.py` (stdio client + fake Ollama) |
| AC-0002-03, 04 | `mcp_servers/ai_repo_auditor_mcp/tests/test_errors.py`, `test_validation.py` |
| INV-0002-03 | `mcp_servers/ai_repo_auditor_mcp/tests/test_http_binding.py` |

## Open questions

None.

---
id: "0001"
title: ai-repo-auditor overview
status: approved
depends_on: ["0000"]
---

# 0001 — `ai-repo-auditor` Overview

## Goal

Deliver a local agent that, given the path of a local Git repository, produces a **probabilistic estimate of how much of the repository may have been developed with AI assistance**, with evidence, a confidence level and explicit limitations — exposed exclusively as an MCP tool so AI workspaces (Odysseus, Open WebUI, Claude Code) can invoke it.

## Scope / Non-goals

**In scope (MVP):**
- One MCP tool: `analyze_repository_ai_authorship` (spec 0002).
- Deterministic LangGraph pipeline (spec 0003): validate → scan → filter → git metadata → chunk → LLM scoring → aggregation → report.
- Local inference via Ollama only; offline by design.
- Markdown + JSON reports persisted to an allowlisted directory (spec 0009).
- Read-only operation over the analyzed repository (spec 0010).

**Non-goals:**
- CLI of any kind (explicitly excluded this phase).
- Forensic or legally meaningful AI-authorship detection. The output is an estimate based on signals, never a determination.
- Per-author attribution, plagiarism detection, license analysis.
- Cloud/remote LLM providers (no code leaves the machine by default).
- Local-model tool calling (the LLM only performs structured classification in the MVP).

## Contracts

The end-to-end contract is the MCP tool defined in spec 0002. The internal contract chain:

```
AnalysisRequest (0002) → AuditState (0003) → FileInventory (0004) → GitFileSignals (0005)
  → CodeChunk (0006) → ChunkScore (0007) → AggregateResult (0008) → Report artifacts (0009)
  → AnalysisResponse (0002)
```

### Expected user-visible result (shape, illustrative values)

```
Estimated share of code developed with AI assistance: 37%
Confidence: medium (0.62)
Lines analyzed: 18,420
Files with the highest estimated AI-assistance probability:
- src/services/report_generator.py — probability 0.82, confidence 0.74
- src/api/generated_client.ts — excluded (appears to be generated code)
- src/controllers/user_controller.ts — probability 0.61, confidence 0.52

Note: this analysis does not prove AI authorship. It estimates probability from
code patterns, Git history, comments, structural homogeneity and local-LLM judgment.
```

## Methodology summary

Two complementary signal sources, combined in spec 0008:

1. **Deterministic heuristics** (specs 0004, 0005): Git history shape (large single-commit files, AI-keyword commit messages, lack of incremental evolution), file classification (generated/vendored/minified excluded or down-weighted).
2. **LLM structured judgment** (spec 0007): per-chunk classification by a local coding model, returning probability, confidence and named signals (over-explaining comments, didactic naming, structural homogeneity, generic error handling vs. domain-specific comments, natural imperfections, explicit trade-offs).

## Model choices (target hardware: RTX 5070 12 GB VRAM, 64 GB RAM)

| Role | Model | Rationale |
|------|-------|-----------|
| Scorer (MVP) | `qwen2.5-coder:14b-instruct-q4_K_M` | ~9 GB quantized; strong code understanding; fits VRAM with `num_ctx` 8192; deterministic JSON at temperature 0. |
| Reviewer (phase 2) | `deepseek-r1:14b` | Second-opinion pass over the *final report only* (per-chunk reasoning would be far too slow). |
| Larger models w/ RAM offload | optional, undocumented path | Not planned; throughput loss outweighs quality gain for chunk classification. |

Model IDs are parameters, never hardcoded (spec 0012).

## Risks & methodological limitations (must appear in every report — spec 0009)

1. The analysis does not prove AI authorship; it estimates probability from indirect signals.
2. Well-structured human code can resemble AI-generated code (false positives).
3. AI-generated code edited by humans can resemble human code (false negatives).
4. Squashed/rewritten Git history removes the incremental-evolution signal.
5. The local LLM judge has its own biases; scores vary across models and prompt versions.
6. Results are a plausible range, not a point of truth; the percentage is line-weighted over *analyzed* files only.

Technical risks: LLM JSON instability (mitigated: `format: json`, retries, `unscored` fallback), large-repo cost (mitigated: budgets + truncation, spec 0003), VRAM pressure (mitigated: one model loaded at a time, bounded `num_ctx`).

## Invariants

- **INV-0001-01:** the analyzed repository is never modified (see INV-0010-01).
- **INV-0001-02:** no network calls leave localhost during an analysis.
- **INV-0001-03:** every produced estimate is accompanied by confidence and the standard limitations block.

## Error cases

Delegated to spec 0002 (error taxonomy) and spec 0003 (node-level handling).

## Acceptance criteria (MVP definition of done)

- **AC-0001-01:** invoking the MCP tool on an allowed local Git repo returns a valid `AnalysisResponse` within the configured timeout.
- **AC-0001-02:** both report files (`.md` and `.json`) are written into the allowlisted reports directory.
- **AC-0001-03:** the analyzed repository's mtimes/contents are unchanged after a run (verified by test).
- **AC-0001-04:** paths outside `allowed_base_dirs` are rejected with error code `PATH_NOT_ALLOWED` and a friendly message.
- **AC-0001-05:** with Ollama down, the tool returns `OLLAMA_UNAVAILABLE` (no crash, no partial report files left behind).
- **AC-0001-06:** all user-facing strings comply with the language policy of spec 0000.

## Test mapping

| Item | Test |
|------|------|
| AC-0001-01, 02 | `tests/e2e/test_mcp_analysis.py` (fake Ollama) |
| AC-0001-03 | `tests/integration/test_readonly_guarantee.py` |
| AC-0001-04, 05 | `mcp_servers/ai_repo_auditor_mcp/tests/test_errors.py` |
| AC-0001-06 | grep-based language check in `scripts/check_language.py` + report snapshot tests |

## Open questions

None.

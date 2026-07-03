---
id: "0009"
title: Report generation
status: approved
depends_on: ["0008", "0010"]
---

# 0009 — Report Generation

## Goal

Render the `AggregateResult` into a Markdown report (human-readable) and a JSON report (machine-readable), written atomically to the allowlisted reports directory, with full analysis metadata and the standard limitations block.

## Scope / Non-goals

- **In scope:** both renderers, file naming, atomic persistence, the normative limitations text.
- **Non-goals:** delivery to the host (spec 0002 embeds paths in the response), run-history persistence (phase 3).

## Contracts

### File naming & location

```
{settings.reports_dir}/{repo.name}-ai-authorship-report.md
{settings.reports_dir}/{repo.name}-ai-authorship-report.json
```

`repo.name` = repository root directory basename, sanitized to `[a-z0-9-]` (lowercased, other chars → `-`). Re-analysis overwrites (MVP behavior; timestamped history is phase 3). Writes go through `ReportStorage`, which enforces the spec 0010 path policy and writes atomically (temp file in the same directory + `os.replace`).

### JSON report (superset of the MCP response)

Top-level keys: `schema_version` (`"1"`), `analysis_metadata` (model, prompt_version, head_commit, head_date, started_at, duration_seconds, parameters, agent_version), `result` (the full `AggregateResult`, including every `FileScore`), `exclusions` (list of `{relpath, reason}` for all ignored files), `unscored_summary`, `limitations`, `truncated`, `truncation_reasons`.

### Markdown report structure (template, normative section order)

```markdown
# AI-Authorship Estimate — {repo_name}

> **This is a probabilistic estimate, not a determination of authorship.**
> See “Limitations” below.

## Summary
Estimated share of analyzed code developed with AI assistance: **{pct}%**
Confidence: **{label}** ({score}) · Lines analyzed: {n} of {total} candidate lines
{if truncated: warning block with truncation reasons}

## Files with highest estimated AI-assistance probability
| File | Probability | Confidence | Top signals |
(top 10 by ai_probability, only confidence ≥ 0.3)

## Files with strongest human-authorship signals
(bottom 5 by ai_probability, only confidence ≥ 0.3)

## Excluded files
(grouped counts by reason; expandable list capped at 100 entries)

## Method
(fixed prose: signals used, git prior, model judgment, aggregation summary, prompt version)

## Analysis metadata
(model, prompt version, HEAD commit, date, duration, parameters)

## Limitations
(standard block below, verbatim)
```

### Standard limitations block (normative, used verbatim in both reports and in `AnalysisResponse.limitations`)

```
- This analysis does not prove AI authorship; it estimates probability from indirect signals.
- Well-structured human code can resemble AI-generated code.
- AI-generated code edited by humans can resemble human-written code.
- Squashed or rewritten Git history weakens history-based signals.
- Scores depend on the local model and prompt version used; different versions produce different estimates.
- The percentage refers only to the lines that were actually analyzed.
```

## Invariants

- **INV-0009-01:** reports are written only inside `settings.reports_dir` (policy-checked), never inside the analyzed repository.
- **INV-0009-02:** writes are atomic — a crash never leaves a partial report file.
- **INV-0009-03:** both artifacts of a run are consistent (same numbers, same metadata) — rendered from the same `AggregateResult` instance.
- **INV-0009-04:** the limitations block appears verbatim in both formats; language policy (spec 0000) holds throughout.
- **INV-0009-05:** on a fatal pipeline error, no report files are produced (see AC-0001-05).

## Error cases

| Case | Behavior |
|------|----------|
| `reports_dir` missing | created (`mkdir -p`) if inside allowlist; else `REPORT_WRITE_FAILED` |
| Not writable / disk full | `REPORT_WRITE_FAILED`, temp file cleaned up |
| Filename collision with a directory | `REPORT_WRITE_FAILED` with explicit message |

## Acceptance criteria

- **AC-0009-01:** Markdown and JSON snapshot tests over a fixed `AggregateResult` match golden files byte-for-byte (dates injected via fake clock).
- **AC-0009-02:** JSON report validates against its Pydantic schema on load (round-trip test).
- **AC-0009-03:** simulated crash between temp-write and rename leaves no visible report file.
- **AC-0009-04:** a `reports_dir` outside the allowlist is rejected with `REPORT_WRITE_FAILED`.

## Test mapping

| Item | Test |
|------|------|
| AC-0009-01, 02 | `agents/ai_repo_auditor/tests/infrastructure/test_report_renderer.py` (+ `tests/golden/`) |
| AC-0009-03, 04, INV-0009-01..02 | `test_report_storage.py` |

## Open questions

None.

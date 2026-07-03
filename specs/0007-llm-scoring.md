---
id: "0007"
title: LLM scoring
status: approved
depends_on: ["0003", "0006"]
---

# 0007 — LLM Scoring

## Goal

Score each chunk with a local Ollama model using a **structured classification prompt** (JSON output, temperature 0), producing per-chunk probability, confidence and named signals. The LLM classifies; it does not decide flow, call tools, or free-associate.

## Scope / Non-goals

- **In scope:** scorer component, Ollama call parameters, prompt (versioned), output contract, retry/degradation behavior, batching.
- **Non-goals:** aggregation math (spec 0008), second-model review (phase 2), tool calling (excluded by design).

## Contracts

### `ChunkScore`

```python
class ChunkScore(BaseModel):
    chunk_id: str
    status: Literal["scored", "unscored"]
    ai_probability: float | None      # [0,1]; None when unscored
    confidence: float | None          # [0,1]; the model's own certainty in its judgment
    signals: list[SignalId]           # empty when unscored
    brief_rationale: str | None       # ≤ 280 chars, truncated if longer
    unscored_reason: str | None       # "invalid_json_after_retries" | "ollama_degraded" | "budget"
```

### `SignalId` enum (closed set — model output outside this set is dropped, not an error)

AI-leaning: `over_explaining_comments`, `didactic_naming`, `structural_homogeneity`, `generic_error_handling`, `boilerplate_repetition`, `exhaustive_symmetry` (every case handled with identical structure), `tutorial_style`.
Human-leaning: `domain_specific_comments`, `contextual_tradeoffs`, `natural_imperfections`, `inconsistent_style`, `legacy_scars` (workarounds, dated idioms, TODO trails).
Neutral: `insufficient_signal`.

### Ollama call (via `agents_ollama_client`)

- Endpoint: `POST /api/chat`, `stream=false`, `format="json"`.
- Options: `temperature=0`, `num_ctx=8192`, `num_predict=350`, `seed=7` (best-effort determinism).
- Timeout per call: `settings.llm_call_timeout_seconds` (default 120 s).
- Sequential execution (one in-flight call) in the MVP — a 12 GB-VRAM 14B model gains nothing from client-side concurrency; batching is a settings-gated future option.
- Health check + model presence check happen once, in `resolve_repository_context` (spec 0003).

### Prompt — version `scoring-prompt/v1` (normative text; changes bump the version)

**System message:**

```
You are a code-authorship analyst. Your task is to estimate the probability that a
code excerpt was written with substantial AI assistance (code generation tools such
as ChatGPT, Copilot, Claude, Cursor).

You must respond with ONLY a JSON object, no prose, matching exactly:
{
  "ai_probability": <float 0.0-1.0>,
  "confidence": <float 0.0-1.0>,
  "signals": [<zero or more signal ids from the list below>],
  "brief_rationale": "<one sentence, max 280 characters>"
}

Signal ids you may use (use only these):
AI-leaning: over_explaining_comments, didactic_naming, structural_homogeneity,
generic_error_handling, boilerplate_repetition, exhaustive_symmetry, tutorial_style
Human-leaning: domain_specific_comments, contextual_tradeoffs, natural_imperfections,
inconsistent_style, legacy_scars
Neutral: insufficient_signal

Guidance:
- over_explaining_comments: comments restating what trivial code obviously does.
- didactic_naming: names optimized for a reader who knows nothing about the project.
- structural_homogeneity: large spans with uniform rhythm, symmetry and formatting.
- generic_error_handling: broad try/except-and-log with no domain-specific recovery.
- domain_specific_comments: comments referencing business rules, tickets, real users.
- contextual_tradeoffs: explicit "we do X instead of Y because <project reason>".
- natural_imperfections: small inconsistencies, leftover debugging, uneven style.
- If the excerpt is too short or too generic to judge, use insufficient_signal,
  ai_probability near 0.5 and confidence at or below 0.3.

Calibration:
- 0.0-0.2 strong human-leaning signals; 0.4-0.6 genuinely ambiguous;
  0.8-1.0 strong AI-leaning signals.
- confidence reflects how much evidence the excerpt itself provides, not your
  general belief. Short or trivial excerpts must get low confidence.
- This is a probabilistic judgment about style patterns. It is not proof of
  authorship, and you must never treat it as such.
```

**User message template:**

```
File: {relpath} (lines {start_line}-{end_line}, language: {language})

<code>
{content}
</code>

Respond with the JSON object only.
```

### Response handling

1. Parse response body as JSON; validate with a Pydantic model mirroring the schema (ranges enforced, unknown signal ids dropped, rationale truncated at 280 chars).
2. Invalid JSON / failed validation → retry (≤ 2) appending: `"Your previous reply was not valid JSON matching the schema. Reply with ONLY the JSON object."`
3. Still invalid → `ChunkScore(status="unscored", unscored_reason="invalid_json_after_retries")`.
4. Connection failure: 1 retry with backoff; persistent failure → stop scoring; already-scored chunks kept; remaining marked `unscored_reason="ollama_degraded"`; run continues truncated (spec 0003). If **zero** chunks were scored → fatal `OLLAMA_UNAVAILABLE`.
5. Budget breach between batches → remaining chunks `unscored_reason="budget"`.

## Invariants

- **INV-0007-01:** the prompt sent to the model is exactly the versioned text with template substitution — no dynamic prompt assembly.
- **INV-0007-02:** every emitted `ChunkScore` with `status="scored"` has `ai_probability` and `confidence` in `[0,1]` and only known signal ids.
- **INV-0007-03:** `prompt_version` is recorded in `analysis_metadata` and in the cache key (ADR 0007).
- **INV-0007-04:** chunk content is sent only to the configured localhost Ollama endpoint.

## Error cases

Covered in “Response handling”; all are recoverable except the zero-scored `OLLAMA_UNAVAILABLE` case.

## Acceptance criteria

- **AC-0007-01:** valid model JSON produces a `scored` ChunkScore with all fields mapped.
- **AC-0007-02:** malformed JSON three times → `unscored` with `invalid_json_after_retries`, exactly 3 calls made.
- **AC-0007-03:** unknown signal ids are dropped; out-of-range probability fails validation and triggers retry.
- **AC-0007-04:** connection drop after N scored chunks keeps them and marks the rest `ollama_degraded`.
- **AC-0007-05:** rendered prompts match golden files for `scoring-prompt/v1` (snapshot test).

## Test mapping

| Item | Test |
|------|------|
| AC-0007-01..04 | `agents/ai_repo_auditor/tests/infrastructure/test_llm_scorer.py` (fake Ollama transport) |
| AC-0007-05, INV-0007-01 | `test_llm_scorer.py::test_prompt_snapshot` (golden files under `tests/golden/`) |

## Open questions

None.

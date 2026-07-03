---
id: "0008"
title: Score aggregation
status: approved
depends_on: ["0005", "0007"]
---

# 0008 — Score Aggregation

## Goal

Combine chunk scores and Git priors into per-file scores and a single repository-level estimate with a calibrated confidence level — as **pure, deterministic domain functions** fully testable against fixtures.

## Scope / Non-goals

- **In scope:** file-level aggregation, repo-level estimate, confidence computation, handling of unscored chunks and truncation.
- **Non-goals:** rendering (spec 0009), any further LLM involvement.

## Contracts

### `FileScore`

```python
class FileScore(BaseModel):
    relpath: str
    ai_probability: float        # [0,1] after prior adjustment and clamping
    confidence: float            # [0,1] mean chunk confidence, coverage-discounted
    lines_scored: int
    lines_total: int
    weight: float                # 1.0 analyze | 0.5 reduced_weight
    git_prior: float             # [-0.15, +0.15] (spec 0005)
    top_signals: list[SignalId]  # up to 3 most frequent signals across chunks
```

### `AggregateResult`

```python
class AggregateResult(BaseModel):
    estimated_ai_percentage: float          # [0,100], 1 decimal
    confidence_label: Literal["low", "medium", "high"]
    confidence_score: float                 # [0,1]
    total_lines_analyzed: int               # sum of lines_scored
    total_files_analyzed: int               # files with ≥1 scored chunk
    coverage_ratio: float                   # lines_scored / candidate lines
    file_scores: list[FileScore]            # sorted by ai_probability desc
    unscored_summary: dict[str, int]        # unscored_reason -> count
```

### Formulas (normative)

**File score.** For file *f* with scored chunks *c₁..cₙ* (line counts *wᵢ*, probabilities *pᵢ*, confidences *kᵢ*):

```
p_llm(f)   = Σ(wᵢ · pᵢ) / Σ(wᵢ)                       # line-weighted mean
p_file(f)  = clamp01( p_llm(f) + git_prior(f) )       # bounded prior (spec 0005)
k_file(f)  = ( Σ(wᵢ · kᵢ) / Σ(wᵢ) ) · coverage(f)     # coverage(f) = lines_scored / lines_total
```

Files with zero scored chunks get no `FileScore` and count only toward coverage shortfall.

**Repository estimate.** Over files with a `FileScore`, using `W(f) = lines_scored(f) · weight(f)`:

```
estimated_ai_percentage = 100 · Σ( W(f) · p_file(f) ) / Σ( W(f) )
```

**Confidence score.**

```
coverage_ratio = Σ lines_scored / Σ lines_total(candidate files)
mean_k         = Σ( W(f) · k_file(f) ) / Σ( W(f) )
dispersion     = stdev( p_file over files, weighted by W )    # high spread = mixed repo, mildly reduces certainty
confidence_score = clamp01( 0.5·coverage_ratio + 0.4·mean_k + 0.1·(1 − min(dispersion/0.5, 1)) )
if truncated: confidence_score = min(confidence_score, 0.59)   # truncated runs never claim high confidence
```

**Bands:** `low < 0.40 ≤ medium < 0.70 ≤ high`.

**Worked example (normative test fixture).** Two files:
- `a.py` (analyze, 100/100 lines scored): chunks (60 lines, p=0.9, k=0.8) and (40, p=0.7, k=0.6) → p_llm=0.82; git_prior=+0.10 → p_file=0.92; k_file=0.72·1.0=0.72.
- `b.md` (reduced_weight, 50/100 lines scored): chunk (50, p=0.2, k=0.5) → p_file=0.2+0=0.2; k_file=0.5·0.5=0.25.

W(a)=100, W(b)=25 → estimate = 100·(100·0.92 + 25·0.2)/125 = **77.6%**; coverage = 150/200 = 0.75; mean_k = (100·0.72+25·0.25)/125 = 0.626; dispersion (weighted stdev of {0.92,0.2}) ≈ 0.288 → term 0.1·(1−0.576)=0.0424; confidence_score = 0.375+0.2504+0.0424 = **0.668 → medium**.

## Invariants

- **INV-0008-01:** all outputs are in their declared ranges for any input (property-based test).
- **INV-0008-02:** aggregation is a pure function — no I/O, no clock, no randomness.
- **INV-0008-03:** `truncated=true` ⇒ `confidence_label != "high"`.
- **INV-0008-04:** files with zero scored lines never contribute to the estimate.
- **INV-0008-05:** the percentage always refers to *analyzed* lines; this is stated wherever the number is displayed (spec 0009).

## Error cases

| Case | Behavior |
|------|----------|
| Zero scored chunks overall | not reachable here — spec 0007 already made it fatal; aggregation asserts non-empty input |
| Single-file repos | dispersion of a single point = 0; formulas hold |

## Acceptance criteria

- **AC-0008-01:** the worked example reproduces 77.6% and 0.668/medium exactly (tolerance 1e-9 before rounding).
- **AC-0008-02:** property test (hypothesis): random valid inputs always satisfy INV-0008-01.
- **AC-0008-03:** setting `truncated=true` caps the label at medium.
- **AC-0008-04:** `reduced_weight` halves a file's contribution (verified by paired fixtures).

## Test mapping

| Item | Test |
|------|------|
| AC-0008-01..04 | `agents/ai_repo_auditor/tests/domain/test_aggregation.py` |
| INV-0008-01 | hypothesis property test in same module |

## Open questions

None.

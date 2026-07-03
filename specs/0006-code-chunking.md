---
id: "0006"
title: Code chunking
status: approved
depends_on: ["0004"]
---

# 0006 — Code Chunking

## Goal

Split each classified file into analyzable chunks that fit the scorer's context window, preferring natural code boundaries, and attach the metadata needed for scoring, aggregation and caching.

## Scope / Non-goals

- **In scope:** line-window chunking with boundary awareness, chunk metadata, hashing.
- **Non-goals:** AST/tree-sitter chunking (documented future upgrade, not MVP), token-exact budgeting (line-count proxy is sufficient for 8k ctx).

## Contracts

### `CodeChunk`

```python
class CodeChunk(BaseModel):
    chunk_id: str            # "<relpath>#<start_line>-<end_line>"
    relpath: str
    start_line: int          # 1-based, inclusive
    end_line: int            # inclusive
    line_count: int
    language: str | None     # from ClassifiedFile
    content: str
    content_hash: str        # sha256 of normalized content (cache key component, ADR 0007)
    classification: Literal["analyze", "reduced_weight"]   # inherited from file
```

### Algorithm (`Chunker.chunk(file: ClassifiedFile, text: str) -> list[CodeChunk]`)

1. Read file as UTF-8 with `errors="replace"`; normalize line endings to `\n`.
2. Target window = `request.max_lines_per_chunk` (default 180, bounds 40–400 per spec 0002).
3. Walk lines accumulating a window; when the window is full, **backtrack to the best split point** within the last 25% of the window: the nearest preceding line that is (a) blank, or (b) a column-0 non-continuation line (top-level `def`/`class`/`function`/`}` etc. approximated as "indentation == 0"). If none exists, split hard at the window limit.
4. No overlap between chunks (overlap adds cost without measurable benefit for classification).
5. Files ≤ window size produce exactly one chunk.
6. Trailing chunk shorter than 10 lines is merged into the previous chunk (avoids low-signal fragments).
7. `content_hash = sha256(content)` after normalization — stable across runs for unchanged code.

### Determinism & limits

- Same input file + same `max_lines_per_chunk` ⇒ byte-identical chunk list (INV-0006-01).
- A single file never yields more than `ceil(line_count / (window × 0.75)) + 1` chunks (backtracking bound).

## Invariants

- **INV-0006-01:** chunking is deterministic.
- **INV-0006-02:** concatenating a file's chunk contents (in order) reproduces the normalized file exactly — no gaps, no overlaps.
- **INV-0006-03:** `1 ≤ line_count ≤ max_lines_per_chunk` for every chunk (post-merge rule 6 allows the last chunk up to window+9 lines; the invariant bound is `max_lines_per_chunk + 9`).
- **INV-0006-04:** chunker never writes to disk.

## Error cases

| Case | Behavior |
|------|----------|
| File unreadable/deleted between scan and chunk | file skipped, recorded `ignored (unreadable_at_chunking)`, recoverable |
| Decode anomalies | `errors="replace"`; if replacement chars > 20% of content, file reclassified `ignored (undecodable)` |
| Empty file | zero chunks (valid) |

## Acceptance criteria

- **AC-0006-01:** a 500-line Python fixture with functions at known lines splits at blank/top-level boundaries, not mid-function, for window 180.
- **AC-0006-02:** chunk concatenation reproduces the normalized source (property test over fixture files).
- **AC-0006-03:** same file chunked twice yields identical `chunk_id` and `content_hash` lists.
- **AC-0006-04:** a file with no split candidates (single 400-line function, window 180) splits hard at the limit.
- **AC-0006-05:** 185-line file with window 180 yields one merged chunk (rule 6).

## Test mapping

| Item | Test |
|------|------|
| AC-0006-01..05, INV-0006-01..03 | `agents/ai_repo_auditor/tests/domain/test_chunker.py` |

## Open questions

None.

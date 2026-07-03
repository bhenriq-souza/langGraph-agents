---
id: "0005"
title: Git metadata analysis
status: approved
depends_on: ["0003", "0004", "0010"]
---

# 0005 — Git Metadata Analysis

## Goal

Collect per-file Git history signals through a **read-only, testable subprocess wrapper** (ADR 0006) and convert them into a bounded deterministic prior that nudges the LLM-based file score (spec 0008).

## Scope / Non-goals

- **In scope:** the `GitCollector` component, per-file signals, the heuristic prior, repository-level context (HEAD, name).
- **Non-goals:** author-baseline style modeling (phase 3 extension), blame-level attribution.

## Contracts

### `GitCollector` (infrastructure component behind a Protocol)

- Executes `git` via `subprocess.run` with `shell=False`, explicit argv, `cwd=repo.root`, timeout per call (default 30 s), env stripped to a minimal safe set.
- **Argv allowlist** (INV-0005-01): `rev-parse`, `log`, `ls-files`, `show`, `diff` (numstat only). Any other subcommand is a programming error (raises immediately).
- Batched collection: one `git log --numstat --format=...` pass parsed into per-file history, instead of one subprocess per file (performance on large repos).

### `GitFileSignals` (per relpath)

```python
class GitFileSignals(BaseModel):
    available: bool                     # False when history could not be read
    commit_count: int
    created_in_commit_lines: int        # lines added by the commit that created the file
    created_at: datetime | None
    last_modified_at: datetime | None
    ai_keyword_commits: int             # commits touching file whose message matches keyword regex
    single_commit_file: bool            # commit_count == 1
    large_initial_commit: bool          # created_in_commit_lines >= 300
    churn_ratio: float | None           # total added+deleted lines / current line count
```

AI-keyword regex (case-insensitive, word-boundary): `generated|copilot|chatgpt|gpt-4|gpt4|claude|cursor|codeium|windsurf|ai[- ]generated|ai[- ]assisted`.

### Heuristic prior — `git_prior(signals) -> float` in `[-0.15, +0.15]` (pure domain function)

| Signal | Contribution |
|--------|--------------|
| `single_commit_file and large_initial_commit` | +0.10 |
| `ai_keyword_commits > 0` | +0.08 |
| `commit_count >= 5 and churn_ratio > 0.5` (incremental evolution) | −0.10 |
| `commit_count >= 10` | −0.05 additional |
| otherwise | 0 |

Sum clamped to `[-0.15, +0.15]`. `available=False` ⇒ prior `0.0`. Rationale: history is suggestive, never decisive — squashed history and rebases are common (limitation #4, spec 0001).

## Invariants

- **INV-0005-01:** only allowlisted git subcommands execute; `shell=True` never appears in the codebase (bandit-enforced, spec 0013).
- **INV-0005-02:** the collector never runs a git command that mutates state (no `checkout`, `clean`, `gc`, config writes).
- **INV-0005-03:** the prior is bounded to `[-0.15, +0.15]` for any input.
- **INV-0005-04:** failure to read history is recoverable — never fails the run (signals marked `available=False`).

## Error cases

| Case | Behavior |
|------|----------|
| git binary missing | all signals `available=False`; warning logged once |
| git command timeout | 1 retry; then `available=False` for the affected files |
| unparseable log output | affected file `available=False`; parse error logged at DEBUG |
| shallow clone / detached HEAD | works with whatever history exists; noted in report metadata |

## Acceptance criteria

- **AC-0005-01:** on a scripted fixture repo (known commit sequence), all `GitFileSignals` fields match expected values exactly.
- **AC-0005-02:** commit message "add generated client via copilot" yields `ai_keyword_commits >= 1`.
- **AC-0005-03:** prior values match the table (parametrized over signal combinations, including clamping).
- **AC-0005-04:** collector raises on non-allowlisted subcommand.
- **AC-0005-05:** with git unavailable (PATH mocked), the pipeline completes and the report notes missing history signals.

## Test mapping

| Item | Test |
|------|------|
| AC-0005-01, 02, 05 | `agents/ai_repo_auditor/tests/infrastructure/test_git_collector.py` (uses `scripts/build_fixture_repo.py`) |
| AC-0005-03 | `agents/ai_repo_auditor/tests/domain/test_git_prior.py` |
| AC-0005-04, INV-0005-01 | `test_git_collector.py::test_allowlist` + bandit gate |

## Open questions

None.

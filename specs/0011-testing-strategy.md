---
id: "0011"
title: Testing strategy
status: approved
depends_on: ["0000", "0013"]
---

# 0011 — Testing Strategy

## Goal

Define the test pyramid, shared fixtures and conventions so every spec's acceptance criteria map to concrete, fast, deterministic tests runnable with `uv run pytest`.

## Scope / Non-goals

- **In scope:** test layers, fixture repo builder, fake Ollama, golden files, coverage targets, conventions.
- **Non-goals:** CI service configuration (local-first project; spec 0013 defines the local gate).

## Contracts

### Test layers

| Layer | Location | Scope | LLM | Git |
|-------|----------|-------|-----|-----|
| Unit | `packages/*/tests`, `agents/ai_repo_auditor/tests/{domain,application,infrastructure,graph}` | one component, DI overrides with fakes | fake | fake or fixture repo |
| Integration | `tests/integration/` | multiple real components (real fs, real git, fake Ollama) | fake | real (fixture repo) |
| E2E | `tests/e2e/` | MCP client ↔ server over stdio, full graph | fake (default) | real |
| Live smoke (optional, not gating) | `tests/e2e/`, marker `live_ollama` | real Ollama + real model | real | real |

### Shared fixtures

- **`scripts/build_fixture_repo.py`** — deterministically builds a temp Git repo with scripted history: an "AI-ish" file (single large commit, keyword message `"add service generated with copilot"`, homogeneous style), a "human-ish" file (8 incremental commits, domain comments, a TODO trail), a minified file, a generated client with `@generated` header, a lockfile, a `node_modules/` entry, a binary, a symlink escaping the repo, and a canary string for log-hygiene tests. Fixed author dates ⇒ stable hashes. Exposed as a pytest fixture (`fixture_repo`) in a shared `conftest.py`.
- **Fake Ollama** — an in-process fake of the `agents_ollama_client` transport with programmable behaviors: `valid(score_map)`, `invalid_json(times)`, `connection_error(after_n)`, plus a call counter (asserts INV-0003-05). Unit/integration tests inject it via container override (spec 0012); the e2e stdio test injects it via an env-selected test transport.
- **Golden files** — `tests/golden/`: rendered prompts (AC-0007-05) and Markdown/JSON reports (AC-0009-01). Regenerated only via explicit `pytest --update-golden` flag.
- **Fake clock** — injected `Clock` protocol (spec 0012) so timestamps in reports and deadline logic are testable.

### Conventions

- `pytest` + `pytest-cov`; `hypothesis` for property tests (INV-0008-01, INV-0006-02).
- Test names state the behavior: `test_symlink_escaping_repo_is_ignored_with_reason`.
- Every test module header comment references the spec IDs it covers.
- Markers: `integration`, `e2e`, `live_ollama` (deselected by default: `-m "not live_ollama"`).
- No test touches the network; no test writes outside `tmp_path`.

### Coverage targets (gating)

- `packages/core`, agent `domain/` + `application/`: **≥ 90%** lines.
- Overall workspace: **≥ 80%**.
- Measured by `uv run pytest --cov` in the quality pipeline (spec 0013).

## Invariants

- **INV-0011-01:** the default test suite is hermetic — passes offline with no Ollama running.
- **INV-0011-02:** the suite is order-independent and parallelizable (`pytest -p xdist` clean).
- **INV-0011-03:** fixture repo construction is deterministic (stable commit hashes).

## Error cases

Not applicable (strategy spec); flaky tests are treated as bugs.

## Acceptance criteria

- **AC-0011-01:** `uv run pytest -m "not live_ollama"` passes with Ollama stopped and network disabled.
- **AC-0011-02:** `build_fixture_repo.py` run twice produces identical HEAD hashes.
- **AC-0011-03:** coverage gates enforced (build fails below thresholds).

## Test mapping

Self-referential: this spec is verified by the pipeline configuration in spec 0013 plus AC-0011-01..03 as pipeline steps.

## Open questions

None.

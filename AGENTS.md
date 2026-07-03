# Agent Operating Manual — langgraph-agents

You are working in a **spec-driven** monorepo. Behavior is defined in `specs/`, work items in `docs/backlog.md`. Do not improvise beyond a spec: if a task is ambiguous, the spec gets fixed first (spec 0000).

## Read before working

1. `specs/0000-spec-process.md` — process, task format, definition of done, language policy.
2. `specs/0014-development-workflow.md` — the Git workflow you MUST follow.
3. The spec(s) referenced by your task in `docs/backlog.md`.

## Golden rules

1. **One task = one branch = one PR.** Task IDs look like `T-0004-01`.
2. **Branch ritual, always:**
   ```bash
   git checkout develop && git pull origin develop
   git checkout -b <type>/<task-id>-<slug>     # e.g. feat/t-0004-01-file-scanner
   ```
3. **Conventional Commits** (`feat|fix|docs|test|refactor|chore|ci`), scope = component, footer `Task: T-xxxx-yy`. The commit-msg hook rejects violations — never bypass with `--no-verify`.
4. **Open a PR at the end of the task** (`gh pr create`, template auto-applies). PR title in Conventional Commit format. **Never merge** — merging is the owner's decision after review. Never push directly to `develop`.
5. **Definition of done** (spec 0000): contracts implemented exactly, mapped tests passing, all quality gates green, backlog checkbox ticked in the same PR, spec `status` flipped when its last task completes.
6. **Language policy:** user-facing strings say *estimate/probability/signals/confidence* — never *proof/certainty/definitive detection*.
7. **Security boundaries (spec 0010) are non-negotiable:** never weaken `SecurityPolicy`, never add write access to analyzed repos, never add network destinations, git only via the allowlisted subprocess wrapper, no `shell=True`.
8. Repo skills automate the process — prefer them: `/implement-task`, `/new-spec`, `/check`, `/finish-task` (see `.claude/skills/`).

## Quality gates (run all before opening a PR)

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run bandit -r packages agents mcp_servers -ll
uv run lint-imports
uv run pytest -m "not live_ollama" --cov --cov-fail-under=80
uv run python scripts/check_specs.py && uv run python scripts/check_language.py
```

## Map

| Path | What |
|------|------|
| `specs/` | Normative specs (contracts, invariants, ACs) + `specs/adr/` decisions |
| `docs/backlog.md` | Ordered tasks — your work queue |
| `docs/roadmap.md` | Phases and phase DoD |
| `packages/core`, `packages/ollama_client` | Shared libs (`agents_core`, `agents_ollama_client`) |
| `agents/ai_repo_auditor` | LangGraph agent — `domain/` is pure (no I/O, no DI imports) |
| `mcp_servers/ai_repo_auditor_mcp` | FastMCP server — thin adapter, no business logic |
| `tests/integration`, `tests/e2e` | Cross-package suites (fake Ollama by default) |

Architecture constraints worth repeating: dependency direction is `mcp_servers → agents → packages` (import-linter enforced); `dependency-injector` appears only in container modules and the server entrypoint; the LangGraph graph is a DAG — retries live inside nodes.

---
name: check
description: Run the full local quality pipeline (format, lint, types, security, import contracts, tests with coverage, spec and language checks). Use before opening any PR, or when asked to verify the workspace is green.
---

# Run the quality pipeline

Run every gate; report a pass/fail table at the end. All gates must pass — a task is not done with any gate red (spec 0000 DoD).

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run bandit -r packages agents mcp_servers -ll
uv run lint-imports
uv run pytest -m "not live_ollama" --cov --cov-fail-under=80
uv run python scripts/check_specs.py
uv run python scripts/check_language.py
```

Rules:
- Run gates sequentially; don't stop at the first failure — collect all failures, then fix.
- `ruff format` (without `--check`) and `ruff check --fix` may be used to auto-fix; re-run the checking form afterwards.
- Never relax a gate's configuration to make it pass; config changes require a spec 0013 update via its own PR.
- The suite must pass offline — if a test needs Ollama, it's marked `live_ollama` and excluded here.

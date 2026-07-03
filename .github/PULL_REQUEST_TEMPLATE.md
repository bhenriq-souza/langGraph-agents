<!-- PR title MUST be a Conventional Commit header, e.g.:
     feat(auditor): implement file scanner (T-0004-01)
     It becomes the squash-commit message on develop. -->

## Task

<!-- Backlog ID + one line, e.g.: T-0004-01 — implement FileScanner (docs/backlog.md) -->

## Specs

<!-- Spec IDs implemented/affected, e.g.: 0004 (implements), 0010 (INV-0010-01 relied on) -->

## What & why

<!-- 2–5 sentences: what changed and why, for a reviewer who hasn't followed the branch. -->

## Definition of done

- [ ] Contracts match the spec exactly (names, types, defaults)
- [ ] Mapped tests implemented and passing (`AC-*` / `INV-*` listed below in evidence)
- [ ] All quality gates green locally (`ruff`, `pyright`, `bandit`, `lint-imports`, `pytest --cov`, spec checks)
- [ ] Backlog checkbox ticked in this PR; spec `status` updated if this was its last task
- [ ] User-facing strings follow the language policy (spec 0000)

## Test evidence

<!-- Paste the pytest summary line(s) and the ACs they prove. -->

## Notes for review

<!-- Trade-offs, deviations proposed (require spec change first), anything needing attention. -->

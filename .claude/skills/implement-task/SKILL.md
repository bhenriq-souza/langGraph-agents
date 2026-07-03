---
name: implement-task
description: Implement a backlog task end-to-end following the spec-driven workflow — reads the task and its spec, creates the branch from a freshly pulled develop, implements with tests, runs all quality gates and opens a standardized PR. Use when asked to implement/work on a task ID like T-0004-01.
---

# Implement a backlog task

Argument: a task ID (`T-xxxx-yy`). If missing, pick the first unchecked task in `docs/backlog.md` and confirm with the user.

## Steps

1. **Read the task** in `docs/backlog.md`: What / Where / Done when. Read the referenced spec in full (contracts, invariants, error cases, ACs, test mapping). Read `AGENTS.md` if not already in context.
2. **Check preconditions:** all earlier tasks the spec's `depends_on` chain implies are done (checked boxes). If the task is ambiguous or conflicts with its spec, STOP and report — the spec must be fixed first (spec 0000), in a separate `docs/` PR.
3. **Branch ritual (never skip):**
   ```bash
   git checkout develop && git pull origin develop
   git checkout -b <type>/<task-id-lowercase>-<slug>
   ```
4. **Implement** exactly the referenced contracts — field names, types, defaults verbatim from the spec. Write the mapped tests (spec's Test mapping section) in the same branch.
5. **Run the gates** — invoke the `/check` skill (all must pass; fix until green).
6. **Update traceability in the same branch:** tick the task checkbox in `docs/backlog.md`; if this was the spec's last task, flip its frontmatter `status` to `implemented`.
7. **Commit** with Conventional Commits (scope = component, footer `Task: T-xxxx-yy`). Split into logical commits if useful — they get squashed anyway.
8. **Open the PR** — invoke the `/finish-task` skill.
9. **STOP after the PR is open.** Never merge; never push to `develop`. Report the PR URL and a summary of evidence.

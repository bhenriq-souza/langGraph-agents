---
name: finish-task
description: Verify a task's definition of done and open the standardized pull request to develop (never merges). Use at the end of a task branch, or when asked to open/prepare a PR.
---

# Finish a task: DoD verification + PR

Precondition: you are on a task branch (`<type>/<task-id>-<slug>`), work committed.

## Steps

1. **Verify the DoD** (spec 0000) — all of:
   - Contracts match the spec exactly; mapped tests exist and pass.
   - `/check` skill fully green (run it now if not just run).
   - Backlog checkbox ticked; spec `status` flipped if last task.
   - User-facing strings follow the language policy.
2. **Rebase if needed:** if `develop` moved since branching, `git fetch origin && git rebase origin/develop`, resolve on the branch, re-run `/check`.
3. **Push** the branch: `git push -u origin HEAD`.
4. **Open the PR** targeting `develop`:
   ```bash
   gh pr create --base develop --title "<type>(<scope>): <summary> (T-xxxx-yy)" --body-file <filled template>
   ```
   - Title = Conventional Commit header (it becomes the squash commit on `develop`).
   - Fill every section of `.github/PULL_REQUEST_TEMPLATE.md` — task, specs, what & why, DoD checkboxes (only tick what you verified), test evidence (paste the real pytest summary), notes for review.
5. **STOP.** Merging requires the repository owner's approval (spec 0014, INV-0014-04). Report the PR URL. If review feedback arrives later, address it on the same branch and re-request review.

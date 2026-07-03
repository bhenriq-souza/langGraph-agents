---
id: "0014"
title: Development workflow (branches, commits, pull requests)
status: approved
depends_on: ["0000", "0013"]
---

# 0014 — Development Workflow

## Goal

Define the Git workflow every contributor — human or AI dev agent — must follow: branch naming and creation ritual, commit message convention, standardized pull requests with mandatory owner approval, and the host-side (GitHub) enforcement that makes the rules non-bypassable.

## Scope / Non-goals

- **In scope:** branching model, branch naming, sync ritual, Conventional Commits, PR template and lifecycle, merge strategy, branch protection, CI on PRs, task lifecycle updates.
- **Non-goals:** release/versioning process (future ADR when something is published), the quality gates themselves (spec 0013), GitHub issue tracking (the backlog file is the tracker this phase).

## Contracts

### Branching model

- **`develop` is the default branch.** All work branches off `develop`; all PRs target `develop`. A `main` release branch may be introduced later via a new ADR — out of scope now.
- One backlog task (`T-xxxx-yy`) = one branch = one PR. No multi-task branches.

### Branch creation ritual (normative — run exactly this, in order)

```bash
git checkout develop
git pull origin develop
git checkout -b <type>/<task-id>-<slug>
```

Creating a branch from anything other than a **freshly pulled** `develop` violates INV-0014-03. If `develop` moves while a branch is open, rebase onto updated `develop` before requesting review.

### Branch naming convention

```
<type>/<task-id>-<slug>
```

- `type`: one of the Conventional Commit types below (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`).
- `task-id`: lowercase backlog ID, e.g. `t-0004-01`. For rare non-backlog work (hotfix, spec correction), use the spec ID (`0004`) or `misc`.
- `slug`: short kebab-case description.

Examples: `feat/t-0004-01-file-scanner`, `docs/t-0000-01-spec-checker`, `fix/t-0007-02-retry-count`.

### Commit message convention — [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

```
<type>(<scope>): <imperative summary, ≤ 72 chars>

<body: what and why, wrapped at 100>

Task: T-0004-01
```

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci` (with `!` for breaking changes to internal contracts).
- **Scope:** the component or member touched — `core`, `ollama-client`, `auditor`, `mcp`, `specs`, `workflow`. Omit only for repo-wide changes.
- **Footer:** every commit on a task branch carries the `Task:` footer with its backlog ID.
- Enforced locally by **commitizen** as a `commit-msg` pre-commit hook (spec 0013).

### Pull requests

- Opened at the end of every task, from the task branch to `develop`, via `gh pr create` using the repository template `.github/PULL_REQUEST_TEMPLATE.md`.
- **PR title = the squash commit message header** (Conventional Commit format, since squash merge uses it): `feat(auditor): implement file scanner (T-0004-01)`.
- Template sections (normative): *Task* (ID + link to backlog line), *Specs* (IDs implemented/affected), *What & why* (2–5 sentences), *DoD checklist* (all spec-0013 gates green locally, mapped ACs passing, backlog + spec status updated), *Test evidence* (pytest summary), *Notes for review*.
- **Merge requires approval by the repository owner.** Agents open PRs and respond to review; they never merge. This is host-enforced (branch protection below), not just convention.
- **Merge strategy: squash merge**, delete branch after merge. `develop` history is one Conventional-Commit-titled commit per task.

### Branch protection on `develop` (configured on GitHub — the enforcement layer)

1. Require a pull request before merging; require **1 approval** (owner, via `.github/CODEOWNERS`).
2. Require status checks to pass: the `ci` workflow (below).
3. Dismiss stale approvals on new pushes.
4. No direct pushes (including administrators), no force pushes, no deletions.

**Bootstrap exception:** commits made before the remote exists and protection is enabled (this planning phase and the first scaffold) land on `develop` directly. From the moment protection is active, everything goes through PRs — including changes to specs and to this workflow.

**Phased activation of rule 2:** the required `ci` status check is enabled only at the end of phase 0 (T-0014-02), once the quality-pipeline tooling and scripts exist. Enabling it earlier would deadlock the first PRs: with `enforce_admins` active, the PR that introduces the tooling could never pass the check it is required to satisfy. Until then, rule 1 (owner approval) is the gate; agents must still run the local pipeline before opening PRs.

### CI on PRs — `.github/workflows/ci.yml`

Runs on every PR to `develop`: checkout → install uv → `uv sync` → the exact spec-0013 gate commands (format, lint, types, security, imports, tests+coverage, spec checks). CI must mirror the local pipeline — no CI-only or local-only gates.

### Task lifecycle (traceability)

In the same PR that completes a task: tick its checkbox in `docs/backlog.md`, and if it is the spec's last task, flip the spec's `status` to `implemented`. A task without its backlog update is not done.

## Invariants

- **INV-0014-01:** after protection is enabled, no commit reaches `develop` except through an approved, green-CI, squash-merged PR.
- **INV-0014-02:** every commit on `develop` traces to a task or spec ID (title/footer).
- **INV-0014-03:** work branches are created only from a freshly pulled `develop`.
- **INV-0014-04:** agents never merge PRs; merge is a human (owner) action.
- **INV-0014-05:** CI executes the same commands as the local quality pipeline (spec 0013).

## Error cases

| Situation | Required behavior |
|-----------|-------------------|
| `develop` moved while branch open | rebase onto updated `develop`; resolve conflicts on the branch, never on `develop` |
| CI red on PR | fix on the branch before requesting/expecting review; never merge red |
| commitizen rejects a message | rewrite the message; never bypass with `--no-verify` |
| Review requests changes | address on the same branch, same PR; re-request review |
| Task discovered to be mis-specified mid-branch | stop; fix the spec first (spec 0000 process) in a separate `docs/` PR, then resume |

## Acceptance criteria

- **AC-0014-01:** branch protection on `develop` is active with the four rules above (verified in repo settings).
- **AC-0014-02:** a canary PR with a non-conventional commit message is rejected by the local hook; with a bad title, flagged in review.
- **AC-0014-03:** a canary PR shows the template, runs CI, is blocked from merging until owner approval, and squash-merges cleanly.
- **AC-0014-04:** `git log develop --oneline` after the first merged tasks shows one Conventional-Commit-titled commit per task.

## Test mapping

| Item | Test |
|------|------|
| AC-0014-01..03 | phase-0 verification checklist (T-0014-01/02 in `docs/backlog.md`) — configuration, exercised with a canary PR |
| AC-0014-04 | manual inspection after first real task merges |
| commitizen hook | `pre-commit run --hook-stage commit-msg` in the pipeline (spec 0013) |

## Open questions

None.

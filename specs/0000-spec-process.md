---
id: "0000"
title: Spec process & conventions
status: approved
depends_on: []
---

# 0000 — Spec Process & Conventions

## Goal

Define how specs, ADRs and tasks are written, linked and validated in this monorepo, so that AI dev agents (and humans) can implement work items independently, verifiably and without ambiguity.

## Scope / Non-goals

- **In scope:** spec template, lifecycle, task format, definition of done, naming and cross-referencing rules.
- **Non-goals:** the content of any particular feature (see specs 0001+); CI configuration (spec 0013).

## Spec template

Every spec is a Markdown file `specs/NNNN-kebab-title.md` with YAML frontmatter:

```yaml
---
id: "NNNN"            # zero-padded, unique, never reused
title: Short title
status: draft | approved | implemented | superseded
depends_on: ["NNNN", ...]   # spec IDs this spec builds on
---
```

Required sections, in order:

1. **Goal** — one paragraph: what this spec makes true.
2. **Scope / Non-goals** — explicit boundaries.
3. **Contracts** — input/output schemas (Pydantic-style field lists or JSON), protocols, file formats. Contracts are normative: implementations must match field names and types exactly.
4. **Invariants** — properties that must hold at all times; each invariant gets an ID `INV-NNNN-nn` so tests can reference it.
5. **Error cases** — enumerated failures with error codes, expected behavior and user-facing message style.
6. **Acceptance criteria** — numbered, objectively checkable statements `AC-NNNN-nn`.
7. **Test mapping** — table mapping acceptance criteria/invariants to planned test modules.
8. **Open questions** — unresolved items; must be empty before status becomes `approved`.

## ADR template

`specs/adr/NNNN-kebab-title.md` with sections **Context**, **Decision**, **Consequences**, **Alternatives considered**. Status field in frontmatter: `accepted | superseded`. ADRs are immutable once accepted; changes create a new ADR that supersedes the old one.

## Task format

Tasks live in `docs/backlog.md`. ID format: `T-<spec-id>-<nn>` (e.g. `T-0007-03` = task 03 of spec 0007). Each task states:

- **What** — a single, small deliverable (target: implementable in one focused session).
- **Where** — target package/module path.
- **Done when** — the acceptance criteria and tests it must satisfy (by `AC-*` / `INV-*` IDs).

A task must not require interpretation beyond its spec. If it does, the spec is fixed first.

## Definition of done (applies to every task)

1. Code implements exactly the referenced contracts (names, types, defaults).
2. Mapped tests exist and pass: `uv run pytest`.
3. Quality gates pass: `uv run ruff check`, `uv run ruff format --check`, `uv run pyright`, `uv run bandit` (per spec 0013).
4. No forbidden language in user-facing strings (see below).
5. Spec `status` updated to `implemented` when all its tasks are done.
6. Work delivered via a pull request from a task branch, following spec 0014 (branch ritual, Conventional Commits, PR template), **approved by the repository owner** and squash-merged into `develop`; the task's backlog checkbox is ticked in the same PR.

## Language policy (normative for all user-facing output)

This project estimates; it never proves. All user-facing text (reports, MCP responses, docs) must use cautious vocabulary — *estimate, probability, signals, indications, confidence, plausible range, limitations* — and must never claim *certainty, definitive detection,* or that code was *conclusively/comprovadamente AI-generated*. Every report includes the standard limitations block defined in spec 0009.

## Cross-referencing rules

- Specs reference each other by ID (`spec 0007`).
- Node names, package names, settings keys and error codes are defined once (specs 0002, 0003, 0012, 0013) and reused verbatim everywhere.
- Renames require updating all referencing specs in the same change.

## Invariants

- **INV-0000-01:** every spec file has complete frontmatter and all eight sections.
- **INV-0000-02:** every backlog task references an existing spec ID and at least one `AC-*` or `INV-*` item.
- **INV-0000-03:** `depends_on` references resolve to existing spec IDs; the dependency graph is acyclic.

## Error cases

Not applicable (process spec).

## Acceptance criteria

- **AC-0000-01:** a structural check (script or manual review) can verify INV-0000-01..03 across the `specs/` tree.

## Test mapping

| Item | Test |
|------|------|
| INV-0000-01..03 | `scripts/check_specs.py` (phase 0, optional) or manual review checklist |

## Open questions

None.

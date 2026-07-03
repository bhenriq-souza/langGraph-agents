---
name: new-spec
description: Scaffold a new spec following the 0000 template (frontmatter + eight required sections), register it in the README index and add its tasks to the backlog. Use when asked to create a spec, formalize a feature, or when a task requires a spec change first.
---

# Create or revise a spec

## Steps

1. Read `specs/0000-spec-process.md` (template, lifecycle, task format) if not in context.
2. **New spec:** next free ID (`ls specs/` — zero-padded, never reuse). **Revision of an approved spec:** edit in place only while nothing depending on the changed part is implemented; otherwise document the change explicitly in the PR. Architectural decisions go to a new ADR instead (`specs/adr/`, immutable once accepted — supersede, don't edit).
3. Write the spec with frontmatter (`id`, `title`, `status: draft`, `depends_on`) and all eight sections in order: Goal · Scope/Non-goals · Contracts · Invariants (`INV-NNNN-nn`) · Error cases · Acceptance criteria (`AC-NNNN-nn`) · Test mapping · Open questions.
4. Reuse existing names verbatim (node names, error codes, settings keys, package paths — defined in specs 0002, 0003, 0012, 0013). Never invent a parallel name for an existing concept.
5. Respect the language policy: cautious vocabulary in anything user-facing.
6. Register it: add a row to the README spec index; add its tasks (`T-<id>-<nn>` with What/Where/Done when) to `docs/backlog.md` in dependency order.
7. Deliver via the standard workflow: `docs/`-type branch, Conventional Commit (`docs(specs): …`), PR via `/finish-task`. `status` moves to `approved` only when Open questions is empty and the owner approves the PR.

---
id: "ADR-0006"
title: Git access via allowlisted subprocess wrapper (no GitPython)
status: accepted
---

# ADR 0006 — Git via Subprocess Wrapper

## Context

The agent needs read-only Git metadata (log, ls-files, rev-parse) under strict security constraints: no arbitrary command execution, no repository mutation, bounded runtime, easy faking in tests.

## Decision

Implement `GitCollector` as an infrastructure component that invokes the system `git` binary via `subprocess.run` with `shell=False`, an **explicit argv allowlist** (`rev-parse`, `log`, `ls-files`, `show`, `diff --numstat`), per-call timeout, and a minimal environment (`GIT_TERMINAL_PROMPT=0`, `LC_ALL=C`). It sits behind `GitCollectorProtocol` so tests substitute a fake or run against a scripted fixture repo. History is read in one batched `git log --numstat` pass, not per-file subprocesses.

## Consequences

- The full security posture (allowlist, no shell, timeouts) is visible in ~one module and enforceable by bandit + a dedicated test.
- No dependency on GitPython's process-management quirks, leaked file handles or its own subprocess spawning that we'd have to audit anyway.
- Cost: manual parsing of `git log` output — bounded, format-pinned (`--format` with explicit field separators) and covered by fixture tests.

## Alternatives considered

- **GitPython:** convenient API, but it shells out internally with less control, has a history of resource-handling issues, and hides the exact commands from our allowlist policy.
- **pygit2 (libgit2):** fast and safe, but a heavier native dependency than a prototype warrants.
- **dulwich (pure Python):** slower on large histories; parsing pack data ourselves buys nothing here.

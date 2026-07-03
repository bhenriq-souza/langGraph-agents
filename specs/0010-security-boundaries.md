---
id: "0010"
title: Security boundaries
status: approved
depends_on: ["0000"]
---

# 0010 — Security Boundaries

## Goal

Define the security policy every component must obey: filesystem confinement, read-only guarantee, subprocess discipline, resource limits, offline operation and log hygiene. This spec is cross-cutting — other specs reference its invariants.

## Scope / Non-goals

- **In scope:** path policy, read-only rules, subprocess rules, limits, network policy, logging policy.
- **Non-goals:** sandboxing at the OS level (containers/seccomp — possible hardening, out of MVP scope), authn/z for the HTTP transport (localhost-only in this phase, ADR 0003).

## Contracts

### `SecurityPolicy` (component in `agents_core`, injected everywhere paths are handled — spec 0012)

```python
class SecurityPolicy:
    allowed_base_dirs: tuple[Path, ...]   # from AGENTS_ALLOWED_BASE_DIRS; default ("/home/bhs/code",)
    reports_dir: Path                     # from AGENTS_REPORTS_DIR; must resolve inside an allowed base or its own allowlisted location

    def validate_repo_path(self, raw: str) -> Path: ...
    def validate_report_target(self, path: Path) -> Path: ...
    def is_within_repo(self, path: Path, repo_root: Path) -> bool: ...
```

**`validate_repo_path` algorithm (normative):**
1. Reject non-absolute input (`INVALID_PATH`).
2. `Path(raw).resolve(strict=True)` — resolves symlinks and `..`; missing path → `INVALID_PATH`.
3. Resolved path must be a directory (`INVALID_PATH`).
4. Confinement check: `resolved` equals or is a descendant of one of `allowed_base_dirs` (each also resolved), compared via `Path.is_relative_to` — **string prefix comparison is forbidden** (avoids `/home/bhs/code-evil` bypass).
5. Failure → `PATH_NOT_ALLOWED` (message lists allowed bases, never internal details).

The same resolve-then-confine check applies to every path derived later (symlinked files during scanning — INV-0004-03; report targets).

### Read-only guarantee

- No component holds a writable handle to anything under `repo.root`.
- The only write surface in the whole pipeline is `ReportStorage` (spec 0009) plus the phase-2 PostgreSQL chunk cache (ADR 0007) — a database, never the local filesystem.
- Enforced by construction (only `ReportStorage` imports write APIs) and by test: fixture-repo tree hash + mtimes identical before/after a full run.

### Subprocess discipline

- Only `GitCollector` may spawn processes (INV-0005-01: argv allowlist, `shell=False`, timeout, minimal env: `PATH`, `HOME`, `GIT_TERMINAL_PROMPT=0`, `LC_ALL=C`).
- `bandit` gate (spec 0013) fails the build on `shell=True`, `os.system`, `eval`/`exec`.

### Resource limits (defaults; all configurable — spec 0012)

| Limit | Default |
|-------|---------|
| `max_repo_files` / `max_repo_bytes` | 50 000 / 2 GiB (fatal pre-scan) |
| `max_files_analyzed` | 2 000 (soft) |
| `max_chunks_scored` | 1 500 (soft) |
| `max_total_lines_scored` | 200 000 (soft) |
| `analysis_deadline_seconds` | 600 |
| `llm_call_timeout_seconds` | 120 |
| `git_call_timeout_seconds` | 30 |

### Network policy

- Exactly two network destinations are permitted:
  1. `settings.ollama_base_url` — must resolve to a loopback address (validated at startup; non-loopback requires explicit `AGENTS_ALLOW_NON_LOCAL_OLLAMA=true` opt-in, logged loudly). This is the only destination that ever receives code content.
  2. `settings.cache_database_url` (phase 2, optional) — a PostgreSQL server, typically on the local network (homelab) but any Postgres provider works. The cache connection carries **only content hashes, scores, signals and brief rationales — never raw chunk content** (ADR 0007). TLS (`sslmode=require`) recommended when the server is not on a trusted local network. Unreachable database degrades the cache to no-op; it never blocks or fails an analysis.
- No telemetry, no update checks, no external APIs. Analyzed code never leaves the machine by default.

### Logging & data hygiene

- Structured logs (structlog). INFO level: paths, counts, durations, codes — never chunk content or prompts.
- DEBUG may include prompt/response bodies **only** when `AGENTS_DEBUG_LOG_CONTENT=true` (default false).
- Error messages returned to the MCP host include the offending path and remediation hint, nothing else from the filesystem.
- Reports themselves necessarily contain file paths and signal summaries — but no raw code excerpts in the MVP report (evidence is signal names + probabilities; excerpts are a possible future opt-in).

## Invariants

- **INV-0010-01:** a full analysis run performs zero writes under `repo.root` (tree-hash test).
- **INV-0010-02:** every externally supplied path passes `SecurityPolicy` before any I/O uses it.
- **INV-0010-03:** path confinement uses resolved paths + `is_relative_to`; no string prefix matching.
- **INV-0010-04:** the process spawns no executables other than `git` (allowlisted argv).
- **INV-0010-05:** chunk content never appears at INFO log level.
- **INV-0010-06:** code content travels only to loopback (Ollama) unless the explicit opt-in flag is set; the only other permitted destination is the configured cache database, which never receives raw chunk content.

## Error cases

Path-policy violations map to `INVALID_PATH` / `PATH_NOT_ALLOWED` / `REPORT_WRITE_FAILED` (spec 0002). Policy violations discovered mid-run (symlink escape) degrade per spec 0004 — they never crash the run.

## Acceptance criteria

- **AC-0010-01:** traversal attempts (`/home/bhs/code/../.ssh`, symlink dir → `/etc`, prefix-cousin `/home/bhs/code-evil`) are all rejected with `PATH_NOT_ALLOWED`.
- **AC-0010-02:** relative and nonexistent paths → `INVALID_PATH`.
- **AC-0010-03:** full fixture run leaves the repo tree byte-identical (hash comparison).
- **AC-0010-04:** log capture at INFO during a run contains no chunk content substring (canary string planted in fixture code).
- **AC-0010-05:** non-loopback `ollama_base_url` without the opt-in flag fails startup.

## Test mapping

| Item | Test |
|------|------|
| AC-0010-01, 02 | `packages/core/tests/test_security_policy.py` |
| AC-0010-03 | `tests/integration/test_readonly_guarantee.py` |
| AC-0010-04 | `tests/integration/test_log_hygiene.py` |
| AC-0010-05 | `packages/core/tests/test_settings.py` |
| INV-0010-04 | bandit gate + `test_git_collector.py::test_allowlist` |

## Open questions

None.

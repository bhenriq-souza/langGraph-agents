---
id: "0012"
title: Configuration & dependency injection
status: approved
depends_on: ["0000", "0010"]
---

# 0012 — Configuration & Dependency Injection

## Goal

Define how the system is configured (pydantic-settings, env-first) and how components are composed with **`dependency-injector`** declarative containers (ADR 0004), so every component is replaceable in tests and the LangGraph graph receives fully-built services.

## Scope / Non-goals

- **In scope:** settings schema, env variables, container layout, wiring rules, protocols for injectable components, logging setup.
- **Non-goals:** the components' internal behavior (their own specs), secrets management (nothing secret exists in this offline system).

## Contracts

### Settings — `AgentsSettings` (pydantic-settings, `agents_core.settings`)

Env prefix `AGENTS_`; `.env` file supported (dev convenience); env always wins.

| Key (env var) | Type | Default |
|---------------|------|---------|
| `AGENTS_ALLOWED_BASE_DIRS` | `list[Path]` (colon-separated) | `/home/bhs/code` |
| `AGENTS_REPORTS_DIR` | `Path` | `<workspace>/reports` |
| `AGENTS_OLLAMA_BASE_URL` | `AnyHttpUrl` | `http://127.0.0.1:11434` |
| `AGENTS_ALLOW_NON_LOCAL_OLLAMA` | `bool` | `false` |
| `AGENTS_DEFAULT_MODEL` | `str` | `qwen2.5-coder:14b-instruct-q4_K_M` |
| `AGENTS_REVIEW_MODEL` | `str \| None` | `deepseek-r1:14b` (unused in MVP) |
| `AGENTS_MCP_TRANSPORT` | `Literal["stdio","http"]` | `stdio` |
| `AGENTS_MCP_HTTP_PORT` | `int` | `8765` |
| `AGENTS_LOG_LEVEL` | `str` | `INFO` |
| `AGENTS_DEBUG_LOG_CONTENT` | `bool` | `false` |
| Budget/limit keys | ints | as tabled in spec 0010 |
| `AGENTS_CACHE_DATABASE_URL` | `PostgresDsn \| None` | `None` (phase 2; unset ⇒ `NoopChunkCache`. Any PostgreSQL provider — homelab server, container, managed instance) |

Validation at load: reports dir confinement, loopback check (AC-0010-05), budget sanity (positive ints). A frozen `AnalysisSettings` subset is snapshotted into `AuditState` (spec 0003) so a run is immune to mid-run env changes.

### Injectable protocols (defined in `agents_core.protocols` / agent `application/`)

Each infrastructure component is consumed through a `typing.Protocol`, never a concrete class:

`OllamaClientProtocol`, `FileScannerProtocol`, `GitCollectorProtocol`, `ChunkerProtocol`, `LLMScorerProtocol`, `ScoreAggregatorProtocol`, `ReportRendererProtocol`, `ReportStorageProtocol`, `ChunkCacheProtocol` (phase 2, no-op default), `Clock`, `LoggerFactory`.

### Container — `AuditorContainer` (`dependency_injector.containers.DeclarativeContainer`)

Owned by the deployable (the MCP server builds exactly one at startup):

```python
class AuditorContainer(containers.DeclarativeContainer):
    settings         = providers.Singleton(AgentsSettings)
    logger_factory   = providers.Singleton(configure_structlog, settings=settings)
    clock            = providers.Singleton(SystemClock)
    security_policy  = providers.Singleton(SecurityPolicy, settings=settings)
    ollama_client    = providers.Singleton(OllamaClient, settings=settings)
    file_scanner     = providers.Factory(FileScanner, security_policy=security_policy)
    git_collector    = providers.Factory(GitCollector, settings=settings)
    chunker          = providers.Factory(LineWindowChunker)
    chunk_cache      = providers.Singleton(NoopChunkCache)          # PostgreSQL impl in phase 2 (ADR 0007)
    llm_scorer       = providers.Factory(OllamaChunkScorer,
                                         client=ollama_client, cache=chunk_cache, clock=clock)
    score_aggregator = providers.Factory(ScoreAggregator)
    report_renderer  = providers.Factory(ReportRenderer, clock=clock)
    report_storage   = providers.Singleton(ReportStorage, security_policy=security_policy)
    graph            = providers.Factory(build_graph)                # receives the services above
```

### Wiring rules (normative)

1. **No `@inject` / wiring markers inside LangGraph nodes or domain code.** The graph is produced by `build_graph(scanner=..., git_collector=..., ...)` — a plain factory taking resolved services; nodes are closures/bound methods over them. `dependency-injector` is used at the **composition root only** (MCP server startup).
2. Domain layer (`domain/`) has zero imports from `dependency_injector`, infrastructure, or I/O modules — pure functions and Pydantic models.
3. Tests override providers: `container.ollama_client.override(providers.Object(fake))` — the documented substitution mechanism for every layer above unit-pure code.
4. Exactly one container class per deployable; shared packages define components, never containers.

### Logging

`configure_structlog(settings)` in `agents_core.logging`: JSON renderer, ISO timestamps, correlation id bound per MCP invocation, level from settings. All components receive loggers via `logger_factory(name)` — no module-level `structlog.get_logger()` calls in components (keeps configuration injectable).

## Invariants

- **INV-0012-01:** `dependency_injector` imports exist only in container modules and the MCP server entrypoint.
- **INV-0012-02:** domain modules import neither infrastructure nor `dependency_injector` (import-linter contract, spec 0013).
- **INV-0012-03:** every setting has a safe default; the system boots with zero env vars set (dev mode).
- **INV-0012-04:** a run's behavior depends only on the `AnalysisSettings` snapshot taken at `validate_input`.

## Error cases

| Case | Behavior |
|------|----------|
| Invalid env value | startup fails fast with the pydantic error naming the variable |
| Reports dir violates policy | startup fails (`REPORT_WRITE_FAILED` semantics at boundary) |

## Acceptance criteria

- **AC-0012-01:** container builds and resolves the full graph with zero env vars set.
- **AC-0012-02:** overriding `ollama_client` with the fake changes scoring behavior with no other code touched (canonical DI test).
- **AC-0012-03:** import-linter passes: domain → {application, infrastructure, containers} imports are forbidden and verified.
- **AC-0012-04:** env var change after snapshot does not affect an in-flight run.

## Test mapping

| Item | Test |
|------|------|
| AC-0012-01, 02, 04 | `agents/ai_repo_auditor/tests/test_container.py` |
| AC-0012-03 | `uv run lint-imports` in the quality pipeline (spec 0013) |
| INV-0012-03 | `packages/core/tests/test_settings.py` |

## Open questions

None.

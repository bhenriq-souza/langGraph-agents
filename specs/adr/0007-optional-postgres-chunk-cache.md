---
id: "ADR-0007"
title: Optional PostgreSQL chunk-score cache (phase 2)
status: accepted
---

# ADR 0007 — Optional PostgreSQL Chunk-Score Cache

> Amended 2026-07-03, during the planning phase (pre-implementation): the cache backend
> was changed from SQLite to PostgreSQL. Since no code exists yet, the ADR was amended
> in place instead of superseded.

## Context

Scoring is the expensive stage: one local-LLM call per chunk (hundreds to ~1500 per run, seconds each on a 14B model). Re-runs after truncation, interruption, prompt-parameter tweaks or small repo changes would re-pay the full cost, since most chunk contents are unchanged. The user operates a PostgreSQL server in their homelab, available as durable shared infrastructure.

## Decision

Add (in **phase 2**, not the MVP) a `ChunkCacheProtocol` implementation backed by **PostgreSQL**, connected via a standard DSN (`AGENTS_CACHE_DATABASE_URL`, spec 0012) so it works against **any PostgreSQL provider** — the homelab server is the primary target, but a managed instance (RDS, Neon, Supabase, …) or a local container works identically. Driver: `psycopg` (v3).

Schema (single table, created idempotently at startup):

```sql
CREATE TABLE IF NOT EXISTS chunk_scores (
  content_hash   text        NOT NULL,
  model          text        NOT NULL,
  prompt_version text        NOT NULL,
  score          jsonb       NOT NULL,   -- serialized ChunkScore
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (content_hash, model, prompt_version)
);
```

`score_chunks_with_llm` consults the cache before calling Ollama and writes back after scoring (`INSERT … ON CONFLICT DO NOTHING`). The MVP ships a `NoopChunkCache` so the seam exists from day one (spec 0012 container). Invalidation is automatic by key design: any change to chunk content, model or prompt version misses the cache.

Operational rules:

- **Data hygiene:** the cache stores only content hashes, scores, signals and brief rationales — **never raw chunk content** — so analyzed code does not leave the machine even when the database is remote (spec 0010).
- **Graceful degradation:** if the database is unreachable at startup or mid-run, the cache silently degrades to no-op behavior (one warning logged); the cache is an optimization, never a hard dependency of an analysis run.
- TLS (`sslmode=require`) is recommended in the DSN whenever the server is not on a trusted local network.

## Consequences

- Re-analysis of a mostly-unchanged repo costs only the delta — makes iterative use (and post-truncation resumption) practical.
- A central cache is shared across machines, checkouts and future agents; concurrent writers are safe (real transactional server, `ON CONFLICT` upserts).
- Reuses infrastructure the user already operates; no per-project database files to manage.
- Adds a network dependency and one driver dependency — mitigated by the no-op degradation rule and by the DSN being optional (unset ⇒ `NoopChunkCache`).
- Cached scores can go stale relative to *aggregation* logic changes — acceptable, since aggregation reruns on every analysis; only the per-chunk LLM judgment is cached.

## Alternatives considered

- **SQLite (original decision):** zero-ops and adequate for single-machine use, but per-machine/per-file caches don't benefit from existing homelab infrastructure, are awkward to share across checkouts and agents, and offer weaker concurrent-write behavior. Superseded by this amendment.
- **LangGraph checkpointers (incl. the Postgres checkpointer):** persists whole graph state — heavier, solves a different problem (mid-run resume) less cleanly than idempotent re-runs over a cache.
- **JSON-file cache:** no concurrent-write safety, O(n) rewrites.
- **Redis:** fast but adds a second service dependency the user doesn't already run for this purpose; persistence semantics weaker than needed for a durable cache.
- **No cache ever:** rejected — repeated full-cost runs make the tool painful on real repos.

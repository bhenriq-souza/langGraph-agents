---
id: "ADR-0004"
title: dependency-injector at the composition root
status: accepted
---

# ADR 0004 — `dependency-injector` at the Composition Root

## Context

The pipeline composes ~12 injectable components (Ollama client, scanner, git collector, chunker, scorer, aggregator, renderer, storage, security policy, cache, clock, logging). Tests must swap any of them with fakes. The user selected the `dependency-injector` library over hand-rolled wiring.

## Decision

Use **`dependency-injector` declarative containers**, confined to the **composition root**: one `AuditorContainer` per deployable, built at MCP-server startup. Components are consumed through `typing.Protocol` interfaces; the LangGraph graph is created by a plain factory receiving resolved services. **No `@inject` decorators or wiring inside nodes, application or domain code** — domain stays free of any DI imports (import-linter enforced).

## Consequences

- Declarative provider graph with singleton/factory lifecycles and first-class test overrides (`provider.override(...)`).
- Confinement to the root keeps the library's weaker typing and "magic" out of business code; swapping the library later would touch two modules.
- One extra runtime dependency in the agent package.

## Alternatives considered

- **Hand-rolled container (constructor injection only):** zero deps, fully typed — rejected by user preference for the library's structure.
- **`punq` / `svcs` / `wired`:** smaller libraries, fewer features and less documentation; no advantage here.
- **Module-level singletons:** rejected — untestable, hidden coupling.

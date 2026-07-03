---
id: "ADR-0002"
title: LangGraph as pipeline orchestrator
status: accepted
---

# ADR 0002 — LangGraph as Pipeline Orchestrator

## Context

The analysis is a multi-stage pipeline (validate → scan → filter → git → chunk → score → aggregate → report) with typed state, error routing, budget enforcement and planned extensions (review model, HITL checkpoint, caching). The design principle is robustness over LLM autonomy: deterministic Python flow, LLM used only for structured classification.

## Decision

Use **LangGraph `StateGraph`** as the orchestrator: nodes are deterministic Python callables over a Pydantic `AuditState`; conditional edges route fatal errors to a single error-response node; the graph is a DAG (no cycles — retries live inside nodes with fixed bounds). LangGraph is chosen for its state model, conditional routing, and future interrupt/checkpoint support — not for agentic loops or local-model tool calling, which are explicitly excluded from the MVP.

## Consequences

- Flow is inspectable, testable node-by-node, and extension nodes slot in without changing existing contracts.
- Future HITL (`interrupt`) and persistence (checkpointers) come free when needed.
- Cost: a framework dependency where plain function composition would suffice for the MVP — accepted for the extension roadmap.

## Alternatives considered

- **Plain function pipeline:** simplest, but re-implements state passing, error routing and future interrupts by hand.
- **Autonomous tool-calling agent:** rejected — local 14B models are unreliable tool-callers and the task is a fixed pipeline, not open-ended.
- **Prefect/Dagster-style workflow engines:** rejected — infrastructure weight without LLM-ecosystem benefits.

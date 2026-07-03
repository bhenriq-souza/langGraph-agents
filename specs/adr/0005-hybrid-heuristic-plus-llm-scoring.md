---
id: "ADR-0005"
title: Hybrid scoring — deterministic heuristics + LLM classification
status: accepted
---

# ADR 0005 — Hybrid Heuristic + LLM Scoring

## Context

AI-authorship estimation from code alone is inherently uncertain. Pure heuristics miss stylistic nuance; pure LLM judgment is noisy, uncalibrated and expensive per token. The output must be an honest probabilistic estimate with confidence, never a claim of detection.

## Decision

Combine two independent signal sources:

1. **Deterministic heuristics** (pure Python, fully testable): Git history shape (single large creation commit, AI-keyword messages, incremental-evolution counter-signal) producing a **bounded prior of ±0.15** per file; plus classification rules that exclude or down-weight generated/vendored/minified content.
2. **LLM structured classification** per chunk (local model, temperature 0, JSON schema, closed signal vocabulary, versioned prompt) producing probability + confidence + named signals.

Aggregation is a pure line-weighted computation (spec 0008); confidence reflects coverage, model confidence and dispersion, and is capped at "medium" for truncated runs. The prompt itself instructs calibration and forbids treating the judgment as proof.

## Consequences

- The LLM contributes nuance while hard-bounded priors and deterministic aggregation keep the pipeline reproducible and testable without a model.
- Estimates vary across models/prompt versions — accepted and disclosed (`prompt_version` + model recorded in every report).
- The closed signal vocabulary makes evidence explainable and comparable across runs.

## Alternatives considered

- **Heuristics only:** cheap and deterministic but blind to style; produces weak evidence.
- **LLM only:** uncalibrated single point of failure; unusable offline-tested.
- **Fine-tuned classifier:** no labeled dataset exists; disproportionate effort for a prototype.

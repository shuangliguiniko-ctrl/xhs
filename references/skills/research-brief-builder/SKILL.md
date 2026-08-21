---
name: research-brief-builder
description: Build and confirm an auditable user-research brief for social-listening, product-experience, competitor, reputation, risk, or Xiaohongshu studies. Use before collection or analysis when the research object, decision, source scope, labels, focus rules, prompts, audience, or external-LLM authorization is missing or ambiguous.
---

# Research Brief Builder

Inspect source metadata first. Ask only one brief section at a time and explain its decision impact. Present 2–4 concrete options plus custom input; offer explicit Auto when safe and never interpret silence as Auto. Keep the active question short enough to answer without reading the entire protocol.

Collect seven decision sections in order: decision; subject/users; source/sampling; analysis; evidence; output; privacy/external AI. Within analysis, ask topic engine and research profile as separate choices and explain their different roles. Preserve requested and resolved values plus rationale. Mark unknown collection facts unknown. Present a compact final brief and require explicit confirmation before creating a confirmed project.

Generate `research_brief.yaml` through `python scripts/launch.py init --config PROJECT.yaml`. Use the schema in `../../analysis-contract.md`.

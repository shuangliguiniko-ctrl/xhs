---
name: opinion-analysis-engine
description: Run reproducible rapid, discovery, aspect, experience, comparative, network, predictive, or mixed analysis on cleaned opinion data, alongside explicit fast, semantic, or auto topic engines. Use when a user needs row-linked text analysis, cohort contrasts, user-research synthesis, co-occurrence graphs, or leakage-aware ML.
---

# Opinion Analysis Engine

Explain and require one mode:

- `fast`: local deterministic TF-IDF/K-Means and sklearn LDA; CPU-friendly.
- `semantic`: local embeddings plus BERTopic/HDBSCAN; requires optional packages and may download a model after authorization.
- `auto`: explicit delegation; record the actual engine used.

Never silently fall back from semantic. Treat sentiment rules as a baseline and topics as exploratory. Export module version, config, metrics, tables, evidence, warnings, and limitations. Run `python scripts/launch.py analyze --project NAME --mode MODE`.

Require one research profile separately from the topic engine. For `predictive`, route to `../predictive-modeler/SKILL.md`. For profile selection and stop rules, read `../../analysis-modes.md`. Run `python scripts/launch.py analyze --project NAME --mode MODE --profile PROFILE`.

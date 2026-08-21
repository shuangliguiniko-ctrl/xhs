# Analysis contract

## Contents

1. Guided intake
2. Explicit topic mode
3. Source and field mapping
4. External LLM authorization
5. Evidence and reporting

## Guided intake

Inspect file schema, missingness, duplicates, candidate text/time/source/ID/engagement fields, and collection context first. Ask one section at a time: project, source, AI labels, insights, focus rules, prompt specifications, output. For each section, explain what changes, and require explicit Auto or custom input. Record `requested`, `resolved`, `origin`, and Auto rationale. Never invent unknown sampling, geography, demographics, reach, or causal impact. Confirm the final brief before collection or analysis.

## Explicit topic mode

- `fast`: local TF-IDF/K-Means plus sklearn LDA. Deterministic and CPU-friendly.
- `semantic`: local multilingual embeddings plus BERTopic/HDBSCAN. Better for paraphrases but requires optional packages and possible model download.
- `auto`: explicit delegation to select using corpus size and installed dependencies. Record actual mode.

None is an implicit default for a real study. If semantic dependencies are missing, pause for installation/download authorization. Never silently fall back.

## Explicit research profile

Require `rapid`, `discovery`, `aspect`, `experience`, `comparative`, `network`, `predictive`, or `mixed`. For `mixed`, record the exact profile list. Read `analysis-modes.md` for inputs and stop rules. Predictive mode additionally requires target, task, features, split structure, and minimum-sample gates; a polished report must not obscure a skipped or weak model.

## Source and field mapping

Preserve one or more text fields, a stable ID, and original text internally. Map time, platform/source, author, URL, and engagement only when present. If multiple plausible text columns exist, ask before analysis. Report keyword, ranking, sample depth, observation window, accessible-comment scope, deleted/unavailable content, and recommendation/ranking bias.

## External LLM authorization

Prompt configuration is not transfer authorization. Keep `llm.provider: none` unless the user names a provider, authorizes text transfer, defines `allowed_text`, and sets a row limit. Read API keys only from the configured environment variable. Keep TLS verification on, cache by prompt/model hash, validate JSON, and route low-confidence results to review.

## Evidence and reporting

Require counts or rates, denominator, multiple row IDs, representative excerpts, applicability, confidence, and limitations. Separate observation, model result, interpretation, recommendation, and hypothesis. Treat engagement as review priority, topics as exploratory, dictionary sentiment as a baseline, and risk scores as triage—not probability.

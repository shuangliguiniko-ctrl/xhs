---
name: opinion-data-cleaner
description: Normalize, redact, deduplicate, score marketing content, assess research relevance, split review/excluded datasets, and produce quality diagnostics for Chinese or multilingual opinion data. Use after collection/import and before topics, sentiment, user insights, or reports.
---

# Opinion Data Cleaner

Preserve immutable IDs and original text internally. Normalize Unicode, time, numeric fields, and text while preserving emojis. Redact phone, email, account, and URL tokens from shareable fields.

Combine stable-ID, exact-text, and SimHash near-duplicate checks. Score marketing and relevance from transparent multi-signal rules. Do not permanently delete borderline records; route them to review with reasons.

Run `python scripts/launch.py clean --project NAME`. Reconcile raw, valid, excluded, duplicate, marketing, irrelevant, missing-time, and record-type counts in `data_quality.json`.

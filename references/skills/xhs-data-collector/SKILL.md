---
name: xhs-data-collector
description: Collect, import, normalize, merge, resume, and persist Xiaohongshu note/comment records through BrowserAct, MediaCrawler, hybrid, local-file, or mock adapters. Use for authorized RedNote research collection, existing XLSX/CSV/JSONL ingestion, crawl recovery, source diagnostics, or raw posts/comments/failures.
---

# XHS Data Collector

Require confirmed `research_brief.yaml` and `crawl_plan.yaml`. Use `mock` for tests, `import` for existing exports, `browseract` for composite JSON/JSONL persisted after BrowserAct operation, `mediacrawler` for an accepted local installation or saved output directory, and `hybrid` only when both sources are ready.

Persist each completed note before continuing. Deduplicate by stable content/comment IDs. Retain tokenized detail URLs internally but redact tokens from shared reports. Stop and report when login or verification requires the user; never bypass it.

Run `python scripts/launch.py crawl --config PROJECT.yaml`. Verify raw JSONL schema, failures log, counts, and resume state.

The `browseract` adapter does not drive login inside Python or hold cookies. Load the installed BrowserAct Skill, read Core instructions, follow Open → State → Interact → Verify → Close, then set `crawler.browseract_input_path`. Set `crawler.mediacrawler_input_path` to reuse saved MediaCrawler JSONL output without launching a live crawl. Hybrid mode merges stable platform/content/type IDs, records source adapters, and emits an overlap audit.

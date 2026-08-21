---
name: xhs-crawler-planner
description: Design a compliant Xiaohongshu keyword, sampling, field, comment, retry, and resume plan from a confirmed research brief. Use when planning RedNote search collection, comparing quick/standard/deep scopes, documenting query provenance, or generating crawl_plan.yaml without starting collection.
---

# XHS Crawler Planner

Require a confirmed brief. Expand core terms into product/alias, feature, scene, pain, emotion, competitor, and exclusion groups. Record every term's purpose, origin, priority, and combinations.

Choose quick, standard, deep, or custom scope. Select `browseract` for authorized page interaction and precision checks, `mediacrawler` for batch keyword/comment coverage, `hybrid` for two-source verification and coverage, or `import` for local files. Default to minimum personal data, one serial browser session, bounded concurrency, randomized intervals, incremental persistence, and resumable IDs. Never design verification bypass or access-control circumvention.

Write `crawl_plan.yaml`. Separate `executed_keywords` from `suggested_keyword_expansions`; mark every suggestion `executed: false` until it is copied into the confirmed keyword list. Show the workflow mode, adapter, exact execution keywords, estimated volume, coverage tradeoffs, known ranking bias, comments depth, retained fields, retry/resume rules, source-readiness requirements, and confirmation status. Require a second explicit confirmation before `browseract`, `mediacrawler`, or `hybrid` collection and save `crawler.plan_confirmed: true` only after approval.

---
name: environment-diagnostics
description: Diagnose Python compatibility, core and semantic dependencies, Streamlit, BrowserAct CLI and persisted input, MediaCrawler code or saved output, local-file readiness, paths, permissions, and project output writability. Use in workflow step two or when crawl, analysis, UI, or packaging fails.
---

# Environment Diagnostics

Run `python scripts/launch.py diagnose`, or add `--config PROJECT.yaml` after an adapter is selected. Report core, UI, semantic, BrowserAct, MediaCrawler, import, hybrid, and selected-adapter readiness separately. Distinguish tool presence from live login/session availability. Never install or download models without authorization. Do not print cookies, API keys, or tokenized URLs.

If semantic mode is selected and packages are absent, show `pip install -r scripts/runtime/requirements-advanced.txt` and pause for authorization. If BrowserAct or MediaCrawler is absent, incompatible, logged out, or lacks persisted input, keep import/mock workflows available and report the exact limitation. Mark Hybrid ready only when a BrowserAct composite file and one MediaCrawler source are both ready.

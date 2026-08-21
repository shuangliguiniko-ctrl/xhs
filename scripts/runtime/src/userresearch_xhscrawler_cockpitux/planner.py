from __future__ import annotations

from datetime import datetime, timezone
from itertools import product
from typing import Any


def build_crawl_plan(config: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    crawler = config["crawler"]
    core = [str(value).strip() for value in crawler.get("keywords", []) if str(value).strip()]
    subject = str(config.get("analysis", {}).get("subject", "")).strip()
    if not core and subject:
        core = [subject]
    scenes = ["使用体验", "真实评价", "问题", "避坑", "推荐"]
    competitors = [str(value) for value in config.get("analysis", {}).get("competitors", []) if str(value).strip()]
    taxonomy = config.get("analysis", {}).get("taxonomy", {})
    groups: list[dict[str, Any]] = []
    for term in core:
        groups.append({"keyword": term, "group": "core", "priority": 1, "origin": "user_or_subject", "purpose": "主体覆盖"})
    seen = set()
    groups = [item for item in groups if not (item["keyword"] in seen or seen.add(item["keyword"]))]
    suggested = [
        {"keyword": f"{left} {right}", "group": "scene", "purpose": "体验与评价场景覆盖", "origin": "system_suggestion", "executed": False}
        for left, right in list(product(core[:5], scenes))[:20]
    ]
    for group, purpose in (("features", "功能与体验方面覆盖"), ("scenarios", "使用场景覆盖"), ("pain_points", "痛点表达覆盖"), ("needs", "需求表达覆盖")):
        labels = list((taxonomy.get(group) or {}).keys())[:8]
        suggested.extend(
            {"keyword": f"{core[0]} {label}", "group": group, "purpose": purpose, "origin": "confirmed_taxonomy", "executed": False}
            for label in labels
            if core
        )
    suggested.extend({"keyword": term, "group": "competitor", "purpose": "竞品覆盖", "origin": "competitor_suggestion", "executed": False} for term in competitors if term not in core)
    unique_suggestions: list[dict[str, Any]] = []
    suggestion_seen: set[str] = set(core)
    for item in suggested:
        if item["keyword"] not in suggestion_seen:
            suggestion_seen.add(item["keyword"])
            unique_suggestions.append(item)
    presets = {
        "quick": {"recommended_notes": "100-500", "comments": "optional"},
        "standard": {"recommended_notes": "500-3000", "comments": "first-level"},
        "deep": {"recommended_notes": "3000+", "comments": "first and second-level"},
        "custom": {"recommended_notes": str(crawler.get("max_notes")), "comments": "configured"},
    }
    return {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": config["project"]["name"],
        "brief_confirmed": brief["confirmed"],
        "confirmed": bool(crawler.get("plan_confirmed")),
        "adapter": crawler["adapter"],
        "workflow_mode": config.get("workflow", {}).get("mode"),
        "collection_strategy": {
            "browseract": "authorized page interaction and persisted composite JSON/JSONL",
            "mediacrawler": "confirmed keyword batch collection or persisted MediaCrawler output",
            "hybrid": "BrowserAct verification plus MediaCrawler coverage with stable-ID merge",
            "import": "local CSV/XLSX/JSONL/JSON/Parquet import",
            "mock": "synthetic installation test only",
        }.get(crawler["adapter"], "legacy browser import"),
        "mode": crawler.get("mode", "custom"),
        "mode_guidance": presets.get(crawler.get("mode"), presets["custom"]),
        "keyword_groups": groups,
        "executed_keywords": core,
        "suggested_keyword_expansions": unique_suggestions,
        "excluded_keywords": crawler.get("excluded_keywords", []),
        "limits": {key: crawler.get(key) for key in ("max_notes", "include_comments", "include_sub_comments", "max_comments_per_note", "concurrency", "request_interval_seconds", "retries")},
        "fields": ["content_id", "title", "content", "publish_time", "engagement", "hashtags", "url", "visible_comments"],
        "privacy": {"retain_author_fields": crawler.get("retain_author_fields", False), "download_media": crawler.get("download_media", False), "principle": "data minimization"},
        "biases": ["search ranking and recommendation bias", "access/login visibility", "deleted or unavailable notes", "visible comments only"],
        "compliance": {"bypass_verification": False, "bypass_access_controls": False, "authorized_access_only": True},
        "decision_logic": {
            "execute_only_confirmed_keywords": True,
            "suggestions_are_not_executed": True,
            "live_collection_requires_plan_confirmation": True,
            "resume_by_stable_id": True,
            "hybrid_requires_two_ready_sources": crawler["adapter"] == "hybrid",
            "local_import_skips_live_collection": crawler["adapter"] == "import",
        },
    }

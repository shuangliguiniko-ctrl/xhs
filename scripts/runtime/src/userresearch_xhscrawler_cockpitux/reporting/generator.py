from __future__ import annotations

from datetime import datetime
import html
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ..storage import ProjectPaths, read_json
from ..config import ASSET_ROOT, read_yaml
from ..interaction import config_summary, selection_catalog


def _json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str).replace("</", "<\\/")


def _template_path() -> Path:
    return ASSET_ROOT / "templates" / "report" / "base.html"


def generate_report(config: dict[str, Any], paths: ProjectPaths) -> Path:
    analysis = read_json(paths.analysis / "analysis.json", {})
    insights = read_json(paths.analysis / "insight_summary.json", {})
    quality = read_json(paths.processed / "data_quality.json", {})
    brief = read_json(paths.root / "analysis_brief.json", {})
    crawl_plan = read_yaml(paths.root / "crawl_plan.yaml") if (paths.root / "crawl_plan.yaml").exists() else {}
    collection_observation = read_json(paths.root / "collection_observation.json", {})
    frame = pd.read_csv(paths.analysis / "enriched.csv")
    safe_columns = [
        column for column in [
            "record_id", "record_type", "source_keyword", "publish_time", "clean_text", "sentiment",
            "sentiment_score", "topic_name", "emotion_labels", "feature_labels", "scenario_labels",
            "purpose_labels", "pain_point_labels", "need_labels", "text_length", "like_count",
            "favorite_count", "comment_count", "share_count", "engagement_total",
        ] if column in frame
    ]
    records = frame[safe_columns].fillna("").to_dict("records")
    raw_title = str(config.get("report", {}).get("title", "小红书用户研究与舆情洞察报告"))
    title = html.escape(raw_title)
    parts = title.split(" · ", 1)
    display_title = f'{parts[0]}<span>{parts[1]}</span>' if len(parts) == 2 else title
    subject = html.escape(str(config.get("analysis", {}).get("subject") or "研究对象"))
    payload = {
        "analysis": analysis,
        "insights": insights,
        "quality": quality,
        "brief": brief,
        "crawl_plan": crawl_plan,
        "collection_observation": collection_observation,
        "config_summary": config_summary(config),
        "selection_catalog": selection_catalog(),
        "records": records,
        "report": {
            "title": raw_title,
            "subject": str(config.get("analysis", {}).get("subject") or "研究对象"),
            "audience": str(config.get("report", {}).get("audience") or "研究团队"),
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
    }
    template = _template_path().read_text(encoding="utf-8")
    document = (
        template.replace("__TITLE__", title)
        .replace("__DISPLAY_TITLE__", display_title)
        .replace("__SUBJECT__", subject)
        .replace("__GENERATED__", payload["report"]["generated"])
        .replace("__PAYLOAD__", _json_script(payload))
    )
    target = paths.report / "report.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    assets = paths.report / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "embedded-assets.json").write_text(json.dumps({
        "self_contained": True,
        "external_cdn": False,
        "visual_system": "XHS Research Studio 2.0",
        "features": ["reveal motion", "animated counters", "SVG charts", "filters", "reduced-motion support"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return target

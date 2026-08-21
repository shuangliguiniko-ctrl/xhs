from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STANDARD_FIELDS = [
    "record_id", "record_type", "parent_id", "source_platform", "source_keyword", "content_id",
    "title", "content", "author_name", "publish_time", "crawl_time", "ip_location", "like_count",
    "favorite_count", "comment_count", "share_count", "url", "raw_data", "clean_text",
    "duplicate_group", "marketing_score", "marketing_label", "marketing_reason", "relevance_score",
    "relevance_label", "relevance_reason", "topic_id", "topic_name", "sentiment", "sentiment_score",
    "emotion_labels", "brand_labels", "feature_labels", "scenario_labels", "stage_labels",
    "purpose_labels", "pain_point_labels", "need_labels", "risk_labels", "analysis_version",
]


@dataclass(slots=True)
class StandardRecord:
    record_id: str
    record_type: str
    source_platform: str
    content_id: str
    content: str
    parent_id: str = ""
    source_keyword: str = ""
    title: str = ""
    author_name: str = ""
    publish_time: str = ""
    crawl_time: str = ""
    ip_location: str = ""
    like_count: int = 0
    favorite_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    url: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.record_id.strip():
            raise ValueError("record_id is required")
        if self.record_type not in {"post", "comment", "reply"}:
            raise ValueError(f"unsupported record_type: {self.record_type}")
        if not (self.title.strip() or self.content.strip()):
            raise ValueError("title or content is required")
        for name in ("like_count", "favorite_count", "comment_count", "share_count"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


def module_result(name: str, version: str = "1.0", config: dict | None = None) -> dict[str, Any]:
    return {
        "module": name,
        "version": version,
        "config": config or {},
        "metrics": {},
        "tables": {},
        "charts": {},
        "evidence": [],
        "findings": [],
        "warnings": [],
        "limitations": [],
    }

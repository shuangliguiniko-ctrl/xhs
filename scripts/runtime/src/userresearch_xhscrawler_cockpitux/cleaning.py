from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit
from typing import Any

import jieba
import numpy as np
import pandas as pd

from .models import STANDARD_FIELDS
from .storage import ProjectPaths, read_jsonl, write_json, write_parquet_or_csv


PHONE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ACCOUNT = re.compile(r"(?:微信|VX|vx|V信|小红书号|账号)\s*[:：]?\s*[A-Za-z0-9_-]{5,}")
URL = re.compile(r"https?://[^\s]+")
MENTION = re.compile(r"(?<![A-Za-z0-9_])@[^\s#@，,。！？!?：:；;]{1,30}")
SPACE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]+|[ \t\r\f\v]+")
RESEARCH_TERM_STOPWORDS = {"体验", "产品", "智能", "使用", "真实", "评价", "问题", "推荐", "避坑"}


def redact_url(value: str) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except ValueError:
        return "[URL]"


def clean_text(value: Any, redact_pii: bool = True) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    if redact_pii:
        text = PHONE.sub("[PHONE]", text)
        text = EMAIL.sub("[EMAIL]", text)
        text = ACCOUNT.sub("[ACCOUNT]", text)
        text = MENTION.sub("[ACCOUNT]", text)
        text = re.sub(r"(?<![A-Za-z0-9_])@(?![A-Za-z0-9_])", " ", text)
        text = URL.sub("[URL]", text)
    text = SPACE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _simhash(text: str) -> int:
    tokens = [token.strip().lower() for token in jieba.lcut(text) if token.strip()]
    if len(tokens) > 2:
        tokens += ["|".join(tokens[index:index + 3]) for index in range(len(tokens) - 2)]
    vector = [0] * 64
    for token in tokens:
        digest = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big")
        for bit in range(64):
            vector[bit] += 1 if digest & (1 << bit) else -1
    result = 0
    for bit, value in enumerate(vector):
        if value >= 0:
            result |= 1 << bit
    return result


def _near_duplicate_groups(texts: list[str], threshold: float) -> list[str]:
    hashes = [_simhash(text) for text in texts]
    buckets: dict[int, list[int]] = defaultdict(list)
    groups = [""] * len(hashes)
    group_no = 0
    max_distance = max(1, math.floor(64 * (1 - threshold)))
    for index, value in enumerate(hashes):
        candidates: set[int] = set()
        for shift in (0, 16, 32, 48):
            candidates.update(buckets[(value >> shift) & 0xFFFF])
        matched = None
        for other in candidates:
            if (value ^ hashes[other]).bit_count() <= max_distance:
                matched = other
                break
        if matched is not None:
            if not groups[matched]:
                group_no += 1
                groups[matched] = f"near-{group_no:04d}"
            groups[index] = groups[matched]
        for shift in (0, 16, 32, 48):
            buckets[(value >> shift) & 0xFFFF].append(index)
    return groups


def _marketing(text: str, terms: list[str]) -> tuple[float, str, str]:
    lower = text.lower()
    hits = [term for term in terms if term.lower() in lower]
    contact = int(bool(PHONE.search(text) or EMAIL.search(text) or ACCOUNT.search(text)))
    price = int(bool(re.search(r"(?:优惠|领券|折扣|下单|购买|团购|返现)", text)))
    template = int(text.count("#") >= 6 or text.count("[话题]") >= 4)
    score = min(1.0, 0.18 * len(hits) + 0.35 * contact + 0.2 * price + 0.15 * template)
    label = "营销" if score >= 0.55 else ("疑似营销" if score >= 0.35 else "非营销")
    reason = "; ".join([*(f"命中:{term}" for term in hits[:5]), *( ["联系方式"] if contact else []), *( ["购买导向"] if price else []), *( ["模板化话题"] if template else [])]) or "未发现显著营销信号"
    return round(score, 4), label, reason


def _relevance(text: str, include: list[str], exclude: list[str]) -> tuple[float, str, str]:
    if not include:
        return 1.0, "相关", "未配置关键词，保留并标记为范围待确认"
    lower = text.lower()
    hits = [term for term in include if term and term.lower() in lower]
    excluded = [term for term in exclude if term and term.lower() in lower]
    token_coverage = len(hits) / max(1, min(4, len(include)))
    score = max(0.0, min(1.0, 0.25 + 0.75 * token_coverage - 0.5 * bool(excluded)))
    label = "相关" if score >= 0.35 else ("不确定" if score >= 0.2 else "不相关")
    reason = f"命中研究词:{hits[:6] or '无'}; 命中排除词:{excluded[:4] or '无'}"
    return round(score, 4), label, reason


def _research_terms(values: list[Any]) -> list[str]:
    """Expand confirmed Chinese queries into auditable domain tokens for relevance triage."""
    terms: list[str] = []
    for value in values:
        phrase = str(value or "").strip()
        if not phrase:
            continue
        candidates = [phrase, *re.split(r"[\s,，/、+]+", phrase)]
        for segment in list(candidates):
            candidates.extend(jieba.lcut(segment))
        for term in candidates:
            cleaned = str(term).strip().lower()
            if cleaned in RESEARCH_TERM_STOPWORDS or cleaned in {"-", "与", "和"}:
                continue
            if len(cleaned) >= 2 or re.fullmatch(r"[a-z0-9]+", cleaned):
                if cleaned not in terms:
                    terms.append(cleaned)
    return terms


def clean_project(config: dict[str, Any], paths: ProjectPaths) -> dict[str, Any]:
    rows = read_jsonl(paths.raw / "posts.jsonl") + read_jsonl(paths.raw / "comments.jsonl")
    if not rows:
        raise ValueError("No raw records found. Run crawl or import first.")
    frame = pd.DataFrame(rows)
    for column in STANDARD_FIELDS:
        if column not in frame:
            frame[column] = ""
    frame["_source_row"] = np.arange(len(frame))
    frame["_raw_text"] = frame[["title", "content"]].fillna("").astype(str).agg("\n".join, axis=1).str.strip()
    redact = bool(config["cleaning"].get("redact_pii", True))
    frame["clean_text"] = frame["_raw_text"].map(lambda value: clean_text(value, redact))
    frame["url"] = frame["url"].fillna("").astype(str).map(redact_url if redact else str)
    frame["_text_hash"] = frame["clean_text"].map(lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest())
    frame["_exact_duplicate"] = frame.duplicated(subset=["source_platform", "content_id"], keep="first") | frame.duplicated(subset=["_text_hash"], keep="first")
    frame["duplicate_group"] = _near_duplicate_groups(frame["clean_text"].tolist(), float(config["cleaning"].get("near_duplicate_threshold", 0.92)))
    frame["_near_duplicate"] = frame["duplicate_group"].ne("") & frame.groupby("duplicate_group", dropna=False).cumcount().gt(0)
    marketing_terms = config["cleaning"].get("marketing_terms") or ["广告", "优惠码", "领券", "私信下单", "商务合作"]
    marketing = frame["clean_text"].map(lambda value: _marketing(value, marketing_terms))
    frame[["marketing_score", "marketing_label", "marketing_reason"]] = pd.DataFrame(marketing.tolist(), index=frame.index)
    research_terms = _research_terms([config.get("analysis", {}).get("subject", ""), *config["crawler"].get("keywords", [])])
    excluded_terms = [str(value) for value in config["crawler"].get("excluded_keywords", [])]
    relevance = frame["clean_text"].map(lambda value: _relevance(value, research_terms, excluded_terms))
    frame[["relevance_score", "relevance_label", "relevance_reason"]] = pd.DataFrame(relevance.tolist(), index=frame.index)
    parent_relevance = frame.set_index("record_id")["relevance_score"].to_dict()
    inherited = frame["record_type"].isin(["comment", "reply"]) & frame["parent_id"].map(parent_relevance).fillna(0).ge(float(config["cleaning"].get("relevance_threshold", 0.35))) & frame["relevance_score"].lt(float(config["cleaning"].get("relevance_threshold", 0.35)))
    frame.loc[inherited, "relevance_score"] = frame.loc[inherited, "parent_id"].map(parent_relevance).astype(float) * 0.9
    frame.loc[inherited, "relevance_label"] = "相关"
    frame.loc[inherited, "relevance_reason"] = "评论继承相关父帖的研究语境；仍需结合父帖复核"
    frame["publish_time"] = pd.to_datetime(frame["publish_time"], errors="coerce", utc=True)
    for column in ("like_count", "favorite_count", "comment_count", "share_count"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).clip(lower=0).astype(int)
    empty = frame["clean_text"].eq("")
    marketing_excluded = frame["marketing_score"].ge(float(config["cleaning"].get("marketing_threshold", 0.55)))
    irrelevant = frame["relevance_score"].lt(float(config["cleaning"].get("relevance_threshold", 0.35)))
    duplicate = frame["_exact_duplicate"] | frame["_near_duplicate"]
    frame["exclusion_reason"] = ""
    frame.loc[empty, "exclusion_reason"] = "empty_text"
    frame.loc[duplicate & ~empty, "exclusion_reason"] = "duplicate"
    frame.loc[marketing_excluded & ~empty & ~duplicate, "exclusion_reason"] = "marketing"
    frame.loc[irrelevant & ~empty & ~duplicate & ~marketing_excluded, "exclusion_reason"] = "low_relevance"
    frame["review_status"] = np.where(
        frame["marketing_score"].between(0.35, 0.55, inclusive="left") | frame["relevance_score"].between(0.2, 0.35, inclusive="left"),
        "人工复核", "无需复核",
    )
    valid = frame[frame["exclusion_reason"].eq("")].copy()
    excluded = frame[frame["exclusion_reason"].ne("")].copy()
    review = frame[frame["review_status"].eq("人工复核")].copy()
    saved_valid, warnings = write_parquet_or_csv(valid, paths.processed / "cleaned_data.parquet")
    saved_excluded, excluded_warnings = write_parquet_or_csv(excluded, paths.processed / "excluded_data.parquet")
    warnings.extend(excluded_warnings)
    review[["record_id", "record_type", "clean_text", "marketing_score", "marketing_label", "marketing_reason", "relevance_score", "relevance_label", "relevance_reason", "review_status"]].to_excel(paths.processed / "review_queue.xlsx", index=False)
    quality = {
        "raw_records": int(len(frame)), "valid_records": int(len(valid)), "excluded_records": int(len(excluded)),
        "posts": int((frame["record_type"] == "post").sum()), "comments": int(frame["record_type"].isin(["comment", "reply"]).sum()),
        "empty_text": int(empty.sum()), "exact_duplicates": int(frame["_exact_duplicate"].sum()), "near_duplicates": int(frame["_near_duplicate"].sum()),
        "marketing_excluded": int(marketing_excluded.sum()), "low_relevance": int(irrelevant.sum()), "review_queue": int(len(review)),
        "missing_time": int(frame["publish_time"].isna().sum()), "time_start": valid["publish_time"].min(), "time_end": valid["publish_time"].max(),
        "keyword_coverage": {str(key): int(value) for key, value in frame["source_keyword"].fillna("unknown").value_counts().items()},
        "rules": {"dedup": "content_id + exact SHA-256 + banded SimHash", "marketing": "multi-signal transparent score", "relevance": "subject/query/exclusion coverage"},
        "files": {"cleaned": str(saved_valid), "excluded": str(saved_excluded), "review_queue": str(paths.processed / "review_queue.xlsx")},
        "warnings": warnings,
        "limitations": ["Marketing and relevance scores are triage rules, not validated classifiers.", "SimHash may miss paraphrases outside matching bands."],
    }
    write_json(quality, paths.processed / "data_quality.json")
    return quality

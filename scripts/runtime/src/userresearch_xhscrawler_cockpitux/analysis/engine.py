from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import importlib.util
import math
import os
from pathlib import Path
import re
from typing import Any

import jieba
import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics import silhouette_score

from ..models import module_result
from ..storage import ProjectPaths, write_json
from .advanced import (
    enrich_text_features,
    run_cohort_analysis,
    run_experience_analysis,
    run_network_analysis,
    run_predictive_analysis,
    run_text_diagnostics,
)


os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

STOPWORDS = {"的", "了", "是", "在", "和", "也", "就", "都", "很", "有", "我", "你", "他", "她", "它", "这个", "一个", "还是", "可以", "没有", "真的", "感觉", "一下", "以及", "进行", "用户", "小红书", "话题"}
WORD_PATTERN = r"(?u)\b\w+\b"
POSITIVE = {"喜欢", "满意", "推荐", "惊喜", "可爱", "治愈", "流畅", "清爽", "顺畅", "值得", "成功", "帮助", "期待", "方便", "稳定", "好用", "安心", "专业"}
NEGATIVE = {"失望", "不满", "愤怒", "卡顿", "失败", "无法", "问题", "担心", "焦虑", "隐私", "投诉", "退款", "难用", "崩溃", "异常", "风险", "太贵", "后悔", "厌烦"}
NEGATORS = {"不", "没", "没有", "并非", "不是", "未", "无"}
INTENSIFIERS = {"非常", "太", "特别", "极其", "严重", "真的", "很"}

EMOTION_RULES = {
    "快乐": ["快乐", "开心", "治愈", "好心情"], "愤怒": ["愤怒", "气死", "投诉"], "悲伤": ["悲伤", "难过"],
    "恐惧": ["害怕", "恐惧", "担心", "危险", "紧张"], "惊讶": ["惊讶", "没想到", "居然"], "厌恶": ["恶心", "厌恶"],
    "优越感": ["优越", "领先"], "被支配感": ["被迫", "只能"], "被剥夺感": ["不给", "缺失", "老款不支持"],
    "耻感": ["尴尬", "丢人"], "软慕感": ["羡慕", "眼馋"], "信任感": ["信任", "靠谱"], "依赖感": ["离不开", "依赖"],
    "爱意": ["喜欢", "爱", "可爱"], "谢意": ["感谢", "谢谢"], "同理心": ["理解", "同感"], "恨意": ["恨", "讨厌"],
    "边缘感": ["边缘", "忽视", "区别对待"], "压力感": ["压力", "着急"], "不确定感": ["不确定", "不知道", "什么时候", "请问"],
    "嫉妒感": ["嫉妒"], "自我实现感": ["实现", "达成", "终于"], "释放感": ["释放", "解脱"], "自在感": ["自在", "轻松"],
    "希望感": ["希望", "期待", "想要"], "后悔感": ["后悔"], "失败感": ["失败", "没成功"], "空洞感": ["空洞", "没意义"],
    "认同感": ["认同", "赞同", "我也"], "敬畏感": ["敬畏", "震撼"], "探秘感": ["探索", "揭秘", "隐藏功能"],
    "启迪感": ["启发", "学到了", "教程"], "伤逝感": ["怀念", "逝去"], "虚无感": ["虚无", "无意义"],
}
FEATURE_RULES = {
    "车机与界面": ["车机", "界面", "屏幕", "入口"], "智能座舱": ["座舱", "车内"], "OTA升级": ["ota", "升级", "更新", "推送"],
    "宠物主题": ["宠物", "猫咪", "狗狗", "萌宠", "动态屏保", "艺术相框"], "语音助手": ["语音", "助手", "识别"],
    "连接与生态": ["连接", "生态", "app"], "性能稳定": ["卡顿", "流畅", "崩溃", "稳定", "失败"],
    "设计外观": ["设计", "外观", "清爽", "动画"], "价格成本": ["价格", "贵", "优惠", "成本"],
    "服务售后": ["售后", "客服", "投诉"], "内容生态": ["内容", "主题", "教程"], "购买决策": ["购买", "对比", "车型"],
}
SCENARIO_RULES = {
    "使用前": ["想要", "期待", "什么时候"], "购买决策期": ["购买", "对比", "选车"], "首次体验": ["第一次", "首次"],
    "日常使用": ["日常", "通勤", "每天"], "特定场景使用": ["孩子", "家人", "宠物", "上车"],
    "问题发生": ["失败", "卡顿", "无法", "问题"], "售后处理": ["售后", "客服", "投诉"],
    "长期使用": ["长期", "用了很久", "老款"], "换购或弃用": ["换车", "弃用", "退订"],
}
PURPOSE_RULES = {
    "分享体验": ["体验", "记录", "分享"], "推荐种草": ["推荐", "值得", "种草"], "求助": ["求助", "怎么办", "请问"],
    "避坑": ["避坑", "注意"], "吐槽": ["吐槽", "无语"], "投诉": ["投诉", "维权"], "产品比较": ["对比", "竞品"],
    "购买咨询": ["能买吗", "购买", "选哪"], "使用教程": ["教程", "步骤", "打开"], "情绪表达": ["失望", "开心", "愤怒", "担心"],
    "身份展示": ["车主", "我们家"], "社交互动": ["大家", "评论区", "我也"], "信息求证": ["真的吗", "是否", "什么时候", "支持哪些"],
}
PAIN_RULES = {"兼容覆盖不足": ["老款", "不支持", "部分车型"], "性能稳定问题": ["卡顿", "失败", "崩溃"], "可发现性差": ["入口太深", "找了半天", "教程不清楚"], "隐私透明不足": ["隐私", "保存时间", "删除方式"]}
NEED_RULES = {"扩大车型覆盖": ["老款", "支持", "推送"], "提升稳定性": ["修复", "卡顿", "失败"], "明确操作指引": ["教程", "步骤", "入口"], "强化隐私说明": ["隐私", "保存", "删除"], "增强个性化": ["自定义", "上传", "照片"]}


def _tokens(text: str) -> list[str]:
    return [token.lower().strip() for token in jieba.lcut(str(text)) if token.strip() and token not in STOPWORDS and token.lower().strip() != "r" and (len(token) > 1 or re.search(r"[A-Za-z0-9]", token))]


def _score_sentiment(tokens: list[str], positive_terms: set[str] | None = None, negative_terms: set[str] | None = None) -> tuple[str, float, float]:
    positive_terms = positive_terms or POSITIVE
    negative_terms = negative_terms or NEGATIVE
    positive = negative = 0.0
    for index, token in enumerate(tokens):
        if token not in positive_terms and token not in negative_terms:
            continue
        weight = 1.0
        window = tokens[max(0, index - 2):index]
        if any(value in INTENSIFIERS for value in window): weight *= 1.5
        negated = any(value in NEGATORS for value in window)
        if (token in positive_terms) ^ negated: positive += weight
        else: negative += weight
    if positive and negative: label = "混合"
    elif positive: label = "正向"
    elif negative: label = "负向"
    else: label = "中性"
    score = (positive - negative) / max(1.0, positive + negative)
    confidence = 0.25 if not (positive or negative) else min(0.95, 0.45 + 0.12 * (positive + negative))
    return label, round(score, 4), round(confidence, 4)


def _multi_labels(text: str, rules: dict[str, list[str]], default: str = "未识别") -> list[str]:
    lower = text.lower()
    labels = [label for label, terms in rules.items() if any(term.lower() in lower for term in terms)]
    return labels or [default]


def _taxonomy_rules(config: dict[str, Any], name: str, fallback: dict[str, list[str]]) -> dict[str, list[str]]:
    """Resolve a project taxonomy while keeping the packaged defaults usable."""
    configured = config.get("analysis", {}).get("taxonomy", {}).get(name)
    if not configured:
        return fallback
    if not isinstance(configured, dict):
        raise ValueError(f"analysis.taxonomy.{name} must be a label-to-keywords mapping")
    rules: dict[str, list[str]] = {}
    for label, terms in configured.items():
        if isinstance(terms, str):
            terms = [terms]
        if not isinstance(terms, list) or not all(isinstance(term, str) for term in terms):
            raise ValueError(f"analysis.taxonomy.{name}.{label} must be a string or list of strings")
        cleaned = [term.strip() for term in terms if term.strip()]
        if cleaned:
            rules[str(label)] = cleaned
    if not rules:
        raise ValueError(f"analysis.taxonomy.{name} contains no usable labels")
    return rules


def _vectorize(frame: pd.DataFrame, tfidf: bool = True):
    cls = TfidfVectorizer if tfidf else CountVectorizer
    vectorizer = cls(token_pattern=WORD_PATTERN, min_df=1 if len(frame) < 30 else 2, max_df=1.0 if len(frame) < 10 else 0.95, ngram_range=(1, 2), max_features=8000)
    matrix = vectorizer.fit_transform(frame["_token_text"].replace("", "空文本"))
    return vectorizer, matrix


def _choose_k(matrix, n: int, requested: int) -> tuple[int, float | None]:
    if n < 5: return 1, None
    if requested: return min(max(2, requested), n - 1), None
    upper = min(8, max(2, int(math.sqrt(n))), n - 1)
    best = (2, -1.0)
    for k in range(2, upper + 1):
        labels = MiniBatchKMeans(n_clusters=k, random_state=42, n_init=5, batch_size=min(512, n)).fit_predict(matrix)
        if len(set(labels)) < 2: continue
        score = silhouette_score(matrix, labels, metric="cosine", sample_size=min(n, 1000), random_state=42)
        if score > best[1]: best = (k, float(score))
    return best


def _topic_table(frame: pd.DataFrame, matrix, vectorizer, labels: np.ndarray, confidence: np.ndarray, engine: str) -> list[dict[str, Any]]:
    features = np.asarray(vectorizer.get_feature_names_out())
    topics = []
    for topic_id in sorted(set(int(value) for value in labels)):
        mask = labels == topic_id
        subset = frame.loc[mask]
        weights = np.asarray(matrix[mask].mean(axis=0)).ravel()
        terms = [str(value) for value in features[weights.argsort()[::-1][:8]] if value != "空文本"]
        label = " / ".join(terms[:3]) or f"主题{topic_id}"
        representative = subset.assign(_confidence=confidence[mask]).sort_values("_confidence", ascending=False).head(5)
        topics.append({
            "id": topic_id, "label": label, "engine": engine, "count": int(mask.sum()), "share": round(float(mask.mean()), 4),
            "negative_share": round(float((subset["sentiment"] == "负向").mean()), 4), "keywords": terms,
            "representatives": [{"record_id": str(row.record_id), "excerpt": str(row.clean_text)[:280]} for row in representative.itertuples()],
        })
    return sorted(topics, key=lambda value: value["count"], reverse=True)


def _fast_topics(frame: pd.DataFrame, requested: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    vectorizer, matrix = _vectorize(frame, True)
    k, silhouette = _choose_k(matrix, len(frame), requested)
    if k == 1:
        labels = np.zeros(len(frame), dtype=int); confidence = np.full(len(frame), 0.5)
    else:
        model = MiniBatchKMeans(n_clusters=k, random_state=42, n_init=10, batch_size=min(512, len(frame)))
        labels = model.fit_predict(matrix)
        distances = model.transform(matrix)
        confidence = 1 - distances[np.arange(len(labels)), labels] / np.maximum(distances.max(axis=1), 1e-9)
    topics = _topic_table(frame, matrix, vectorizer, labels, confidence, "tfidf-kmeans")
    names = {item["id"]: item["label"] for item in topics}
    result = frame.copy(); result["topic_id"] = labels; result["topic_name"] = [names[int(value)] for value in labels]; result["topic_confidence"] = np.clip(confidence, 0, 1).round(4)
    return result, {"engine": "tfidf-kmeans", "topic_count": k, "silhouette": None if silhouette is None else round(silhouette, 4), "topics": topics}


def _lda_topics(frame: pd.DataFrame, requested: int) -> dict[str, Any]:
    vectorizer, matrix = _vectorize(frame, False)
    k = min(max(2, requested or max(2, min(6, int(math.sqrt(len(frame)))))), max(2, len(frame) - 1))
    model = LatentDirichletAllocation(n_components=k, random_state=42, learning_method="batch", max_iter=20)
    distribution = model.fit_transform(matrix)
    features = np.asarray(vectorizer.get_feature_names_out())
    topics = []
    for topic_id, component in enumerate(model.components_):
        terms = [str(value) for value in features[component.argsort()[::-1][:10]]]
        rows = np.argsort(distribution[:, topic_id])[::-1][:5]
        topics.append({"id": topic_id, "label": " / ".join(terms[:3]), "keywords": terms, "representatives": [{"record_id": str(frame.iloc[row]["record_id"]), "excerpt": str(frame.iloc[row]["clean_text"])[:280]} for row in rows]})
    return {"engine": "sklearn-lda", "topic_count": k, "perplexity": round(float(model.perplexity(matrix)), 4), "topics": topics}


def _semantic_topics(frame: pd.DataFrame, requested: int, embedding_model: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = ["sentence_transformers", "bertopic", "umap", "hdbscan"]
    missing = [name for name in required if not importlib.util.find_spec(name)]
    if missing:
        raise RuntimeError(f"Semantic mode unavailable; install authorized advanced dependencies: {', '.join(missing)}")
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(embedding_model)
    embeddings = model.encode(frame["clean_text"].tolist(), show_progress_bar=False, normalize_embeddings=True)
    topic_model = BERTopic(embedding_model=model, nr_topics=requested or "auto", min_topic_size=max(3, min(10, len(frame) // 20 or 3)), calculate_probabilities=False, verbose=False)
    labels, probabilities = topic_model.fit_transform(frame["clean_text"].tolist(), embeddings)
    info = topic_model.get_topic_info()
    topics = []
    for row in info.itertuples(index=False):
        topic_id = int(row.Topic); keywords = [term for term, _ in (topic_model.get_topic(topic_id) or [])[:10]]
        mask = np.asarray(labels) == topic_id; subset = frame.loc[mask].head(5)
        topics.append({"id": topic_id, "label": " / ".join(keywords[:3]) or "离群/待复核", "count": int(mask.sum()), "share": round(float(mask.mean()), 4), "keywords": keywords, "representatives": [{"record_id": str(value.record_id), "excerpt": str(value.clean_text)[:280]} for value in subset.itertuples()]})
    names = {item["id"]: item["label"] for item in topics}
    result = frame.copy(); result["topic_id"] = labels; result["topic_name"] = [names[int(value)] for value in labels]; result["topic_confidence"] = probabilities if probabilities is not None and np.ndim(probabilities) == 1 else 0.5
    return result, {"engine": "bertopic", "embedding_model": embedding_model, "topic_count": len([item for item in topics if item["id"] != -1]), "outlier_share": round(float((np.asarray(labels) == -1).mean()), 4), "topics": topics}


def _distribution(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    counts = Counter(label for labels in frame[column] for label in labels)
    total = max(1, len(frame))
    return [{"label": label, "count": int(count), "record_share": round(count / total, 4)} for label, count in counts.most_common()]


def _evidence(frame: pd.DataFrame, mask: pd.Series | np.ndarray | None = None, limit: int = 5) -> list[dict[str, Any]]:
    subset = frame if mask is None else frame.loc[mask]
    subset = subset.assign(_engagement=subset[["like_count", "favorite_count", "comment_count", "share_count"]].sum(axis=1)).sort_values("_engagement", ascending=False).head(limit)
    return [{"record_id": str(row["record_id"]), "record_type": str(row["record_type"]), "excerpt": str(row["clean_text"])[:300], "engagement": int(row["_engagement"])} for _, row in subset.iterrows()]


def _trend(frame: pd.DataFrame) -> dict[str, Any]:
    valid = frame.dropna(subset=["publish_time"]).copy()
    if valid.empty: return {"available": False, "reason": "No valid time values"}
    valid["date"] = pd.to_datetime(valid["publish_time"], utc=True).dt.floor("D")
    daily = valid.groupby("date").agg(volume=("record_id", "size"), negative_share=("sentiment", lambda values: float((values == "负向").mean()))).reset_index()
    median = float(daily["volume"].median()); mad = float(np.median(np.abs(daily["volume"] - median))); scale = 1.4826 * mad if mad else max(1.0, float(daily["volume"].std(ddof=0)))
    daily["burst_score"] = ((daily["volume"] - median) / scale).round(3)
    points = [{"date": row.date.date().isoformat(), "volume": int(row.volume), "negative_share": round(float(row.negative_share), 4), "burst_score": float(row.burst_score)} for row in daily.itertuples()]
    return {"available": True, "valid_time_rows": int(len(valid)), "valid_time_share": round(len(valid) / len(frame), 4), "start": points[0]["date"], "end": points[-1]["date"], "points": points, "bursts": [item["date"] for item in points if item["burst_score"] >= 2.5]}


def _load_cleaned(paths: ProjectPaths) -> pd.DataFrame:
    parquet = paths.processed / "cleaned_data.parquet"
    csv = paths.processed / "cleaned_data.csv"
    if parquet.exists(): return pd.read_parquet(parquet)
    if csv.exists(): return pd.read_csv(csv)
    raise FileNotFoundError("cleaned_data not found; run clean first")


def run_analysis(
    config: dict[str, Any],
    paths: ProjectPaths,
    selected_mode: str | None = None,
    selected_profile: str | None = None,
) -> dict[str, Any]:
    frame = _load_cleaned(paths)
    if frame.empty: raise ValueError("No cleaned records available")
    mode = selected_mode or config["analysis"].get("mode")
    if mode not in {"fast", "semantic", "auto"}: raise ValueError("Explicit fast, semantic, or auto mode is required")
    profile = selected_profile or config["analysis"].get("profile")
    allowed_profiles = {"rapid", "discovery", "aspect", "experience", "comparative", "network", "predictive", "mixed"}
    if profile not in allowed_profiles:
        raise ValueError("Explicit rapid, discovery, aspect, experience, comparative, network, predictive, or mixed profile is required")
    profiles = list(config["analysis"].get("profiles", [])) if profile == "mixed" else [profile]
    invalid_profiles = sorted(set(profiles) - allowed_profiles)
    if invalid_profiles or not profiles:
        raise ValueError(f"analysis.profiles contains invalid or empty values: {invalid_profiles}")
    semantic_ready = all(importlib.util.find_spec(name) for name in ["sentence_transformers", "bertopic", "umap", "hdbscan"])
    actual_mode = "semantic" if mode == "semantic" or (mode == "auto" and semantic_ready and len(frame) >= 200) else "fast"
    if mode == "semantic" and not semantic_ready:
        raise RuntimeError("Semantic mode was selected but advanced dependencies are unavailable. No silent fallback was performed.")
    frame["_tokens"] = frame["clean_text"].fillna("").astype(str).map(_tokens)
    frame["_token_text"] = frame["_tokens"].map(" ".join)
    sentiment_config = config["analysis"].get("sentiment", {})
    positive_terms = POSITIVE | {str(term).strip().lower() for term in sentiment_config.get("positive_terms", []) if str(term).strip()}
    negative_terms = NEGATIVE | {str(term).strip().lower() for term in sentiment_config.get("negative_terms", []) if str(term).strip()}
    sentiment = frame["_tokens"].map(lambda tokens: _score_sentiment(tokens, positive_terms, negative_terms))
    frame[["sentiment", "sentiment_score", "sentiment_confidence"]] = pd.DataFrame(sentiment.tolist(), index=frame.index)
    emotion_rules = _taxonomy_rules(config, "emotions", EMOTION_RULES)
    feature_rules = _taxonomy_rules(config, "features", FEATURE_RULES)
    scenario_rules = _taxonomy_rules(config, "scenarios", SCENARIO_RULES)
    purpose_rules = _taxonomy_rules(config, "purposes", PURPOSE_RULES)
    pain_rules = _taxonomy_rules(config, "pain_points", PAIN_RULES)
    need_rules = _taxonomy_rules(config, "needs", NEED_RULES)
    frame["emotion_labels"] = frame["clean_text"].map(lambda value: _multi_labels(value, emotion_rules, "无法判断"))
    subject = str(config["analysis"].get("subject", "")); brands = [subject, *config["analysis"].get("competitors", []), "小米", "蔚来", "比亚迪", "理想"]
    brand_rules = {brand: [brand] for brand in brands if brand}
    frame["brand_labels"] = frame["clean_text"].map(lambda value: _multi_labels(value, brand_rules, "未提及品牌"))
    frame["feature_labels"] = frame["clean_text"].map(lambda value: _multi_labels(value, feature_rules))
    frame["scenario_labels"] = frame["clean_text"].map(lambda value: _multi_labels(value, scenario_rules))
    frame["stage_labels"] = frame["scenario_labels"]
    frame["purpose_labels"] = frame["clean_text"].map(lambda value: _multi_labels(value, purpose_rules))
    frame["pain_point_labels"] = frame["clean_text"].map(lambda value: _multi_labels(value, pain_rules, "未识别痛点"))
    frame["need_labels"] = frame["clean_text"].map(lambda value: _multi_labels(value, need_rules, "未识别需求"))
    frame = enrich_text_features(frame)
    requested_scope = str(config["analysis"].get("topic_scope", "posts"))
    if requested_scope not in {"posts", "all"}:
        raise ValueError("analysis.topic_scope must be posts or all")
    topic_source = frame[frame["record_type"].eq("post")].copy() if requested_scope == "posts" else frame.copy()
    scope_used = requested_scope
    if len(topic_source) < 5:
        topic_source = frame.copy()
        scope_used = "all_fallback"
    if actual_mode == "semantic":
        topic_source, topic = _semantic_topics(topic_source, int(config["analysis"].get("topic_count", 0)), config["analysis"].get("embedding_model"))
    else:
        topic_source, topic = _fast_topics(topic_source, int(config["analysis"].get("topic_count", 0)))
    topic["scope_requested"] = requested_scope
    topic["scope_used"] = scope_used
    topic["clustered_records"] = int(len(topic_source))
    assignments = topic_source.set_index("record_id")[["topic_id", "topic_name", "topic_confidence"]]
    own_ids = frame["record_id"].map(assignments["topic_id"])
    parent_ids = frame["parent_id"].map(assignments["topic_id"])
    frame["topic_id"] = own_ids.combine_first(parent_ids).fillna(-99).astype(int)
    own_names = frame["record_id"].map(assignments["topic_name"])
    parent_names = frame["parent_id"].map(assignments["topic_name"])
    frame["topic_name"] = own_names.combine_first(parent_names).fillna("未归入父帖主题")
    own_confidence = frame["record_id"].map(assignments["topic_confidence"])
    parent_confidence = frame["parent_id"].map(assignments["topic_confidence"])
    frame["topic_confidence"] = own_confidence.combine_first(parent_confidence).fillna(0.0).astype(float)
    lda = _lda_topics(topic_source, int(config["analysis"].get("topic_count", 0))) if len(topic_source) >= 5 else {"engine": "sklearn-lda", "available": False, "reason": "fewer than 5 records"}
    token_counts = Counter(token for tokens in frame["_tokens"] for token in tokens)
    keywords = [{"term": term, "count": int(count)} for term, count in token_counts.most_common(60)]
    sentiment_counts = frame["sentiment"].value_counts().reindex(["正向", "中性", "负向", "混合", "无法判断"], fill_value=0)
    sentiment_result = {"counts": {key: int(value) for key, value in sentiment_counts.items()}, "shares": {key: round(int(value) / len(frame), 4) for key, value in sentiment_counts.items()}, "low_confidence_share": round(float((frame["sentiment_confidence"] < 0.5).mean()), 4), "method": "transparent local lexicon baseline with negation and mixed-polarity path"}
    trend = _trend(frame)
    risk_rows = []
    for item in topic["topics"]:
        subset = frame[frame["topic_id"] == item["id"]]
        negative_share = float((subset["sentiment"] == "负向").mean()) if len(subset) else 0
        risk_score = min(100.0, 100 * (0.55 * negative_share + 0.25 * item.get("share", 0) + 0.20 * float((subset["sentiment_confidence"] < 0.5).mean())))
        risk_rows.append({"topic_id": item["id"], "topic": item["label"], "count": len(subset), "negative_share": round(negative_share, 4), "review_priority_score": round(risk_score, 2), "evidence": _evidence(subset, limit=3)})
    risk_rows.sort(key=lambda value: value["review_priority_score"], reverse=True)
    aspect_rows = []
    for item in _distribution(frame, "feature_labels"):
        label = item["label"]
        subset = frame[frame["feature_labels"].map(lambda values: label in values)]
        aspect_rows.append({
            **item,
            "positive_share": round(float((subset["sentiment"] == "正向").mean()), 4),
            "negative_share": round(float((subset["sentiment"] == "负向").mean()), 4),
            "top_emotions": [name for name, _ in Counter(value for values in subset["emotion_labels"] for value in values).most_common(3)],
            "evidence_ids": [str(value) for value in subset["record_id"].head(5)],
        })
    text_diagnostics = run_text_diagnostics(frame)
    comparative = run_cohort_analysis(frame, config) if "comparative" in profiles else {**module_result("comparative_analysis", "2.0"), "status": "skipped", "metrics": {"reason": "profile_not_selected"}}
    experience = run_experience_analysis(frame, config) if "experience" in profiles else {**module_result("experience_research", "2.0"), "status": "skipped", "metrics": {"reason": "profile_not_selected"}}
    network = run_network_analysis(frame, config) if "network" in profiles else {**module_result("cooccurrence_network", "2.0"), "status": "skipped", "metrics": {"reason": "profile_not_selected"}}
    predictive = run_predictive_analysis(frame, config) if "predictive" in profiles else {**module_result("predictive_modeling", "2.0"), "status": "skipped", "metrics": {"reason": "profile_not_selected"}}
    descriptive = module_result("descriptive_statistics"); descriptive["metrics"] = {"records": len(frame), "posts": int((frame["record_type"] == "post").sum()), "comments": int(frame["record_type"].isin(["comment", "reply"]).sum()), "engagement_total": int(frame[["like_count", "favorite_count", "comment_count", "share_count"]].sum().sum()), "time_valid": int(pd.to_datetime(frame["publish_time"], errors="coerce").notna().sum())}; descriptive["tables"]["record_type"] = frame["record_type"].value_counts().rename_axis("record_type").reset_index(name="count").to_dict("records")
    descriptive["status"] = "complete"
    payloads = {
        "descriptive_statistics.json": descriptive,
        "keyword_analysis.json": {**module_result("keyword_analysis"), "tables": {"keywords": keywords}, "evidence": _evidence(frame)},
        "topic_analysis.json": {**module_result("topic_analysis", config={"mode_requested": mode, "mode_used": actual_mode}), "metrics": {"mode_requested": mode, "mode_used": actual_mode}, "tables": {"selected_topics": topic, "lda_reference": lda}, "warnings": ["Topics are exploratory clusters and require representative-text review."]},
        "sentiment_analysis.json": {**module_result("sentiment_analysis"), "metrics": sentiment_result, "tables": {"by_topic": frame.groupby("topic_name")["sentiment"].value_counts().unstack(fill_value=0).reset_index().to_dict("records")}, "limitations": ["The local sentiment scorer is a triage baseline, not a validated domain model."]},
        "emotion_analysis.json": {**module_result("emotion_analysis"), "tables": {"emotions": _distribution(frame, "emotion_labels")}, "config": {"framework": "three-source taxonomy: source graphic labels 35, 34 labels visibly enumerated", "visible_label_count": 34}},
        "brand_analysis.json": {**module_result("brand_analysis"), "tables": {"brands": _distribution(frame, "brand_labels")}},
        "feature_analysis.json": {**module_result("feature_analysis"), "tables": {"features": _distribution(frame, "feature_labels"), "aspect_matrix": aspect_rows}, "status": "complete"},
        "scenario_analysis.json": {**module_result("scenario_analysis"), "tables": {"scenarios": _distribution(frame, "scenario_labels"), "purposes": _distribution(frame, "purpose_labels")}},
        "trend_analysis.json": {**module_result("trend_analysis"), "metrics": trend},
        "risk_analysis.json": {**module_result("risk_analysis"), "tables": {"risks": risk_rows}, "limitations": ["Review-priority score is not a probability of real-world harm."]},
        "text_diagnostics.json": text_diagnostics,
        "comparative_analysis.json": comparative,
        "experience_analysis.json": experience,
        "network_analysis.json": network,
        "predictive_analysis.json": predictive,
    }
    for name, payload in payloads.items(): write_json(payload, paths.analysis / name)
    write_json({"chart": "topic_share", "data": [{"label": item["label"], "count": item["count"], "share": item.get("share", 0)} for item in topic["topics"]]}, paths.charts / "topic_share.json")
    write_json({"chart": "sentiment_distribution", "data": [{"label": key, "count": int(value)} for key, value in sentiment_counts.items()]}, paths.charts / "sentiment_distribution.json")
    write_json({"chart": "trend", "data": trend.get("points", []) if trend.get("available") else [], "available": trend.get("available")}, paths.charts / "trend.json")
    write_json({"chart": "risk_priority", "data": [{"topic": item["topic"], "score": item["review_priority_score"]} for item in risk_rows]}, paths.charts / "risk_priority.json")
    write_json({"chart": "opportunity_matrix", "data": experience.get("tables", {}).get("opportunities", [])}, paths.charts / "opportunity_matrix.json")
    write_json({"chart": "cooccurrence_network", "data": network.get("tables", {})}, paths.charts / "cooccurrence_network.json")
    write_json({"chart": "model_importance", "data": predictive.get("tables", {}).get("feature_importance", [])}, paths.charts / "model_importance.json")
    export = frame.copy()
    for column in ["_tokens", "emotion_labels", "brand_labels", "feature_labels", "scenario_labels", "stage_labels", "purpose_labels", "pain_point_labels", "need_labels"]:
        export[column] = export[column].map(lambda value: "|".join(value) if isinstance(value, list) else value)
    export.to_csv(paths.analysis / "enriched.csv", index=False, encoding="utf-8-sig")
    summary = {"schema_version": "2.0", "generated_at": datetime.now(timezone.utc).isoformat(), "records": len(frame), "mode_requested": mode, "mode_used": actual_mode, "profile_requested": profile, "profiles_used": profiles, "semantic_ready": semantic_ready, "sentiment": sentiment_result, "keywords": keywords, "topics": topic["topics"], "lda_reference": lda, "emotions": _distribution(frame, "emotion_labels"), "brands": _distribution(frame, "brand_labels"), "features": _distribution(frame, "feature_labels"), "aspect_matrix": aspect_rows, "scenarios": _distribution(frame, "scenario_labels"), "purposes": _distribution(frame, "purpose_labels"), "trends": trend, "risks": risk_rows, "text_diagnostics": text_diagnostics, "comparative": comparative, "experience": experience, "network": network, "predictive": predictive, "evidence": _evidence(frame, limit=12), "provenance": {"analysis_version": "2.0.0", "sentiment": sentiment_result["method"], "topic_engine": topic["engine"], "external_llm": config.get("llm", {}).get("provider", "none")}}
    write_json(summary, paths.analysis / "analysis.json")
    return summary

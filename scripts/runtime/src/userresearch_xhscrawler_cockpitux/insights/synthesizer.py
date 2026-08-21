from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from ..storage import ProjectPaths, read_json, write_json
from .validator import validate_insights


def _split(value: Any) -> list[str]:
    return [item for item in str(value or "").split("|") if item]


def _evidence(frame: pd.DataFrame, column: str, label: str, limit: int = 5) -> list[dict[str, Any]]:
    subset = frame[frame[column].fillna("").astype(str).str.split("|").map(lambda values: label in values)].copy()
    subset["_engagement"] = subset[["like_count", "favorite_count", "comment_count", "share_count"]].sum(axis=1)
    subset = subset.sort_values("_engagement", ascending=False).head(limit)
    return [{"record_id": str(row["record_id"]), "record_type": str(row["record_type"]), "source_keyword": str(row.get("source_keyword", "")), "publish_time": str(row.get("publish_time", "")), "excerpt": str(row["clean_text"])[:320], "engagement": int(row["_engagement"])} for _, row in subset.iterrows()]


def _top_labels(frame: pd.DataFrame, column: str, excluded: set[str] | None = None) -> list[tuple[str, int]]:
    excluded = excluded or set()
    counts = Counter(label for value in frame[column] for label in _split(value) if label not in excluded)
    return counts.most_common(5)


def synthesize_insights(config: dict[str, Any], paths: ProjectPaths) -> dict[str, Any]:
    frame = pd.read_csv(paths.analysis / "enriched.csv")
    analysis = read_json(paths.analysis / "analysis.json", {})
    experience = read_json(paths.analysis / "experience_analysis.json", {})
    total = len(frame)
    insights: list[dict[str, Any]] = []
    for label, count in _top_labels(frame, "pain_point_labels", {"未识别痛点"})[:3]:
        evidence = _evidence(frame, "pain_point_labels", label)
        insights.append({
            "title": f"痛点：{label}", "kind": "pain_point",
            "data_fact": {"count": count, "denominator": total, "rate": round(count / max(1, total), 4), "source": "deterministic multi-label coding"},
            "observation": f"{total} 条有效记录中有 {count} 条命中“{label}”规则。",
            "interpretation": ["该信号说明该问题值得进入定性复核；它不证明总体人群发生率或因果关系。"],
            "evidence": evidence, "applicability": "本次关键词、时间与可见内容范围内的有效样本",
            "confidence": "中" if len(evidence) >= 3 else "低", "business_impact": "可能影响体验完成率、信任或推荐意愿",
            "recommendation": f"围绕“{label}”抽样人工复核，并用产品日志或访谈验证优先级。",
        })
    for label, count in _top_labels(frame, "need_labels", {"未识别需求"})[:3]:
        evidence = _evidence(frame, "need_labels", label)
        insights.append({
            "title": f"未满足需求：{label}", "kind": "need",
            "data_fact": {"count": count, "denominator": total, "rate": round(count / max(1, total), 4), "source": "deterministic need coding"},
            "observation": f"“{label}”在 {count} 条记录中出现。", "interpretation": ["这是文本表达线索，需要结合场景和原文确认具体方案边界。"],
            "evidence": evidence, "applicability": "本次有效样本", "confidence": "中" if len(evidence) >= 3 else "低",
            "business_impact": "可作为需求机会池输入", "recommendation": f"将“{label}”转化为可测试的需求假设并安排用户验证。",
        })
    for label, count in _top_labels(frame, "feature_labels", {"未识别"})[:2]:
        evidence = _evidence(frame, "feature_labels", label)
        subset = frame[frame["feature_labels"].fillna("").str.contains(label, regex=False)]
        negative = int((subset["sentiment"] == "负向").sum())
        insights.append({
            "title": f"体验焦点：{label}", "kind": "feature",
            "data_fact": {"count": count, "denominator": total, "rate": round(count / max(1, total), 4), "negative_count": negative, "source": "feature and sentiment baseline"},
            "observation": f"“{label}”相关记录 {count} 条，其中本地情感基线标记负向 {negative} 条。",
            "interpretation": ["讨论量代表样本内关注度，不等同于满意度或市场渗透。"], "evidence": evidence,
            "applicability": "本次有效样本", "confidence": "中", "business_impact": "影响体验议题排序",
            "recommendation": "将正负向样本分层复核，提炼具体触发条件与完成任务。",
        })
    existing_titles = {item["title"] for item in insights}
    for theme in experience.get("tables", {}).get("themes", [])[:4]:
        title = f"体验主题：{theme['title']}"
        if title in existing_titles:
            continue
        evidence = theme.get("evidence", [])
        count = int(theme.get("supporting_signals", 0))
        insights.append({
            "title": title,
            "kind": "experience_theme",
            "data_fact": {"count": count, "denominator": total, "rate": round(count / max(1, total), 4), "source": "rule-coded experience synthesis"},
            "observation": theme.get("observation", ""),
            "interpretation": [theme.get("insight_statement", ""), "该主题描述样本内文本信号，需要访谈、日志或可用性测试验证机制。"],
            "evidence": evidence,
            "applicability": "本次关键词、排序、时间与可见内容范围内的有效记录",
            "confidence": {"强": "中", "中": "中", "弱": "低"}.get(theme.get("signal_strength"), "低"),
            "business_impact": f"{theme.get('severity', '未知')}严重性体验候选",
            "recommendation": theme.get("how_might_we", "继续验证该体验主题。"),
            "how_might_we": theme.get("how_might_we", ""),
            "opportunity_type": theme.get("opportunity_type", "战略问题"),
            "counter_signal": "检查同主题下的正向或未受影响样本，避免只保留负向高互动记录。",
        })
    validated = validate_insights(insights, total, int(config["analysis"].get("evidence_minimum", 3)))
    payload = {
        "schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(), "total_records": total,
        "method": "two-step deterministic extraction then synthesis from counts, labels, sentiment baseline, and row-linked excerpts",
        "validation": validated["summary"], "insights": validated["insights"],
        "extraction": {"dimensions": ["直接引用", "观察行为候选", "痛点", "未满足需求", "情绪信号", "矛盾"], "rule": "extract before interpret; concrete behaviors and contradictions require human confirmation"},
        "journey": {"structure": ["用户场景", "用户目标", "用户行为", "触发因素", "使用体验", "情绪反应", "问题与阻碍", "未满足需求", "用户期待", "产品机会"], "note": "Journey fields are synthesized only where deterministic labels and excerpts exist; missing stages remain unknown."},
        "limitations": ["Rules are exploratory coding aids, not a validated domain taxonomy.", "Search samples do not represent the full platform population.", "No causal claim is made from co-occurrence."],
        "analysis_mode": analysis.get("mode_used"),
        "analysis_profiles": analysis.get("profiles_used", []),
    }
    write_json(payload, paths.analysis / "insight_summary.json")
    evidence_rows = []
    for insight in payload["insights"]:
        for item in insight["evidence"]:
            evidence_rows.append({"insight_title": insight["title"], "validation_status": insight["validation"]["status"], **item})
    pd.DataFrame(evidence_rows).to_excel(paths.evidence / "evidence_index.xlsx", index=False)
    return payload

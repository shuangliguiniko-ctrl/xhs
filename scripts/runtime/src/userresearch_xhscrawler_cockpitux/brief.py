from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SECTIONS = ["project", "source", "ai_labels", "insights", "focus_rules", "prompts", "output"]


def _auto(section: str, config: dict[str, Any]) -> tuple[dict[str, Any], str]:
    subject = config.get("analysis", {}).get("subject") or "研究对象"
    crawler = config.get("crawler", {})
    values = {
        "project": {"analysis_goal": f"识别{subject}的主题、体验、情绪、风险与机会", "decision_support": "产品、用户研究与品牌决策"},
        "source": {"platforms": ["小红书"], "collection_method": crawler.get("adapter", "unknown"), "query_scope": crawler.get("keywords", []), "date_scope": "unknown", "known_biases": "搜索排序、访问权限、已删除内容和可见评论范围可能造成覆盖偏差"},
        "ai_labels": {"directions": ["主题", "功能", "场景", "情感", "情绪", "目的", "风险", "需求"], "uncertain_policy": "低置信度进入人工复核"},
        "insights": {"directions": ["产品体验", "购买决策", "痛点", "未满足需求", "风险", "机会"], "questions": ["用户讨论什么", "为什么满意或不满", "哪些场景和功能应优先改进"]},
        "focus_rules": {"deduplication": "稳定ID、精确文本与SimHash", "small_denominator": 30, "evidence_minimum": config.get("analysis", {}).get("evidence_minimum", 3)},
        "prompts": {"aspect_coding": "仅依据文本证据进行多标签编码", "topic_naming": "使用具体领域短语并避免重复搜索词", "risk_review": "输出证据、严重性、紧迫性与不确定性", "executive_summary": "区分观察、解释、建议和局限"},
        "output": {"audience": config.get("report", {}).get("audience", "混合受众"), "sections": config.get("report", {}).get("sections", []), "deliverables": ["analysis JSON", "enriched CSV", "evidence index", "self-contained HTML", "manifest"]},
    }
    return values[section], "Resolved from the named subject, configured adapter, local modules, evidence rules, and report audience."


def resolve_brief(config: dict[str, Any]) -> dict[str, Any]:
    requested = config.get("brief", {})
    auto_fields = list(requested.get("auto_fields", []))
    resolved: dict[str, Any] = {}
    for section in SECTIONS:
        custom = requested.get(section) or {}
        if custom:
            resolved[section] = {"origin": "user", "requested": custom, "resolved": custom}
        elif section in auto_fields:
            value, rationale = _auto(section, config)
            resolved[section] = {"origin": "auto", "requested": "Auto", "resolved": value, "rationale": rationale}
        else:
            raise ValueError(f"brief.{section} must be populated or explicitly listed in brief.auto_fields")
    if config.get("analysis", {}).get("mode") not in {"fast", "semantic", "auto"}:
        raise ValueError("analysis.mode requires explicit fast, semantic, or auto selection")
    if config.get("analysis", {}).get("profile") not in {"rapid", "discovery", "aspect", "experience", "comparative", "network", "predictive", "mixed"}:
        raise ValueError("analysis.profile requires an explicit research profile")
    if not requested.get("confirmed"):
        raise ValueError("brief.confirmed must be true before collection or analysis")
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confirmed": True,
        "auto_fields": auto_fields,
        "requested": {key: requested.get(key) for key in [*SECTIONS, "auto_fields"]},
        "resolved": resolved,
        "analysis_mode": config["analysis"]["mode"],
        "analysis_profile": config["analysis"]["profile"],
        "external_llm": {key: config.get("llm", {}).get(key) for key in ("provider", "authorized", "allowed_text", "max_rows")},
    }

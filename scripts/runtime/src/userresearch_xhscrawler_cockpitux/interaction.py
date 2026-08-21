from __future__ import annotations

from typing import Any


TOPIC_ENGINES = {
    "fast": {
        "label": "快速本地主题",
        "description": "使用 TF-IDF/K-Means 与 LDA，确定性强、CPU 友好，适合快速基线与体验研究。",
        "requirements": "无需外部模型下载；主题仍需人工命名与复核。",
    },
    "semantic": {
        "label": "语义主题",
        "description": "使用多语嵌入与 BERTopic/HDBSCAN，更适合识别不同说法表达的同一含义。",
        "requirements": "需要可选依赖和模型下载授权；依赖缺失时停止，不静默降级。",
    },
    "auto": {
        "label": "显式自动选择",
        "description": "根据语料规模与本地依赖选择主题引擎，并记录 requested 与 actual。",
        "requirements": "必须明确选择 Auto；不能把未回答视为授权。",
    },
}


RESEARCH_PROFILES = {
    "rapid": {"label": "舆情概览", "question": "现在讨论什么、哪些内容应先复核？", "outputs": "量级、关键词、基线情感/情绪、风险分诊"},
    "discovery": {"label": "主题探索", "question": "没有预设分类时，语料中存在哪些主题？", "outputs": "探索主题、代表记录、人工命名队列"},
    "aspect": {"label": "产品方面", "question": "用户如何评价已知功能或体验方面？", "outputs": "方面 × 情感/情绪/场景矩阵"},
    "experience": {"label": "体验机会", "question": "用户想完成什么、体验在哪里中断？", "outputs": "行为、痛点、需求、旅程、矛盾、HMW 与机会"},
    "comparative": {"label": "群组比较", "question": "关键词、来源、记录类型或时间群组有何差异？", "outputs": "计数、比例、效应量、不确定性与小组警告"},
    "network": {"label": "关系网络", "question": "功能、痛点与需求如何在同一记录中共现？", "outputs": "节点、边、簇与共现网络"},
    "predictive": {"label": "预测建模", "question": "预先声明的输入能否在样本外预测目标？", "outputs": "泄漏审计、基线、留出指标与特征重要性"},
    "mixed": {"label": "组合研究", "question": "哪些明确模块组合才能回答当前决策？", "outputs": "共享稳定 ID 的多模块结果与跳过原因"},
}


COLLECTION_ADAPTERS = {
    "browseract": {"label": "BrowserAct 精确挖掘", "description": "由 AI 按 BrowserAct Core 规范操作已授权浏览器，持久化复合 JSON/JSONL 后导入。"},
    "mediacrawler": {"label": "MediaCrawler 批量挖掘", "description": "按确认关键词批量采集笔记与评论；需要许可证复核、有效登录和平台可访问性。"},
    "hybrid": {"label": "混合挖掘", "description": "合并 BrowserAct 页面核验样本与 MediaCrawler 批量结果，并按稳定内容 ID 去重。"},
    "import": {"label": "上传本地数据", "description": "导入 CSV/XLSX/JSONL/JSON/Parquet，适合已有数据或实时入口不可用的研究。"},
    "mock": {"label": "演示与测试", "description": "只验证安装、流程和报告，不形成真实研究证据。"},
}


WORKFLOW_MODES = {
    "ai": {"label": "AI 模式", "description": "在 AI 会话中完成五步流程、判断与确认。"},
    "ui": {"label": "UI 模式", "description": "环境检查后启动 Streamlit，由页面完成第三至第五步。"},
}


PROFILE_ORDER = ["rapid", "discovery", "aspect", "experience", "comparative", "network", "predictive"]


def selected_profiles(config: dict[str, Any]) -> list[str]:
    analysis = config.get("analysis", {})
    profile = analysis.get("profile")
    if profile == "mixed":
        return [item for item in analysis.get("profiles", []) if item in PROFILE_ORDER]
    return [profile] if profile in RESEARCH_PROFILES else []


def selection_catalog() -> dict[str, Any]:
    return {
        "workflow_modes": WORKFLOW_MODES,
        "topic_engines": TOPIC_ENGINES,
        "research_profiles": RESEARCH_PROFILES,
        "collection_adapters": COLLECTION_ADAPTERS,
    }


def config_summary(config: dict[str, Any]) -> dict[str, Any]:
    crawler = config.get("crawler", {})
    analysis = config.get("analysis", {})
    return {
        "workflow_mode": config.get("workflow", {}).get("mode"),
        "execution_mode": config.get("project", {}).get("execution_mode", "unknown"),
        "brief_confirmed": bool(config.get("brief", {}).get("confirmed")),
        "crawl_plan_confirmed": bool(crawler.get("plan_confirmed")),
        "adapter": crawler.get("adapter"),
        "collection_mode": crawler.get("mode"),
        "keywords": [str(item) for item in crawler.get("keywords", [])],
        "excluded_keywords": [str(item) for item in crawler.get("excluded_keywords", [])],
        "include_comments": bool(crawler.get("include_comments")),
        "include_sub_comments": bool(crawler.get("include_sub_comments")),
        "max_notes": crawler.get("max_notes"),
        "max_notes_per_keyword": crawler.get("max_notes_per_keyword"),
        "max_comments_per_note": crawler.get("max_comments_per_note"),
        "mode_requested": analysis.get("mode"),
        "profile_requested": analysis.get("profile"),
        "profiles_requested": selected_profiles(config),
        "predictive_enabled": bool(analysis.get("predictive", {}).get("enabled")),
        "external_llm": config.get("llm", {}).get("provider", "none"),
    }

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

import streamlit as st
import yaml

PACKAGE = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from userresearch_xhscrawler_cockpitux.brief import resolve_brief
from userresearch_xhscrawler_cockpitux.config import ASSET_ROOT, load_config
from userresearch_xhscrawler_cockpitux.diagnostics import run_diagnostics
from userresearch_xhscrawler_cockpitux.interaction import COLLECTION_ADAPTERS, RESEARCH_PROFILES, TOPIC_ENGINES
from userresearch_xhscrawler_cockpitux.orchestrator import run_all
from userresearch_xhscrawler_cockpitux.planner import build_crawl_plan


st.set_page_config(page_title="New XHS Research", page_icon="◉", layout="wide")
st.markdown(
    """<style>
    .stApp{background:#f7f8fb}.block-container{max-width:1320px;padding-top:2rem}
    .hero{padding:18px 0 30px;border-bottom:1px solid #e4e7ec;margin-bottom:24px}.hero h1{font-size:3rem;letter-spacing:0;line-height:1.05;margin:.2em 0}
    .mode-note{padding:14px 16px;border-left:4px solid #5b4bff;background:#fff;border-radius:6px;margin:8px 0 18px}
    .plan-box{padding:18px;border:1px solid #d0d5dd;background:#fff;border-radius:8px}
    </style>""",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero"><div>NEW XHS RESEARCH · UI MODE</div><h1>从目标到证据化产品机会</h1><p>UI 模式已选定。页面依次完成环境、简报、舆情挖掘、分析与 HTML 报告。</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    page = st.radio("工作区", ["研究向导", "环境诊断", "历史项目"])

if page == "环境诊断":
    st.json(run_diagnostics())
elif page == "历史项目":
    projects = sorted((PROJECT_ROOT / "outputs").glob("*/manifest.json"))
    if not projects:
        st.info("尚无历史项目。")
    for manifest in projects:
        report = manifest.parent / "report" / "report.html"
        st.markdown(f"- [{manifest.parent.name}]({report.as_uri()})")
else:
    st.subheader("2 · 安装环境排查")
    environment = run_diagnostics()
    e1, e2, e3 = st.columns(3)
    e1.metric("核心运行时", "就绪" if environment["core_ready"] else "缺失")
    e2.metric("UI", "就绪" if environment["ui_ready"] else "缺失")
    e3.metric("BrowserAct CLI", "就绪" if environment["browseract_cli_ready"] else "缺失")
    with st.expander("查看完整诊断"):
        st.json(environment)

    st.subheader("3 · 任务目标与研究简报")
    c1, c2 = st.columns(2)
    name = c1.text_input("项目名称", "xhs-research-project")
    subject = c2.text_input("研究对象", "智能座舱仪表盘与 HUD 产品体验")
    adapter = st.selectbox(
        "数据入口（必须选择）",
        list(COLLECTION_ADAPTERS),
        format_func=lambda key: f"{key} · {COLLECTION_ADAPTERS[key]['label']}",
    )
    st.caption(COLLECTION_ADAPTERS[adapter]["description"])
    upload = None
    input_path = ""
    browseract_input_path = ""
    mediacrawler_input_path = ""
    mediacrawler_path = ""
    if adapter == "import":
        upload = st.file_uploader("导入 CSV / XLSX / JSONL / Parquet", type=["csv", "xlsx", "xls", "jsonl", "json", "parquet"])
    elif adapter == "browseract":
        upload = st.file_uploader("上传 BrowserAct 已持久化的复合 JSON / JSONL", type=["json", "jsonl"])
        browseract_input_path = st.text_input("或填写 BrowserAct 复合文件路径")
    elif adapter == "mediacrawler":
        mediacrawler_path = st.text_input("MediaCrawler 本机路径", help="实时运行时必须指向包含 main.py 的目录")
        mediacrawler_input_path = st.text_input("或填写已持久化的 MediaCrawler 输出目录")
    elif adapter == "hybrid":
        upload = st.file_uploader("上传 BrowserAct 复合 JSON / JSONL", type=["json", "jsonl"])
        browseract_input_path = st.text_input("或填写 BrowserAct 复合文件路径")
        mediacrawler_path = st.text_input("MediaCrawler 本机路径（实时运行）")
        mediacrawler_input_path = st.text_input("或填写已持久化的 MediaCrawler 输出目录")

    keywords = st.text_area("确认执行的关键词（每行一个）", subject, help="只有这里确认的关键词会执行；功能、场景、痛点和需求扩展词只在计划中建议。")
    c1, c2, c3 = st.columns(3)
    crawl_mode = c1.selectbox("采集深度", ["quick", "standard", "deep", "custom"], index=1)
    max_notes_per_keyword = c2.number_input("每个关键词最多笔记", min_value=1, max_value=1000, value=20)
    max_comments = c3.number_input("每篇最多评论", min_value=0, max_value=1000, value=20)
    include_comments = st.checkbox("采集当前会话可见评论", value=True)
    include_sub_comments = st.checkbox("采集可见二级回复", value=False, disabled=not include_comments)

    st.markdown("#### 七段研究简报")
    st.caption("逐段选择 Auto 或自定义。未选择的段落不会被当成 Auto，也不能进入下一阶段。")
    section_labels = {
        "project": "项目目标与决策",
        "source": "来源、采样与已知偏差",
        "ai_labels": "AI 标签方向与不确定路径",
        "insights": "洞察问题与比较组",
        "focus_rules": "过滤、去重与证据规则",
        "prompts": "编码、命名与摘要规范",
        "output": "受众、章节与交付",
    }
    auto_fields, custom = [], {}
    for key, label in section_labels.items():
        with st.expander(label):
            choice = st.radio(f"{label}配置方式", ["请选择", "Auto", "自定义"], horizontal=True, key=f"choice-{key}")
            if choice == "Auto":
                auto_fields.append(key)
                st.caption("系统将记录 Auto 的实际解析值、来源与理由。")
            elif choice == "自定义":
                details = st.text_area("输入具体要求", key=f"text-{key}")
                custom[key] = {"details": details}

    st.subheader("4 · 舆情挖掘方式与分析选择")
    mode = st.selectbox(
        "主题引擎（必须选择）",
        ["请选择", *TOPIC_ENGINES],
        format_func=lambda key: "请选择" if key == "请选择" else f"{key} · {TOPIC_ENGINES[key]['label']}",
    )
    if mode != "请选择":
        st.markdown(f'<div class="mode-note"><b>{TOPIC_ENGINES[mode]["description"]}</b><br>{TOPIC_ENGINES[mode]["requirements"]}</div>', unsafe_allow_html=True)
    profile = st.selectbox(
        "研究 Profile（必须选择）",
        ["请选择", *RESEARCH_PROFILES],
        format_func=lambda key: "请选择" if key == "请选择" else f"{key} · {RESEARCH_PROFILES[key]['label']}",
    )
    profiles: list[str] = []
    if profile != "请选择":
        info = RESEARCH_PROFILES[profile]
        st.markdown(f'<div class="mode-note"><b>回答：</b>{info["question"]}<br><b>输出：</b>{info["outputs"]}</div>', unsafe_allow_html=True)
    if profile == "mixed":
        profiles = st.multiselect(
            "Mixed 组合（至少选择一项）",
            [key for key in RESEARCH_PROFILES if key not in {"mixed"}],
            default=["rapid", "discovery", "aspect", "experience", "comparative", "network"],
            format_func=lambda key: f"{key} · {RESEARCH_PROFILES[key]['label']}",
        )
    elif profile != "请选择":
        profiles = [profile]

    predictive_enabled = "predictive" in profiles and st.checkbox("启用预测建模门槛检查", value=False)
    llm = st.selectbox("外部 LLM", ["none", "openai-compatible"])
    authorized = st.checkbox("明确授权传输下述脱敏文本范围", disabled=llm == "none")
    allowed_text = st.text_input("允许传输范围", "none" if llm == "none" else "仅脱敏 clean_text，最多 50 条")

    brief_ready = len(auto_fields) + len(custom) == len(section_labels)
    analysis_ready = mode != "请选择" and profile != "请选择" and (profile != "mixed" or bool(profiles))
    source_ready = {
        "mock": True,
        "import": bool(upload) or bool(input_path),
        "browseract": bool(upload) or bool(browseract_input_path),
        "mediacrawler": bool(mediacrawler_path) or bool(mediacrawler_input_path),
        "hybrid": (bool(upload) or bool(browseract_input_path)) and (bool(mediacrawler_path) or bool(mediacrawler_input_path)),
    }.get(adapter, False)
    preview_ready = brief_ready and analysis_ready and source_ready

    def build_candidate(plan_confirmed: bool) -> tuple[dict, Path]:
        base = yaml.safe_load((ASSET_ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
        persisted_input = input_path or None
        persisted_browseract = browseract_input_path or None
        if upload:
            upload_dir = Path(tempfile.mkdtemp(prefix="xhs-research-upload-"))
            target = upload_dir / upload.name
            target.write_bytes(upload.getvalue())
            if adapter == "import":
                persisted_input = str(target)
            else:
                persisted_browseract = str(target)
        base["workflow"]["mode"] = "ui"
        base["project"].update({"name": name, "execution_mode": "ui-guided"})
        base["brief"].update({"confirmed": True, "auto_fields": auto_fields, **custom})
        base["crawler"].update({
            "adapter": adapter,
            "mode": crawl_mode,
            "plan_confirmed": plan_confirmed,
            "input_path": persisted_input,
            "browseract_input_path": persisted_browseract,
            "mediacrawler_input_path": mediacrawler_input_path or None,
            "mediacrawler_path": mediacrawler_path or None,
            "keywords": [value.strip() for value in keywords.splitlines() if value.strip()],
            "max_notes": int(max_notes_per_keyword) * max(1, len([value for value in keywords.splitlines() if value.strip()])),
            "max_notes_per_keyword": int(max_notes_per_keyword),
            "include_comments": include_comments,
            "include_sub_comments": include_sub_comments,
            "max_comments_per_note": int(max_comments),
        })
        base["analysis"].update({"subject": subject, "mode": mode, "profile": profile, "profiles": profiles})
        base["analysis"]["predictive"]["enabled"] = predictive_enabled
        base["llm"].update({"provider": llm, "authorized": authorized if llm != "none" else False, "allowed_text": allowed_text, "max_rows": 50 if llm != "none" else 0})
        config_file = Path(tempfile.mkdtemp(prefix="xhs-research-config-")) / "project.yaml"
        config_file.write_text(yaml.safe_dump(base, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return base, config_file

    if st.button("预览研究简报与采集计划", disabled=not preview_ready):
        candidate, config_file = build_candidate(False)
        brief = resolve_brief(candidate)
        plan = build_crawl_plan(candidate, brief)
        st.session_state["candidate_config"] = candidate
        st.session_state["candidate_file"] = str(config_file)
        st.session_state["candidate_brief"] = brief
        st.session_state["candidate_plan"] = plan

    if "candidate_plan" in st.session_state:
        plan = st.session_state["candidate_plan"]
        brief = st.session_state["candidate_brief"]
        st.subheader("5 · 分析与 HTML 生成前确认")
        st.markdown('<div class="plan-box">', unsafe_allow_html=True)
        st.write(f"**研究目标：** {brief['resolved']['project']['resolved'].get('analysis_goal', '见自定义简报')}")
        st.write(f"**执行入口：** {plan['adapter']} · **采集深度：** {plan['mode']}")
        st.write(f"**实际执行关键词：** {'；'.join(plan['executed_keywords']) or '无'}")
        st.write(f"**评论范围：** {'含可见评论' if plan['limits']['include_comments'] else '不含评论'}；二级回复 {'开启' if plan['limits']['include_sub_comments'] else '关闭'}")
        suggestions = [item["keyword"] for item in plan["suggested_keyword_expansions"][:12]]
        st.write(f"**建议但不会自动执行：** {'；'.join(suggestions) or '无'}")
        st.write(f"**分析：** {mode} × {profile}{'（' + '、'.join(profiles) + '）' if profile == 'mixed' else ''}")
        st.markdown('</div>', unsafe_allow_html=True)
        plan_confirmed = st.checkbox("确认以上研究简报、执行关键词、采集范围、分析模式、证据规则与隐私设置")
        if st.button("确认并运行完整工作流", type="primary", disabled=not plan_confirmed):
            candidate = dict(st.session_state["candidate_config"])
            candidate["crawler"] = dict(candidate["crawler"])
            candidate["crawler"]["plan_confirmed"] = True
            config_file = Path(st.session_state["candidate_file"])
            config_file.write_text(yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False), encoding="utf-8")
            bar = st.progress(0)
            status = st.empty()

            def progress(message, fraction):
                status.info(message)
                bar.progress(fraction)

            try:
                result = run_all(load_config(config_file), progress)
                st.success("工作流完成")
                st.json({key: value for key, value in result.items() if key != "analysis"})
                st.components.v1.html(Path(result["report"]).read_text(encoding="utf-8"), height=900, scrolling=True)
            except Exception as exc:
                st.error(f"{type(exc).__name__}: {exc}")

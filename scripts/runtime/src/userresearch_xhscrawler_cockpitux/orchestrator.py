from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import platform
import sys
from typing import Any, Callable

from .analysis import run_analysis
from .brief import resolve_brief
from .cleaning import clean_project
from .config import load_config, project_dir, write_yaml
from .crawler import collect_records
from .insights import synthesize_insights
from .planner import build_crawl_plan
from .reporting import generate_report
from .storage import ProjectPaths, read_json, write_json


Progress = Callable[[str, float], None]


def _notify(progress: Progress | None, message: str, fraction: float) -> None:
    if progress: progress(message, fraction)
    else: print(message, flush=True)


def initialize_project(config: dict[str, Any], progress: Progress | None = None) -> ProjectPaths:
    paths = ProjectPaths(project_dir(config)).create()
    paths.state("init", "running")
    _notify(progress, "已解析项目配置", 0.03)
    paths.save_config(config)
    brief = resolve_brief(config)
    write_json(brief, paths.root / "analysis_brief.json")
    write_yaml(brief, paths.root / "research_brief.yaml")
    plan = build_crawl_plan(config, brief)
    write_yaml(plan, paths.root / "crawl_plan.yaml")
    paths.state("init", "complete", {"keywords": len(plan["keyword_groups"])})
    _notify(progress, f"已生成研究 brief 与 {len(plan['keyword_groups'])} 条关键词计划", 0.08)
    return paths


def crawl_stage(config: dict[str, Any], paths: ProjectPaths | None = None, progress: Progress | None = None) -> dict[str, Any]:
    paths = paths or initialize_project(config, progress)
    if not (paths.root / "analysis_brief.json").exists(): initialize_project(config, progress)
    if config.get("crawler", {}).get("adapter") in {"browser", "browseract", "mediacrawler", "hybrid"} and not config.get("crawler", {}).get("plan_confirmed"):
        raise ValueError("live collection requires crawler.plan_confirmed=true after reviewing crawl_plan.yaml")
    paths.state("crawl", "running")
    _notify(progress, "正在采集或导入小红书记录", 0.16)
    result = collect_records(config, paths)
    write_json({
        **result,
        "workflow_mode": config.get("workflow", {}).get("mode"),
        "executed_keywords": config.get("crawler", {}).get("keywords", []),
        "include_comments": bool(config.get("crawler", {}).get("include_comments")),
    }, paths.root / "collection_observation.json")
    paths.state("crawl", "complete", result)
    _notify(progress, f"采集完成：{result['posts']} 帖、{result['comments']} 条评论", 0.28)
    return result


def clean_stage(config: dict[str, Any], paths: ProjectPaths, progress: Progress | None = None) -> dict[str, Any]:
    paths.state("clean", "running")
    _notify(progress, "正在执行清洗、去重、营销与相关性诊断", 0.34)
    quality = clean_project(config, paths)
    paths.state("clean", "complete", {"valid_records": quality["valid_records"], "excluded_records": quality["excluded_records"]})
    _notify(progress, f"清洗完成：有效 {quality['valid_records']} 条，排除 {quality['excluded_records']} 条", 0.48)
    return quality


def analyze_stage(config: dict[str, Any], paths: ProjectPaths, mode: str | None = None, profile: str | None = None, progress: Progress | None = None) -> dict[str, Any]:
    paths.state("analyze", "running")
    _notify(progress, "正在运行主题、LDA、情感、情绪、功能、场景、趋势与风险分析", 0.56)
    analysis = run_analysis(config, paths, mode, profile)
    _notify(progress, "正在合成并校验证据化用户洞察", 0.76)
    insights = synthesize_insights(config, paths)
    paths.state("analyze", "complete", {"records": analysis["records"], "mode_used": analysis["mode_used"], "profiles_used": analysis["profiles_used"], "insights": len(insights["insights"])})
    return analysis


def report_stage(config: dict[str, Any], paths: ProjectPaths, progress: Progress | None = None) -> Path:
    paths.state("report", "running")
    _notify(progress, "正在生成自包含交互式 HTML 报告", 0.86)
    report = generate_report(config, paths)
    paths.state("report", "complete", {"report": str(report)})
    build_manifest(config, paths)
    _notify(progress, "报告、证据索引与 manifest 已完成", 1.0)
    return report


def build_manifest(config: dict[str, Any], paths: ProjectPaths) -> dict[str, Any]:
    files = []
    for path in sorted(paths.root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            files.append({"path": path.relative_to(paths.root).as_posix(), "bytes": path.stat().st_size, "sha256": digest})
    analysis = read_json(paths.analysis / "analysis.json", {})
    quality = read_json(paths.processed / "data_quality.json", {})
    state = read_json(paths.root / "state.json", {})
    manifest = {
        "schema_version": "1.0", "project": config["project"]["name"], "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_scale": {"raw": quality.get("raw_records", 0), "valid": quality.get("valid_records", 0)},
        "config_files": ["project_config.yaml", "research_brief.yaml", "crawl_plan.yaml"],
        "code_version": "1.0.0", "python": platform.python_version(), "platform": sys.platform,
        "models": {"topic_mode": analysis.get("mode_used"), "analysis_profiles": analysis.get("profiles_used", []), "topic_engine": analysis.get("provenance", {}).get("topic_engine"), "predictive_status": analysis.get("predictive", {}).get("status"), "sentiment": analysis.get("provenance", {}).get("sentiment"), "external_llm": analysis.get("provenance", {}).get("external_llm")},
        "analysis_modules": config.get("analysis", {}).get("modules", []), "state": state, "warnings": quality.get("warnings", []), "files": files,
    }
    write_json(manifest, paths.root / "manifest.json")
    return manifest


def run_all(config: dict[str, Any], progress: Progress | None = None) -> dict[str, Any]:
    paths = initialize_project(config, progress)
    crawl = crawl_stage(config, paths, progress)
    quality = clean_stage(config, paths, progress)
    analysis = analyze_stage(config, paths, config["analysis"]["mode"], config["analysis"]["profile"], progress)
    report = report_stage(config, paths, progress)
    return {"project_dir": str(paths.root), "crawl": crawl, "quality": quality, "analysis": {"records": analysis["records"], "mode_requested": analysis["mode_requested"], "mode_used": analysis["mode_used"], "profile_requested": analysis["profile_requested"], "profiles_used": analysis["profiles_used"], "topic_count": len(analysis.get("topics", [])), "predictive_status": analysis.get("predictive", {}).get("status"), "insight_file": str(paths.analysis / "insight_summary.json")}, "report": str(report), "manifest": str(paths.root / "manifest.json")}


def load_project(project: str, output_root: str | Path | None = None) -> tuple[dict[str, Any], ProjectPaths]:
    from .config import PROJECT_ROOT
    root = Path(output_root).expanduser().resolve() if output_root else Path.cwd() / "outputs"
    path = root / project / "project_config.yaml"
    if not path.exists(): raise FileNotFoundError(f"Project config not found: {path}")
    return load_config(path), ProjectPaths(root / project).create()

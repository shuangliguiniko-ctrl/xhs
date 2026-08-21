from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .config import load_config
from .diagnostics import run_diagnostics
from .orchestrator import analyze_stage, clean_stage, crawl_stage, initialize_project, load_project, report_stage, run_all


def _config_or_project(args) -> tuple[dict, object]:
    if getattr(args, "config", None):
        config = load_config(args.config); paths = initialize_project(config); return config, paths
    return load_project(args.project, getattr(args, "output_root", None))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="new-xhs-research", description="Five-step AI and UI Xiaohongshu research studio")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.add_argument("--config", required=True)
    diagnose = sub.add_parser("diagnose"); diagnose.add_argument("--config")
    crawl = sub.add_parser("crawl"); crawl.add_argument("--config", required=True)
    for name in ("clean", "report"):
        item = sub.add_parser(name); item.add_argument("--project", required=True); item.add_argument("--output-root")
    analyze = sub.add_parser("analyze"); analyze.add_argument("--project", required=True); analyze.add_argument("--mode", required=True, choices=["fast", "semantic", "auto"]); analyze.add_argument("--profile", required=True, choices=["rapid", "discovery", "aspect", "experience", "comparative", "network", "predictive", "mixed"]); analyze.add_argument("--output-root")
    run = sub.add_parser("run"); run.add_argument("--config", required=True)
    ui = sub.add_parser("ui"); ui.add_argument("--port", type=int, default=8501)
    package = sub.add_parser("package"); package.add_argument("--project", required=True); package.add_argument("--output-root")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "diagnose":
            config = load_config(args.config) if args.config else None; result = run_diagnostics(config)
        elif args.command == "init":
            config = load_config(args.config); result = {"project_dir": str(initialize_project(config).root)}
        elif args.command == "crawl":
            config = load_config(args.config); paths = initialize_project(config); result = crawl_stage(config, paths)
        elif args.command == "clean":
            config, paths = load_project(args.project, args.output_root); result = clean_stage(config, paths)
        elif args.command == "analyze":
            config, paths = load_project(args.project, args.output_root); result = analyze_stage(config, paths, args.mode, args.profile)
        elif args.command == "report":
            config, paths = load_project(args.project, args.output_root); result = {"report": str(report_stage(config, paths))}
        elif args.command == "run":
            result = run_all(load_config(args.config))
        elif args.command == "ui":
            import subprocess  # nosec B404
            app = Path(__file__).with_name("ui") / "app.py"
            return subprocess.call(  # noqa: S603  # nosec B603
                [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(args.port)]
            )
        else:
            _, paths = load_project(args.project, args.output_root)
            archive = shutil.make_archive(str(paths.root), "zip", paths.root); result = {"archive": archive}
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Any

from .config import SKILL_ROOT

CORE = ["pandas", "numpy", "sklearn", "jieba", "yaml", "openpyxl", "pyarrow", "requests"]
UI = ["streamlit", "plotly"]
SEMANTIC = ["sentence_transformers", "bertopic", "umap", "hdbscan"]


def run_diagnostics(config: dict[str, Any] | None = None) -> dict[str, Any]:
    packages = {name: bool(importlib.util.find_spec(name)) for name in [*CORE, *UI, *SEMANTIC, "ruptures"]}
    configured_crawler = str((config or {}).get("crawler", {}).get("mediacrawler_path") or "").strip()
    crawler_path = Path(configured_crawler).expanduser() if configured_crawler else None
    if crawler_path and not crawler_path.is_absolute():
        crawler_path = (SKILL_ROOT / crawler_path).resolve()
    crawler = (config or {}).get("crawler", {})
    adapter = str(crawler.get("adapter") or "unselected")
    browseract_path = shutil.which("browser-act")
    browseract_input = str(crawler.get("browseract_input_path") or crawler.get("input_path") or "").strip()
    browseract_file = Path(browseract_input).expanduser() if browseract_input else None
    if browseract_file and not browseract_file.is_absolute():
        browseract_file = (SKILL_ROOT / browseract_file).resolve()
    mediacrawler_input = str(crawler.get("mediacrawler_input_path") or "").strip()
    mediacrawler_input_path = Path(mediacrawler_input).expanduser() if mediacrawler_input else None
    if mediacrawler_input_path and not mediacrawler_input_path.is_absolute():
        mediacrawler_input_path = (SKILL_ROOT / mediacrawler_input_path).resolve()
    local_input = str(crawler.get("input_path") or "").strip()
    local_input_path = Path(local_input).expanduser() if local_input else None
    if local_input_path and not local_input_path.is_absolute():
        local_input_path = (SKILL_ROOT / local_input_path).resolve()
    configured_output = Path(os.environ.get("XHS_RESEARCH_OUTPUT_ROOT") or str((config or {}).get("project", {}).get("output_root", "outputs")))
    output_root = configured_output if configured_output.is_absolute() else Path.cwd() / configured_output
    output_parent = output_root if output_root.exists() else output_root.parent
    browseract_ready = bool(browseract_path and browseract_file and browseract_file.exists())
    mediacrawler_code_ready = bool(crawler_path and (crawler_path / "main.py").exists())
    mediacrawler_saved_ready = bool(mediacrawler_input_path and mediacrawler_input_path.exists())
    import_ready = bool(local_input_path and local_input_path.exists())
    readiness = {
        "mock": True,
        "import": import_ready,
        "browser": browseract_ready,
        "browseract": browseract_ready,
        "mediacrawler": mediacrawler_code_ready or mediacrawler_saved_ready,
        "hybrid": browseract_ready and (mediacrawler_code_ready or mediacrawler_saved_ready),
    }
    return {
        "python": sys.executable,
        "python_version": platform.python_version(),
        "supported_python": sys.version_info >= (3, 11),
        "platform": platform.platform(),
        "packages": packages,
        "core_ready": all(packages[name] for name in CORE),
        "ui_ready": all(packages[name] for name in UI),
        "semantic_ready": all(packages[name] for name in SEMANTIC),
        "mediacrawler_path": str(crawler_path) if crawler_path else None,
        "workflow_mode": (config or {}).get("workflow", {}).get("mode"),
        "selected_adapter": adapter,
        "selected_adapter_ready": readiness.get(adapter, False),
        "adapter_readiness": readiness,
        "browseract_cli": browseract_path,
        "browseract_cli_ready": bool(browseract_path),
        "browseract_input_ready": bool(browseract_file and browseract_file.exists()),
        "browseract_live_requirements": ["compatible BrowserAct Core skill", "authorized browser", "active accessible Xiaohongshu session"],
        "mediacrawler_ready": mediacrawler_code_ready or mediacrawler_saved_ready,
        "mediacrawler_code_ready": mediacrawler_code_ready,
        "mediacrawler_input_ready": mediacrawler_saved_ready,
        "mediacrawler_license_review_required": True,
        "output_root": str(output_root.resolve()),
        "local_input_ready": import_ready,
        "output_writable": output_parent.exists() and os.access(output_parent, os.W_OK),
        "external_llm_key_present": bool(os.environ.get((config or {}).get("llm", {}).get("api_key_env", "OPINION_LLM_API_KEY"))),
        "notes": [
            "BrowserAct CLI readiness does not prove that login state or a live Xiaohongshu page is available.",
            "Semantic packages/models are optional and must not be installed or downloaded without authorization.",
            "MediaCrawler retains its own license and platform compliance obligations.",
        ],
    }

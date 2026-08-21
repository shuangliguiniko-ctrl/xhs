from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
from typing import Any

import yaml


def _skill_root() -> Path:
    configured = os.environ.get("XHS_RESEARCH_SKILL_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "SKILL.md").is_file():
            return parent
    return Path(__file__).resolve().parents[2]


SKILL_ROOT = _skill_root()
PROJECT_ROOT = SKILL_ROOT
ASSET_ROOT = SKILL_ROOT / "assets" if (SKILL_ROOT / "assets" / "config").is_dir() else SKILL_ROOT


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def read_yaml(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    with source.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {source}")
    return payload


def write_yaml(payload: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    temporary.replace(target)
    return target


def load_config(path: str | Path) -> dict[str, Any]:
    default = read_yaml(ASSET_ROOT / "config" / "default.yaml")
    supplied = read_yaml(path)
    config = deep_merge(default, supplied)
    validate_config(config)
    config["_config_path"] = str(Path(path).expanduser().resolve())
    return config


def validate_config(config: dict[str, Any]) -> None:
    workflow_mode = config.get("workflow", {}).get("mode")
    if workflow_mode not in {None, "ai", "ui"}:
        raise ValueError("workflow.mode must be ai, ui, or null before the first decision")
    name = str(config.get("project", {}).get("name", "")).strip()
    if not name:
        raise ValueError("project.name is required")
    if any(char in name for char in "/\\\0"):
        raise ValueError("project.name must not contain path separators")
    adapter = config.get("crawler", {}).get("adapter")
    if adapter not in {"mock", "import", "browser", "browseract", "mediacrawler", "hybrid"}:
        raise ValueError("crawler.adapter must be browseract, mediacrawler, hybrid, import, mock, or legacy browser")
    mode = config.get("analysis", {}).get("mode")
    if mode not in {None, "fast", "semantic", "auto"}:
        raise ValueError("analysis.mode must be fast, semantic, auto, or null before confirmation")
    profile = config.get("analysis", {}).get("profile")
    profiles = set(config.get("analysis", {}).get("profiles", []))
    allowed_profiles = {"rapid", "discovery", "aspect", "experience", "comparative", "network", "predictive", "mixed"}
    if profile not in {None, *allowed_profiles}:
        raise ValueError("analysis.profile is invalid")
    if profiles - allowed_profiles:
        raise ValueError(f"analysis.profiles contains invalid values: {sorted(profiles - allowed_profiles)}")
    llm = config.get("llm", {})
    if llm.get("provider") != "none" and not llm.get("authorized"):
        raise ValueError("external LLM provider requires llm.authorized=true and explicit allowed_text")
    if llm.get("authorized") and llm.get("allowed_text") in {None, "", "none"}:
        raise ValueError("authorized external LLM use requires llm.allowed_text")


def project_dir(config: dict[str, Any], root_override: str | Path | None = None) -> Path:
    if root_override:
        root = Path(root_override)
    else:
        configured = Path(str(config["project"].get("output_root", "outputs")))
        root = configured if configured.is_absolute() else Path.cwd() / configured
    return root.expanduser().resolve() / config["project"]["name"]

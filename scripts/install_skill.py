#!/usr/bin/env python3
"""Install the standard New XHS Research skill package for Codex or OpenCode."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404
import sys
import tomllib


SOURCE = Path(__file__).resolve().parents[1]
SKILL_NAME = "new-xhs-research"
IMPORT_NAMES = {
    "pandas": "pandas",
    "numpy": "numpy",
    "scikit-learn": "sklearn",
    "jieba": "jieba",
    "pyyaml": "yaml",
    "openpyxl": "openpyxl",
    "pyarrow": "pyarrow",
    "requests": "requests",
    "streamlit": "streamlit",
    "plotly": "plotly",
    "sentence-transformers": "sentence_transformers",
    "bertopic": "bertopic",
    "umap-learn": "umap",
    "hdbscan": "hdbscan",
    "ruptures": "ruptures",
}


def destination(args: argparse.Namespace) -> Path:
    if args.codex:
        return Path.home() / ".codex" / "skills" / SKILL_NAME
    if args.opencode_global:
        return Path.home() / ".config" / "opencode" / "skills" / SKILL_NAME
    if args.opencode_project:
        return args.opencode_project.expanduser().resolve() / ".opencode" / "skills" / SKILL_NAME
    if args.agents_project:
        return args.agents_project.expanduser().resolve() / ".agents" / "skills" / SKILL_NAME
    return args.destination.expanduser().resolve()


def copy_skill(target: Path, force: bool) -> Path | None:
    if target == SOURCE:
        raise ValueError("Source and destination are the same directory")
    backup = None
    if target.exists():
        if not force:
            raise FileExistsError(f"Destination exists: {target}. Use --force to back it up and replace it.")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target.parent / f"{SKILL_NAME}-backup-{stamp}"
        shutil.move(str(target), str(backup))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        SOURCE,
        target,
        ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "*.pyo", ".DS_Store", ".env"),
    )
    return backup


def runtime_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def requirement_name(spec: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", spec)
    if not match:
        raise ValueError(f"Unsupported requirement: {spec}")
    return match.group(0).lower()


def requirements(target: Path, profile: str) -> list[str]:
    project_file = target / "scripts" / "runtime" / "pyproject.toml"
    project = tomllib.loads(project_file.read_text(encoding="utf-8"))["project"]
    specs = list(project.get("dependencies", []))
    if profile != "core":
        specs.extend(project.get("optional-dependencies", {}).get(profile, []))
    return specs


def missing(python: Path, specs: list[str]) -> list[str]:
    modules = {
        spec: IMPORT_NAMES.get(requirement_name(spec), requirement_name(spec).replace("-", "_")) for spec in specs
    }
    probe = (
        "import importlib.util,importlib.metadata,json,sys; "
        "from pip._vendor.packaging.requirements import Requirement; "
        "mods=json.loads(sys.argv[1]); missing=[]; "
        "exec(\"for spec,module in mods.items():\\n"
        " r=Requirement(spec)\\n"
        " try: installed=importlib.metadata.version(r.name)\\n"
        " except importlib.metadata.PackageNotFoundError: installed=None\\n"
        " if importlib.util.find_spec(module) is None or installed is None or (r.specifier and installed not in r.specifier): missing.append(spec)\"); "
        "print(json.dumps(missing))"
    )
    completed = subprocess.run(  # noqa: S603  # nosec B603
        [str(python), "-c", probe, json.dumps(modules)], check=True, text=True, capture_output=True
    )
    return json.loads(completed.stdout)


def prepare_runtime(
    target: Path,
    base_python: Path,
    profile: str,
    system_site_packages: bool,
    index_url: str | None,
    cert: Path | None,
) -> Path:
    version_check = subprocess.run(  # noqa: S603  # nosec B603
        [str(base_python), "-c", "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info < (3, 15) else 1)"],
        capture_output=True,
    )
    if version_check.returncode != 0:
        raise RuntimeError(f"Python 3.11-3.14 is required: {base_python}")
    venv = target / ".venv"
    command = [str(base_python), "-m", "venv"]
    if system_site_packages:
        command.append("--system-site-packages")
    command.append(str(venv))
    subprocess.run(command, check=True)  # noqa: S603  # nosec B603
    python = runtime_python(venv)
    site = subprocess.run(  # nosec B603  # noqa: S603
        [str(python), "-c", "import site; print(site.getsitepackages()[0])"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    runtime_src = target / "scripts" / "runtime" / "src"
    (Path(site) / "xhs_research_skill.pth").write_text(str(runtime_src) + "\n", encoding="utf-8")
    needed = missing(python, requirements(target, profile))
    if needed:
        pip = [str(python), "-m", "pip", "install"]
        if index_url:
            pip.extend(["--index-url", index_url])
        if cert:
            pip.extend(["--cert", str(cert.expanduser().resolve())])
        subprocess.run([*pip, *needed], check=True)  # noqa: S603  # nosec B603
    return python


def reuse_runtime(target: Path, existing_venv: Path, profile: str) -> Path:
    source = existing_venv.expanduser().resolve()
    python = runtime_python(source)
    if not python.is_file():
        raise FileNotFoundError(f"Existing virtual environment has no Python executable: {python}")
    needed = missing(python, requirements(target, profile)) if profile != "none" else []
    if needed:
        raise RuntimeError(f"Existing virtual environment is missing required dependencies: {needed}")
    link = target / ".venv"
    link.symlink_to(source, target_is_directory=True)
    return python


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Install the standard New XHS Research skill")
    target = result.add_mutually_exclusive_group(required=True)
    target.add_argument("--codex", action="store_true", help="Install in ~/.codex/skills/new-xhs-research")
    target.add_argument("--opencode-global", action="store_true")
    target.add_argument("--opencode-project", type=Path)
    target.add_argument("--agents-project", type=Path)
    target.add_argument("--destination", type=Path, help="Exact new-xhs-research destination directory")
    result.add_argument("--deps", choices=("none", "core", "ui", "semantic"), default="core")
    result.add_argument("--python", type=Path, default=Path(sys.executable))
    result.add_argument("--system-site-packages", action="store_true")
    result.add_argument("--existing-venv", type=Path, help="Reuse a verified local virtual environment without downloading dependencies")
    result.add_argument("--index-url")
    result.add_argument("--cert", type=Path)
    result.add_argument("--mediacrawler", type=Path)
    result.add_argument("--force", action="store_true")
    result.add_argument("--skip-verify", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    target = destination(args)
    try:
        backup = copy_skill(target, args.force)
        python = None
        if args.existing_venv:
            python = reuse_runtime(target, args.existing_venv, args.deps)
        elif args.deps != "none":
            python = prepare_runtime(
                target,
                Path(os.path.abspath(os.path.expanduser(str(args.python)))),
                args.deps,
                args.system_site_packages,
                args.index_url,
                args.cert,
            )
        if not args.skip_verify:
            command = [sys.executable, str(target / "scripts" / "verify_skill.py"), "--skill-dir", str(target)]
            if python:
                command.extend(["--python", str(python), "--full"])
            if args.mediacrawler:
                command.extend(["--mediacrawler", str(args.mediacrawler.expanduser().resolve())])
            subprocess.run(command, check=True)  # noqa: S603  # nosec B603
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"INSTALL FAILED: {error}", file=sys.stderr)
        return 1
    print(f"Installed standard skill: {target}")
    if backup:
        print(f"Previous version backed up: {backup}")
    if python:
        print(f"Runtime: {python}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

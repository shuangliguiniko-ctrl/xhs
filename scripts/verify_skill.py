#!/usr/bin/env python3
"""Validate the strict structure, content, safety, and runtime of New XHS Research."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess  # nosec B404
import sys
import tempfile
from typing import Any


EXPECTED_DIRECTORIES = {"agents", "assets", "references", "scripts"}
EXPECTED_CHILDREN = {
    "environment-diagnostics",
    "evidence-validator",
    "html-report-generator",
    "opinion-analysis-engine",
    "opinion-data-cleaner",
    "predictive-modeler",
    "research-brief-builder",
    "user-insight-synthesizer",
    "xhs-crawler-planner",
    "xhs-data-collector",
}
CORE_FILES = (
    "SKILL.md",
    "INSTALL.md",
    "LICENSE",
    "agents/openai.yaml",
    "assets/config/default.yaml",
    "assets/examples/sample_project.yaml",
    "assets/templates/report/base.html",
    "references/resource-index.md",
    "references/security-and-validation.md",
    "scripts/install_skill.py",
    "scripts/launch.py",
    "scripts/package_shareable.py",
    "scripts/verify_skill.py",
    "scripts/runtime/pyproject.toml",
    "scripts/runtime/src/userresearch_xhscrawler_cockpitux/cli.py",
    "scripts/runtime/src/userresearch_xhscrawler_cockpitux/crawler/adapters.py",
    "scripts/runtime/tests/test_end_to_end.py",
)
TEXT_SUFFIXES = {".csv", ".html", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
SECOND_PERSON = re.compile(r"\b(?:you|your|yours|yourself|yourselves)\b|你|您", re.I)
PERSONAL_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
PRIVATE_IP = re.compile(r"\b(?:10(?:\.\d{1,3}){3}|127(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FORBIDDEN_COMPONENTS = re.compile(r"\b(?:scapy|mitmproxy|pyshark|debugpy|pysnooper|frida|pdb)\b", re.I)


def item(name: str, ok: bool, detail: str, warning: bool = False) -> dict[str, Any]:
    return {"check": name, "ok": ok, "warning": warning, "detail": detail}


def metadata(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.search(text)
    if not match:
        return {}, text
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result, text[match.end():]


def utf8_checks(root: Path) -> tuple[bool, list[str]]:
    failures = []
    for path in root.rglob("*"):
        if path.is_file() and ".venv" not in path.parts and path.suffix.lower() in TEXT_SUFFIXES:
            try:
                path.read_text(encoding="utf-8")
            except UnicodeError:
                failures.append(str(path.relative_to(root)))
    return not failures, failures


def reference_checks(root: Path) -> tuple[bool, list[str]]:
    failures = []
    for document in root.rglob("*.md"):
        if ".venv" in document.parts:
            continue
        text = document.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            target = target.split("#", 1)[0].strip()
            if not target or re.match(r"^[a-z]+://", target, re.I):
                continue
            candidate = (document.parent / target).resolve()
            if not candidate.exists():
                failures.append(f"{document.relative_to(root)} -> {target}")
    return not failures, failures


def resource_index_checks(root: Path) -> tuple[bool, list[str]]:
    index_file = root / "references" / "resource-index.md"
    if not index_file.is_file():
        return False, ["references/resource-index.md"]
    index = index_file.read_text(encoding="utf-8")
    missing = []
    for directory in sorted(EXPECTED_DIRECTORIES):
        for path in sorted((root / directory).rglob("*")):
            if not path.is_file() or path == index_file or ".venv" in path.parts:
                continue
            relative = path.relative_to(root).as_posix()
            if relative not in index:
                missing.append(relative)
    return not missing, missing


def safety_checks(root: Path) -> list[dict[str, Any]]:
    text_files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and ".venv" not in path.parts
        and path.suffix.lower() in TEXT_SUFFIXES
        and path.name != "verify_skill.py"
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in text_files)
    credential_patterns = (
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"(?i)(?:api[_-]?key|password|passwd|secret)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"),
        re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{16,}\b"),
    )
    credential_hits = [pattern.pattern for pattern in credential_patterns if pattern.search(combined)]
    pii_hits = []
    for path in text_files:
        text = path.read_text(encoding="utf-8")
        if PERSONAL_PHONE.search(text):
            pii_hits.append(f"phone:{path.relative_to(root)}")
        real_emails = [address for address in EMAIL.findall(text) if not address.endswith(".invalid")]
        if real_emails:
            pii_hits.append(f"email:{path.relative_to(root)}")
        if PRIVATE_IP.search(text):
            pii_hits.append(f"private-ip:{path.relative_to(root)}")
    component_hits = [str(path.relative_to(root)) for path in text_files if FORBIDDEN_COMPONENTS.search(path.read_text(encoding="utf-8"))]
    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    llm_client = root / "scripts" / "runtime" / "src" / "userresearch_xhscrawler_cockpitux" / "llm" / "client.py"
    injection_guard = "untrusted data" in skill_text and llm_client.is_file() and "UNTRUSTED_DATA_GUARD" in llm_client.read_text(encoding="utf-8")
    return [
        item("no_hardcoded_credentials", not credential_hits, f"hits={credential_hits}"),
        item("no_personal_or_private_addresses", not pii_hits, f"hits={pii_hits[:10]}"),
        item("no_questionable_components", not component_hits, f"hits={component_hits[:10]}"),
        item("prompt_injection_guard", injection_guard, "skill gate and LLM message guard present"),
    ]


def structural(root: Path) -> list[dict[str, Any]]:
    results = [item("skill_root", root.is_dir(), str(root))]
    if not root.is_dir():
        return results
    skill_file = root / "SKILL.md"
    frontmatter, body = metadata(skill_file) if skill_file.is_file() else ({}, "")
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    root_names = {path.name for path in root.iterdir()}
    directories = {path.name for path in root.iterdir() if path.is_dir() and path.name != ".venv"}
    results.extend(
        [
            item("root_SKILL.md", skill_file.is_file() and "SKILL.md" in root_names and "skill.md" not in root_names, str(skill_file)),
            item("directory_matches_name", root.name == name, f"directory={root.name!r} name={name!r}"),
            item("standard_directories", directories == EXPECTED_DIRECTORIES, f"directories={sorted(directories)}"),
            item("lowercase_directories", all(value == value.lower() and NAME_PATTERN.fullmatch(value) for value in directories), str(sorted(directories))),
            item("name_rules", bool(NAME_PATTERN.fullmatch(name)) and len(name) <= 64, f"name={name!r} length={len(name)}"),
            item("frontmatter_fields", set(frontmatter) == {"name", "description"}, f"fields={sorted(frontmatter)}"),
            item("description_rules", bool(description) and len(description) <= 1024 and description.startswith("Use for ") and not SECOND_PERSON.search(description), f"length={len(description)}"),
            item("body_line_limit", len(body.splitlines()) <= 500, f"lines={len(body.splitlines())}"),
            item("no_second_person", not SECOND_PERSON.search(body), "second-person pronoun scan"),
        ]
    )
    missing_core = [relative for relative in CORE_FILES if not (root / relative).is_file()]
    results.append(item("complete_code_tree", not missing_core, f"missing={missing_core}"))
    children = {path.parent.name for path in (root / "references" / "skills").glob("*/SKILL.md")}
    results.append(item("bundled_child_skills", children == EXPECTED_CHILDREN, f"found={len(children)} missing={sorted(EXPECTED_CHILDREN-children)}"))
    utf8_ok, utf8_failed = utf8_checks(root)
    results.append(item("utf8_text", utf8_ok, f"failures={utf8_failed}"))
    refs_ok, refs_failed = reference_checks(root)
    results.append(item("referenced_files_exist", refs_ok, f"failures={refs_failed[:10]}"))
    index_ok, index_missing = resource_index_checks(root)
    results.append(item("all_resources_indexed", index_ok, f"missing={index_missing[:10]}"))
    forbidden = [str(path.relative_to(root)) for path in root.rglob("*") if ".venv" not in path.parts and path.name in {".env", ".DS_Store"}]
    results.append(item("package_hygiene", not forbidden, f"forbidden={forbidden[:10]}"))
    checksum_file = root / "checksums.json"
    if checksum_file.is_file():
        expected = json.loads(checksum_file.read_text(encoding="utf-8"))
        failed = []
        for relative, digest in expected.items():
            path = root / relative
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            if actual != digest:
                failed.append(relative)
        results.append(item("file_checksums", not failed, f"files={len(expected)} failures={failed[:10]}"))
    else:
        results.append(item("file_checksums", False, "checksums.json missing"))
    results.extend(safety_checks(root))
    return results


def execute(command: list[str], cwd: Path, env: dict[str, str]) -> tuple[bool, str]:
    completed = subprocess.run(  # noqa: S603  # nosec B603
        command, cwd=cwd, env=env, text=True, capture_output=True
    )
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    return completed.returncode == 0, "\n".join(output.splitlines()[-12:]) or f"exit={completed.returncode}"


def runtime(root: Path, python: Path | None) -> list[dict[str, Any]]:
    if python is None:
        candidate = root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        python = candidate if candidate.is_file() else Path(sys.executable)
    python = Path(os.path.abspath(os.path.expanduser(str(python))))
    results = [item("python_runtime", python.is_file(), str(python))]
    if not python.is_file():
        return results
    runtime_root = root / "scripts" / "runtime"
    with tempfile.TemporaryDirectory(prefix="xhs-research-verify-") as temporary:
        env = dict(os.environ)
        env["XHS_RESEARCH_SKILL_ROOT"] = str(root)
        env["XHS_RESEARCH_OUTPUT_ROOT"] = temporary
        env["PYTHONPYCACHEPREFIX"] = str(Path(temporary) / "pycache")
        env["PYTHONPATH"] = str(runtime_root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        commands = (
            ("static_compile", [str(python), "-m", "compileall", "-q", "scripts"]),
            ("package_import", [str(python), "-c", "import userresearch_xhscrawler_cockpitux as p; print(p.__file__)"]),
            ("diagnostics", [str(python), "scripts/launch.py", "diagnose"]),
            ("unit_tests", [str(python), "-m", "unittest", "discover", "-s", "scripts/runtime/tests", "-v"]),
        )
        for name, command in commands:
            ok, detail = execute(command, root, env)
            results.append(item(name, ok, detail))
    return results


def mediacrawler(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return [item("mediacrawler_external", True, "optional external component; not supplied", True)]
    path = path.expanduser().resolve()
    license_file = path / "LICENSE"
    return [
        item("mediacrawler_main", (path / "main.py").is_file(), str(path / "main.py")),
        item("mediacrawler_license", license_file.is_file() and "NON-COMMERCIAL LEARNING LICENSE" in license_file.read_text(encoding="utf-8", errors="ignore"), str(license_file)),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the strict New XHS Research skill package")
    parser.add_argument("--skill-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--python", type=Path)
    parser.add_argument("--mediacrawler", type=Path)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.skill_dir.expanduser().resolve()
    results = structural(root)
    if args.full:
        results.extend(runtime(root, args.python))
    results.extend(mediacrawler(args.mediacrawler))
    failed = [result for result in results if not result["ok"] and not result["warning"]]
    summary = {"ok": not failed, "skill_dir": str(root), "checks": results}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for result in results:
            label = "WARN" if result["warning"] else "PASS" if result["ok"] else "FAIL"
            print(f"[{label}] {result['check']}: {result['detail']}")
        print(f"\nRESULT: {'PASS' if not failed else 'FAIL'} ({len(results)-len(failed)}/{len(results)} checks passed)")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

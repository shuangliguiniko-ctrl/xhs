#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile


EXCLUDED_PREFIXES = ("raw/mediacrawler/", "logs/")
EXCLUDED_NAMES = {"manifest.json", "shareable_manifest.json"}


def _selected(project: Path) -> list[Path]:
    files = []
    for path in sorted(project.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(project).as_posix()
        if relative in EXCLUDED_NAMES or relative.endswith(".zip") or relative.startswith(EXCLUDED_PREFIXES):
            continue
        files.append(path)
    return files


def _privacy_checks(project: Path) -> dict[str, object]:
    rows = []
    for relative in ("raw/posts.jsonl", "raw/comments.jsonl"):
        source = project / relative
        rows.extend(json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip())
    raw_blob = json.dumps(rows, ensure_ascii=False)
    html = (project / "report/report.html").read_text(encoding="utf-8")
    match = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
    if not match:
        raise ValueError("report payload not found")
    payload_blob = match.group(1)
    checks = {
        "standardized_raw_records": len(rows),
        "nonempty_author_values": sum(bool(row.get("author_name")) for row in rows),
        "raw_xsec_token_present": "xsec_token" in raw_blob,
        "raw_creator_hash_present": "creator_hash" in raw_blob,
        "report_xsec_token_present": "xsec_token" in payload_blob,
        "report_creator_hash_present": "creator_hash" in payload_blob,
        "report_at_signs": payload_blob.count("@"),
        "report_http_urls": len(re.findall(r"https?://", payload_blob)),
    }
    failed = [key for key, value in checks.items() if key != "standardized_raw_records" and value not in (0, False)]
    if failed:
        raise ValueError(f"shareable privacy checks failed: {failed}")
    return checks


def package(project: Path, output: Path) -> Path:
    project = project.expanduser().resolve()
    if not (project / "report/report.html").exists():
        raise FileNotFoundError("report/report.html not found")
    privacy = _privacy_checks(project)
    files = _selected(project)
    manifest = {
        "schema_version": "1.0",
        "project": project.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "de-identified shareable package",
        "excluded": ["raw/mediacrawler/**", "logs/**", "manifest.json", "*.zip"],
        "privacy_checks": privacy,
        "files": [
            {
                "path": path.relative_to(project).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in files
        ],
    }
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        prefix = project.name
        for path in files:
            archive.write(path, f"{prefix}/{path.relative_to(project).as_posix()}")
        archive.writestr(f"{prefix}/shareable_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a de-identified XHS research package")
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(package(args.project_dir, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

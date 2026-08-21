from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .config import write_yaml


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(payload: Any, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(target)
    return target


def read_json(path: str | Path, default: Any = None) -> Any:
    source = Path(path)
    return json.loads(source.read_text(encoding="utf-8")) if source.exists() else default


def write_jsonl(rows: Iterable[dict[str, Any]], path: str | Path, append: bool = False) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with target.open(mode, encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return target


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    rows = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def raw(self) -> Path: return self.root / "raw"
    @property
    def processed(self) -> Path: return self.root / "processed"
    @property
    def analysis(self) -> Path: return self.root / "analysis"
    @property
    def charts(self) -> Path: return self.root / "charts"
    @property
    def evidence(self) -> Path: return self.root / "evidence"
    @property
    def report(self) -> Path: return self.root / "report"
    @property
    def logs(self) -> Path: return self.root / "logs"

    def create(self) -> "ProjectPaths":
        for path in (self.root, self.raw, self.processed, self.analysis, self.charts, self.evidence, self.report, self.logs):
            path.mkdir(parents=True, exist_ok=True)
        return self

    def state(self, stage: str, status: str, detail: dict | None = None) -> None:
        payload = read_json(self.root / "state.json", {"stages": {}})
        payload["updated_at"] = now_iso()
        event = {"stage": stage, "status": status, "updated_at": now_iso(), "detail": detail or {}}
        payload.setdefault("stages", {})[stage] = {key: value for key, value in event.items() if key != "stage"}
        write_json(payload, self.root / "state.json")
        self.logs.mkdir(parents=True, exist_ok=True)
        with (self.logs / "run.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def save_config(self, config: dict[str, Any]) -> None:
        public = {key: value for key, value in config.items() if not key.startswith("_")}
        write_yaml(public, self.root / "project_config.yaml")


def write_parquet_or_csv(df: pd.DataFrame, parquet_path: Path) -> tuple[Path, list[str]]:
    warnings: list[str] = []
    try:
        df.to_parquet(parquet_path, index=False)
        return parquet_path, warnings
    except Exception as exc:
        fallback = parquet_path.with_suffix(".csv")
        df.to_csv(fallback, index=False, encoding="utf-8-sig")
        warnings.append(f"Parquet unavailable; wrote CSV fallback: {exc}")
        return fallback, warnings

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from ..storage import write_json


class AnalysisModule(ABC):
    name = "base"
    version = "1.0"

    def validate_input(self, data: pd.DataFrame, config: dict[str, Any]) -> None:
        if data.empty:
            raise ValueError(f"{self.name}: empty input")
        if "record_id" not in data or "clean_text" not in data:
            raise ValueError(f"{self.name}: record_id and clean_text are required")

    @abstractmethod
    def run(self, data: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def export(self, result: dict[str, Any], output_dir: Path) -> Path:
        return write_json(result, output_dir / f"{self.name}.json")

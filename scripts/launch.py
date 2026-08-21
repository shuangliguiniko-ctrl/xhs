#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "runtime" / "src"))

from userresearch_xhscrawler_cockpitux.cli import main

raise SystemExit(main())

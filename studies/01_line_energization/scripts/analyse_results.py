"""Analyse raw PowerFactory CSV files without consuming a PowerFactory licence."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from pfemt.config import load_yaml  # noqa: E402
from pfemt.workflows import analyse_sweep  # noqa: E402

configuration = load_yaml(REPOSITORY / "studies/01_line_energization/configs/base.yaml")
print(analyse_sweep(configuration))


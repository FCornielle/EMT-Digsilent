"""Run the declared EMT time-step sensitivity from a PowerFactory ComPython object."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from pfemt.application import connect  # noqa: E402
from pfemt.config import load_yaml  # noqa: E402
from pfemt.workflows import run_timestep_sensitivity  # noqa: E402

configuration = load_yaml(REPOSITORY / "studies/01_line_energization/configs/base.yaml")
configuration["connection"]["mode"] = "internal"
application = connect(configuration)
destination = run_timestep_sensitivity(configuration, app=application)
application.PrintPlain("PFEMT: time-step sensitivity exported to {}".format(destination))

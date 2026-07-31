"""Export the Study 02 linked diagram from an interactive PowerFactory session."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from pfemt.application import connect  # noqa: E402
from pfemt.config import load_yaml  # noqa: E402
from pfemt.workflows import export_diagram  # noqa: E402

configuration = load_yaml(REPOSITORY / "studies/02_hv_cable_energization/configs/base.yaml")
configuration["connection"]["mode"] = "internal"
application = connect(configuration)
destination = export_diagram(configuration, app=application)
application.PrintPlain("PFEMT: PowerFactory cable diagram exported to {}".format(destination))

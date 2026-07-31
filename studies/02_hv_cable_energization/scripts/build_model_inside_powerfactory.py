"""Build Study 02 from a PowerFactory ComPython object."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from pfemt.application import connect  # noqa: E402
from pfemt.config import load_yaml  # noqa: E402
from pfemt.workflows import build  # noqa: E402

configuration = load_yaml(REPOSITORY / "studies/02_hv_cable_energization/configs/base.yaml")
configuration["connection"]["mode"] = "internal"
application = connect(configuration)
objects = build(configuration, app=application)
application.PrintPlain(
    "PFEMT: explicit cable model ready in project {}".format(objects["project"].loc_name)
)
application.PrintPlain(
    "PFEMT: ElmCabsys {} couples {} and {}".format(
        objects["cable_system"].loc_name,
        objects["core_line"].loc_name,
        objects["sheath_line"].loc_name,
    )
)

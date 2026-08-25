"""PowerFactory API builder for breaker-TRV and variable-clearing studies."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from pfemt.builders.common import connect, create_or_activate_project, grid, study_case
from pfemt.diagram import ensure_study_diagram
from pfemt.pfapi import create_or_get, set_attribute


def _shunt(grid_model: Any, name: str, bus: Any, q_mvar: float, voltage_kv: float) -> Any:
    shunt = create_or_get(grid_model, "ElmShnt", name)
    set_attribute(shunt, "shtype", 2)
    set_attribute(shunt, "cgnd", 0)
    set_attribute(shunt, "ushnm", voltage_kv)
    set_attribute(shunt, "qcapn", q_mvar)
    set_attribute(shunt, "ncapx", 1)
    set_attribute(shunt, "ncapa", 1)
    connect(shunt, bus, "bus1", "CUB_{}".format(name))
    return shunt


def build_fault_network_model(app: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    """Build an idempotent grounded 230 kV source-breaker-impedance benchmark."""
    pf_config = config["powerfactory"]
    names = config["objects"]
    network = config["network"]
    project = create_or_activate_project(app, pf_config["project"], pf_config["grid"])
    grid_model = grid(app, pf_config["grid"])
    voltage_kv = float(network["nominal_voltage_kv"])
    buses = {
        key: create_or_get(grid_model, "ElmTerm", names[key])
        for key in ("source_bus", "load_bus", "fault_bus")
    }
    for bus in buses.values():
        set_attribute(bus, "uknom", voltage_kv)

    source = create_or_get(grid_model, "ElmXnet", names["source"])
    source_data = network["source"]
    set_attribute(source, "bustp", "SL", required=False)
    set_attribute(source, "usetp", float(source_data["voltage_pu"]))
    set_attribute(source, "snss", float(source_data["short_circuit_mva"]))
    set_attribute(source, "rntxn", float(source_data["r_over_x"]))
    set_attribute(source, "xntrn", float(source_data["x0_over_x1"]), required=False)
    set_attribute(source, "r0tx0", float(source_data["r0_over_x0"]), required=False)
    connect(source, buses["source_bus"], "bus1", "CUB_{}".format(names["source"]))

    breaker = create_or_get(grid_model, "ElmCoup", names["breaker"])
    set_attribute(breaker, "on_off", 1)
    set_attribute(breaker, "nphase", 3)
    connect(breaker, buses["source_bus"], "bus1", "CUB_{}_1".format(names["breaker"]))
    connect(breaker, buses["load_bus"], "bus2", "CUB_{}_2".format(names["breaker"]))

    impedance = create_or_get(grid_model, "ElmZpu", names["impedance"])
    impedance_data = network["impedance"]
    for attribute in ("Sn", "r_pu", "x_pu", "r0_pu", "x0_pu"):
        set_attribute(impedance, attribute, float(impedance_data[attribute]))
    set_attribute(impedance, "nphases", 3)
    connect(
        impedance,
        buses["load_bus"],
        "bus1",
        "CUB_{}_1".format(names["impedance"]),
    )
    connect(
        impedance,
        buses["fault_bus"],
        "bus2",
        "CUB_{}_2".format(names["impedance"]),
    )

    shunts: Dict[str, Any] = {}
    for key, bus_key, data_key in (
        ("source_capacitance", "source_bus", "source_capacitance_mvar"),
        ("load_capacitance", "load_bus", "load_capacitance_mvar"),
    ):
        if key in names and float(network.get(data_key, 0.0)) > 0.0:
            shunts[key] = _shunt(
                grid_model,
                names[key],
                buses[bus_key],
                float(network[data_key]),
                voltage_kv,
            )

    study = study_case(app, pf_config["study_case"])
    if not grid_model.IsCalcRelevant():
        grid_model.Activate()
    diagram = ensure_study_diagram(
        app,
        grid_model,
        config["diagram"]["name"],
        list(names.values()),
    )
    writer = getattr(project, "WriteChangesToDb", None)
    if callable(writer):
        writer()
    return {
        "project": project,
        "grid": grid_model,
        "source": source,
        "breaker": breaker,
        "impedance": impedance,
        "diagram": diagram,
        **buses,
        **shunts,
        **study,
    }

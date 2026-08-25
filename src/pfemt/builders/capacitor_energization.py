"""PowerFactory API builder for isolated and back-to-back capacitor switching."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping

from pfemt.builders.common import connect, create_or_activate_project, grid, study_case
from pfemt.diagram import ensure_study_diagram
from pfemt.pfapi import create_or_get, set_attribute


def _reactor_pu(config: Mapping[str, Any]) -> Dict[str, float]:
    network = config["network"]
    voltage_kv = float(network["nominal_voltage_kv"])
    power_mva = float(network["bank"]["reactive_power_mvar"])
    base_impedance = voltage_kv**2 / power_mva
    frequency_hz = float(network["frequency_hz"])
    reactor = network["reactor"]
    reactance = 2.0 * math.pi * frequency_hz * float(reactor["inductance_mh"]) * 1e-3
    return {
        "Sn": power_mva,
        "r_pu": float(reactor["resistance_ohm"]) / base_impedance,
        "x_pu": reactance / base_impedance,
        "r0_pu": float(reactor["resistance_ohm"]) / base_impedance,
        "x0_pu": reactance / base_impedance,
    }


def _bank(grid_model: Any, name: str, bus: Any, config: Mapping[str, Any]) -> Any:
    data = config["network"]["bank"]
    bank = create_or_get(grid_model, "ElmShnt", name)
    set_attribute(bank, "shtype", 2)
    set_attribute(bank, "cgnd", 0)
    set_attribute(bank, "ushnm", float(config["network"]["nominal_voltage_kv"]))
    set_attribute(bank, "qcapn", float(data["reactive_power_mvar"]))
    set_attribute(bank, "ncapx", int(data["number_of_steps"]))
    set_attribute(bank, "ncapa", int(data["number_of_steps"]))
    connect(bank, bus, "bus1", "CUB_{}".format(name))
    return bank


def build_capacitor_energization_model(
    app: Any, config: Mapping[str, Any]
) -> Dict[str, Any]:
    """Build the two-branch 230 kV capacitor-switching benchmark."""
    pf_config = config["powerfactory"]
    names = config["objects"]
    network = config["network"]
    project = create_or_activate_project(app, pf_config["project"], pf_config["grid"])
    grid_model = grid(app, pf_config["grid"])
    voltage_kv = float(network["nominal_voltage_kv"])

    buses = {
        key: create_or_get(grid_model, "ElmTerm", names[key])
        for key in ("main_bus", "feeder_bus_a", "bank_bus_a", "feeder_bus_b", "bank_bus_b")
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
    connect(source, buses["main_bus"], "bus1", "CUB_{}".format(names["source"]))

    reactor_values = _reactor_pu(config)
    branch_objects: Dict[str, Any] = {}
    for suffix in ("a", "b"):
        breaker = create_or_get(grid_model, "ElmCoup", names["breaker_" + suffix])
        set_attribute(breaker, "on_off", 0 if suffix == "a" else 1)
        set_attribute(breaker, "nphase", 3)
        connect(
            breaker,
            buses["main_bus"],
            "bus1",
            "CUB_{}_1".format(names["breaker_" + suffix]),
        )
        connect(
            breaker,
            buses["feeder_bus_" + suffix],
            "bus2",
            "CUB_{}_2".format(names["breaker_" + suffix]),
        )
        reactor = create_or_get(grid_model, "ElmZpu", names["reactor_" + suffix])
        for attribute, value in reactor_values.items():
            set_attribute(reactor, attribute, value)
        set_attribute(reactor, "nphases", 3)
        connect(
            reactor,
            buses["feeder_bus_" + suffix],
            "bus1",
            "CUB_{}_1".format(names["reactor_" + suffix]),
        )
        connect(
            reactor,
            buses["bank_bus_" + suffix],
            "bus2",
            "CUB_{}_2".format(names["reactor_" + suffix]),
        )
        bank = _bank(
            grid_model,
            names["bank_" + suffix],
            buses["bank_bus_" + suffix],
            config,
        )
        branch_objects["breaker_" + suffix] = breaker
        branch_objects["reactor_" + suffix] = reactor
        branch_objects["bank_" + suffix] = bank

    study = study_case(app, pf_config["study_case"])
    if not grid_model.IsCalcRelevant():
        grid_model.Activate()
    expected_names = list(names.values())
    diagram = ensure_study_diagram(
        app,
        grid_model,
        "EMT Capacitor Switching 230 kV",
        expected_names,
    )
    writer = getattr(project, "WriteChangesToDb", None)
    if callable(writer):
        writer()
    return {
        "project": project,
        "grid": grid_model,
        "source": source,
        "diagram": diagram,
        **buses,
        **branch_objects,
        **study,
    }

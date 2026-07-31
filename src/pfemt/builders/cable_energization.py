"""API builder for the 220 kV explicit-sheath cable benchmark."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from pfemt.builders.common import connect, create_or_activate_project, grid, study_case
from pfemt.cable import cable_geometry
from pfemt.diagram import ensure_cable_energization_diagram
from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import create_or_get, set_attribute


def _cable_type(app: Any, config: Mapping[str, Any]) -> Any:
    """Create the catalogue-derived ``TypCab`` layer model."""
    network = config["network"]
    cable = network["cable"]
    raw_geometry = cable["geometry"]
    conductor = raw_geometry["conductor"]
    main_insulation = raw_geometry["main_insulation"]
    sheath = raw_geometry["sheath"]
    oversheath = raw_geometry["oversheath"]
    derived = cable_geometry(config)

    folder = app.GetProjectFolder("equip", 1)
    cable_type = create_or_get(folder, "TypCab", cable["type_name"])
    scalar_values = {
        "uline": float(network["nominal_voltage_kv"]),
        "typCon": "Compact",
        "diaCon": derived.conductor_diameter_mm,
        "diaTube": 0.0,
        "has_sht": 1,
        "has_arm": 0,
        "has_ins2": 1,
        "has_ins3": 0,
        "has_scco": 0,
        "has_scio": 0,
        # PowerFactory option 0 selects a solid sheath defined by thickness.
        "iShtScreen": 0,
        "thSht": derived.sheath_thickness_mm,
        "As": derived.sheath_area_mm2,
        "tmax": 90.0,
    }
    vector_values = {
        # Fixed order in TypCab: core, sheath, armour.
        "rho": [
            float(conductor["resistivity_uohm_cm_20c"]),
            float(sheath["resistivity_uohm_cm_20c"]),
            1.77,
        ],
        "my": [1.0, 1.0, 1.0],
        "Cf": [derived.conductor_fill_factor_pct, 100.0, 100.0],
        "ralpha": [
            float(conductor["temperature_coefficient_per_k"]),
            float(sheath["temperature_coefficient_per_k"]),
            0.00382,
        ],
        # Fixed order in TypCab: main insulation, oversheath, serving.
        "thIns": [
            derived.effective_main_insulation_thickness_mm,
            derived.oversheath_thickness_mm,
            # PowerFactory validates all fixed vector slots even when the
            # corresponding third layer is disabled.
            1.0,
        ],
        "epsr": [
            derived.main_insulation_relative_permittivity,
            float(oversheath["relative_permittivity"]),
            1.0,
        ],
        "tand": [
            float(main_insulation["loss_tangent"]),
            float(oversheath["loss_tangent"]),
            0.0,
        ],
    }
    for name, value in {**scalar_values, **vector_values}.items():
        set_attribute(cable_type, name, value)
    set_attribute(
        cable_type,
        "desc",
        [
            "Catalogue-derived teaching model: {}".format(raw_geometry["source_id"]),
            "Effective insulation thickness preserves diameter over insulation; ",
            "relative permittivity is calibrated to catalogue capacitance.",
        ],
        required=False,
    )
    return cable_type


def _cable_system_type(app: Any, config: Mapping[str, Any], cable_type: Any) -> Any:
    """Create the three-phase flat-formation ``TypCabsys`` definition."""
    network = config["network"]
    cable = network["cable"]
    spacing = float(cable["phase_spacing_m"])
    depth = float(cable["burial_depth_m"])
    folder = app.GetProjectFolder("equip", 1)
    system_type = create_or_get(folder, "TypCabsys", cable["system_type_name"])
    values = {
        "iopt_bur": "gnd",
        "systp": 0,
        "nlcir": 1,
        "rhoEarth": float(cable["soil_resistivity_ohm_m"]),
        "frnom": float(network["frequency_hz"]),
        "nphas": [3.0],
        "dInom": [float(cable["rated_current_ka"])],
        # Keep sheath conductors explicit; bonding is applied by each scenario.
        "red": [0.0],
        "bond": [0.0],
        "xy_c": [[-spacing, 0.0, spacing, depth, depth, depth]],
        "pcab_c": [cable_type],
    }
    for name, value in values.items():
        set_attribute(system_type, name, value)
    return system_type


def _fit_cable_system(cable_system: Any, config: Mapping[str, Any]) -> None:
    """Configure and calculate the frequency-dependent EMT representation."""
    emt = config["network"]["cable"]["emt_model"]
    for name, value in {
        "i_dist": 1,
        "i_model": 1,
        "fd_model": 1,
        "fmin": float(emt["fit_frequency_min_hz"]),
        "fmax": float(emt["fit_frequency_max_hz"]),
        "ftau": float(emt["main_transient_frequency_hz"]),
    }.items():
        set_attribute(cable_system, name, value)
    signature = _fit_signature(config)
    get_attribute = getattr(cable_system, "GetAttribute", None)
    descriptions = list(get_attribute("desc") or []) if callable(get_attribute) else []
    signature_line = "PFEMT_FIT_SHA256={}".format(signature)
    if signature_line in descriptions:
        return
    update = getattr(cable_system, "Update", None)
    if callable(update):
        update_code = update()
        if update_code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Cable-system update failed with return code {}".format(update_code)
            )
    fit = getattr(cable_system, "FitParams", None)
    if not callable(fit):
        raise PowerFactoryExecutionError("ElmCabsys does not expose FitParams()")
    fit_code = fit()
    if fit_code not in (None, 0):
        raise PowerFactoryExecutionError(
            "Frequency-dependent cable fitting failed with return code {}".format(fit_code)
        )
    set_attribute(
        cable_system,
        "desc",
        [
            signature_line,
            "Frequency-dependent parameters fitted by the Study 02 API builder.",
        ],
        required=False,
    )


def _fit_signature(config: Mapping[str, Any]) -> str:
    """Fingerprint every cable input that can invalidate fitted EMT parameters."""
    payload = {
        "nominal_voltage_kv": config["network"]["nominal_voltage_kv"],
        "frequency_hz": config["network"]["frequency_hz"],
        "cable": config["network"]["cable"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def build_cable_energization_model(app: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    """Build or update the explicit-core/screen network and EMT Study Case."""
    pf_config = config["powerfactory"]
    names = config["objects"]
    network = config["network"]
    source_data = network["source"]
    cable_data = network["cable"]

    project = create_or_activate_project(app, pf_config["project"], pf_config["grid"])
    grid_model = grid(app, pf_config["grid"])
    cable_type = _cable_type(app, config)
    cable_system_type = _cable_system_type(app, config, cable_type)

    sending = create_or_get(grid_model, "ElmTerm", names["sending_bus"])
    cable_side = create_or_get(grid_model, "ElmTerm", names["cable_bus"])
    receiving = create_or_get(grid_model, "ElmTerm", names["receiving_bus"])
    sheath_sending = create_or_get(grid_model, "ElmTerm", names["sheath_sending_bus"])
    sheath_receiving = create_or_get(grid_model, "ElmTerm", names["sheath_receiving_bus"])
    for terminal in (sending, cable_side, receiving, sheath_sending, sheath_receiving):
        set_attribute(terminal, "uknom", float(network["nominal_voltage_kv"]))

    source = create_or_get(grid_model, "ElmXnet", names["source"])
    set_attribute(source, "bustp", "SL", required=False)
    set_attribute(source, "usetp", float(source_data["voltage_pu"]))
    set_attribute(source, "snss", float(source_data["short_circuit_mva"]))
    set_attribute(source, "rntxn", float(source_data["r_over_x"]))
    connect(source, sending, "bus1", "CUB_{}".format(names["source"]))

    breaker = create_or_get(grid_model, "ElmCoup", names["breaker"])
    set_attribute(breaker, "on_off", 0)
    connect(breaker, sending, "bus1", "CUB_{}_1".format(names["breaker"]))
    connect(breaker, cable_side, "bus2", "CUB_{}_2".format(names["breaker"]))

    core_line = create_or_get(grid_model, "ElmLne", names["core_line"])
    sheath_line = create_or_get(grid_model, "ElmLne", names["sheath_line"])
    for line in (core_line, sheath_line):
        set_attribute(line, "dline", float(cable_data["length_km"]))
    connect(core_line, cable_side, "bus1", "CUB_{}_1".format(names["core_line"]))
    connect(core_line, receiving, "bus2", "CUB_{}_2".format(names["core_line"]))
    connect(
        sheath_line,
        sheath_sending,
        "bus1",
        "CUB_{}_1".format(names["sheath_line"]),
    )
    connect(
        sheath_line,
        sheath_receiving,
        "bus2",
        "CUB_{}_2".format(names["sheath_line"]),
    )

    cable_system = create_or_get(grid_model, "ElmCabsys", names["cable_system"])
    set_attribute(cable_system, "typ_id", cable_system_type)
    # The ordering is the one requested by PowerFactory's bonding tutorial:
    # the selected core line first, followed by its explicit sheath line.
    set_attribute(cable_system, "plines", [core_line, sheath_line])
    _fit_cable_system(cable_system, config)

    study = study_case(app, pf_config["study_case"])
    if not grid_model.IsCalcRelevant():
        grid_code = grid_model.Activate()
        if grid_code not in (None, 0):
            raise PowerFactoryExecutionError(
                "Could not activate grid {!r} in Study Case {!r}".format(
                    pf_config["grid"], pf_config["study_case"]
                )
            )
    diagram = ensure_cable_energization_diagram(app, grid_model)
    writer = getattr(project, "WriteChangesToDb", None)
    if callable(writer):
        writer()
    return {
        "project": project,
        "grid": grid_model,
        "sending_bus": sending,
        "cable_bus": cable_side,
        "receiving_bus": receiving,
        "sheath_sending_bus": sheath_sending,
        "sheath_receiving_bus": sheath_receiving,
        "source": source,
        "breaker": breaker,
        "core_line": core_line,
        "sheath_line": sheath_line,
        "cable_system": cable_system,
        "cable_type": cable_type,
        "cable_system_type": cable_system_type,
        "diagram": diagram,
        **study,
    }

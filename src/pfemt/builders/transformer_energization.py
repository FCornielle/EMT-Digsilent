"""PowerFactory API builder for transformer energization and inrush studies."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from pfemt.builders.common import connect, create_or_activate_project, grid, study_case
from pfemt.diagram import ensure_study_diagram
from pfemt.pfapi import create_or_get, set_attribute


def _transformer_type(app: Any, config: Mapping[str, Any]) -> Any:
    network = config["network"]
    data = network["transformer"]
    transformer_type = create_or_get(
        app.GetProjectFolder("equip", 1),
        "TypTr2",
        data["type_name"],
    )
    values = {
        "strn": float(data["rated_power_mva"]),
        "utrn_h": float(data["hv_voltage_kv"]),
        "utrn_l": float(data["lv_voltage_kv"]),
        "uktr": float(data["short_circuit_voltage_pct"]),
        "pcutr": float(data["copper_losses_kw"]),
        "curmg": float(data["no_load_current_pct"]),
        "pfe": float(data["no_load_losses_kw"]),
        "frnom": float(network["frequency_hz"]),
        "tr2cn_h": str(data["vector_group_hv"]),
        "tr2cn_l": str(data["vector_group_lv"]),
        "itrmt": int(data["saturation"]["model_type_code"]),
        "iLimb": int(data["saturation"]["core_limb_model"]),
        "iHyster": int(data["saturation"]["hysteresis_model"]),
        "iFit": int(data["saturation"]["fit_model"]),
        "iFinalSlope": 1,
        "cknee": float(data["saturation"]["knee_current_pu"]),
        "psi0": float(data["saturation"]["knee_flux_pu"]),
        "xmair": float(data["saturation"]["air_core_reactance_pu"]),
        "ksat": int(data["saturation"]["saturation_exponent"]),
    }
    for name, value in values.items():
        set_attribute(transformer_type, name, value)
    return transformer_type


def build_transformer_energization_model(
    app: Any, config: Mapping[str, Any]
) -> Dict[str, Any]:
    """Build the unloaded HV/MV transformer energization benchmark."""
    pf_config = config["powerfactory"]
    names = config["objects"]
    network = config["network"]
    source_data = network["source"]
    transformer_data = network["transformer"]
    project = create_or_activate_project(app, pf_config["project"], pf_config["grid"])
    grid_model = grid(app, pf_config["grid"])
    transformer_type = _transformer_type(app, config)

    source_bus = create_or_get(grid_model, "ElmTerm", names["source_bus"])
    transformer_hv_bus = create_or_get(
        grid_model, "ElmTerm", names["transformer_hv_bus"]
    )
    transformer_lv_bus = create_or_get(
        grid_model, "ElmTerm", names["transformer_lv_bus"]
    )
    set_attribute(source_bus, "uknom", float(transformer_data["hv_voltage_kv"]))
    set_attribute(transformer_hv_bus, "uknom", float(transformer_data["hv_voltage_kv"]))
    set_attribute(transformer_lv_bus, "uknom", float(transformer_data["lv_voltage_kv"]))

    source = create_or_get(grid_model, "ElmXnet", names["source"])
    set_attribute(source, "bustp", "SL", required=False)
    set_attribute(source, "usetp", float(source_data["voltage_pu"]))
    set_attribute(source, "snss", float(source_data["short_circuit_mva"]))
    set_attribute(source, "rntxn", float(source_data["r_over_x"]))
    set_attribute(source, "xntrn", float(source_data.get("x0_over_x1", 1.0)), required=False)
    set_attribute(source, "r0tx0", float(source_data.get("r0_over_x0", 0.1)), required=False)
    connect(source, source_bus, "bus1", "CUB_{}".format(names["source"]))

    breaker = create_or_get(grid_model, "ElmCoup", names["breaker"])
    set_attribute(breaker, "on_off", 0)
    set_attribute(breaker, "nphase", 3)
    connect(breaker, source_bus, "bus1", "CUB_{}_1".format(names["breaker"]))
    connect(
        breaker,
        transformer_hv_bus,
        "bus2",
        "CUB_{}_2".format(names["breaker"]),
    )

    transformer = create_or_get(grid_model, "ElmTr2", names["transformer"])
    set_attribute(transformer, "typ_id", transformer_type)
    set_attribute(transformer, "iAstabint", 1)
    set_attribute(transformer, "iResFlux", 1)
    set_attribute(transformer, "PsiresA", 0.0)
    set_attribute(transformer, "PsiresB", 0.0)
    set_attribute(transformer, "PsiresC", 0.0)
    connect(
        transformer,
        transformer_hv_bus,
        "bushv",
        "CUB_{}_HV".format(names["transformer"]),
    )
    connect(
        transformer,
        transformer_lv_bus,
        "buslv",
        "CUB_{}_LV".format(names["transformer"]),
    )

    study = study_case(app, pf_config["study_case"])
    if not grid_model.IsCalcRelevant():
        grid_model.Activate()
    diagram = ensure_study_diagram(
        app,
        grid_model,
        "EMT Transformer Energization 230-34.5 kV",
        [
            names["source"],
            names["source_bus"],
            names["breaker"],
            names["transformer_hv_bus"],
            names["transformer"],
            names["transformer_lv_bus"],
        ],
    )
    writer = getattr(project, "WriteChangesToDb", None)
    if callable(writer):
        writer()
    return {
        "project": project,
        "grid": grid_model,
        "source": source,
        "source_bus": source_bus,
        "breaker": breaker,
        "transformer_hv_bus": transformer_hv_bus,
        "transformer": transformer,
        "transformer_type": transformer_type,
        "transformer_lv_bus": transformer_lv_bus,
        "diagram": diagram,
        **study,
    }

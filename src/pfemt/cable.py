"""Engineering calculations for the HV cable energization study."""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

import numpy as np
import pandas as pd

from pfemt.errors import ConfigurationError
from pfemt.scenarios import switching_time


@dataclass(frozen=True)
class CableScenario:
    """One deterministic cable-bonding and point-on-wave EMT scenario."""

    scenario_id: str
    bonding_id: str
    bonding_label: str
    switching_angle_deg: float
    switching_time_s: float
    grounded_sending: bool
    grounded_receiving: bool
    cross_bonded: bool
    source_voltage_pu: float
    cable_length_km: float


@dataclass(frozen=True)
class CableGeometry:
    """Validated single-core dimensions derived from a catalogue data row."""

    conductor_area_mm2: float
    conductor_diameter_mm: float
    conductor_fill_factor_pct: float
    nominal_main_insulation_thickness_mm: float
    effective_main_insulation_thickness_mm: float
    main_insulation_relative_permittivity: float
    sheath_thickness_mm: float
    sheath_area_mm2: float
    oversheath_thickness_mm: float
    overall_diameter_mm: float


def cable_geometry(config: Mapping[str, object]) -> CableGeometry:
    """Derive the PowerFactory layer geometry and validate radial consistency.

    The effective insulation thickness follows DIgSILENT's cable-parameter
    tutorial: when semiconducting-layer dimensions are unavailable, preserve
    the catalogue diameter over insulation. The relative permittivity is then
    calibrated to the declared catalogue capacitance using the coaxial first-
    order expression. PowerFactory remains responsible for the final coupled
    phase-domain parameter calculation.
    """
    cable = config["network"]["cable"]  # type: ignore[index]
    geometry = cable["geometry"]  # type: ignore[index]
    conductor = geometry["conductor"]  # type: ignore[index]
    insulation = geometry["main_insulation"]  # type: ignore[index]
    sheath = geometry["sheath"]  # type: ignore[index]

    area = float(conductor["area_mm2"])  # type: ignore[index]
    conductor_diameter = float(conductor["diameter_mm"])  # type: ignore[index]
    nominal_insulation = float(insulation["nominal_thickness_mm"])  # type: ignore[index]
    diameter_over_insulation = float(geometry["diameter_over_insulation_mm"])  # type: ignore[index]
    sheath_thickness = float(sheath["thickness_mm"])  # type: ignore[index]
    overall_diameter = float(geometry["overall_diameter_mm"])  # type: ignore[index]
    capacitance_uf_per_km = float(
        insulation["capacitance_target_uf_per_km"]  # type: ignore[index]
    )
    inputs = {
        "conductor area": area,
        "conductor diameter": conductor_diameter,
        "nominal insulation thickness": nominal_insulation,
        "diameter over insulation": diameter_over_insulation,
        "sheath thickness": sheath_thickness,
        "overall diameter": overall_diameter,
        "capacitance target": capacitance_uf_per_km,
    }
    invalid = [name for name, value in inputs.items() if value <= 0.0]
    if invalid:
        raise ConfigurationError(
            "Cable geometry values must be positive: {}".format(", ".join(invalid))
        )
    if diameter_over_insulation <= conductor_diameter:
        raise ConfigurationError("Diameter over insulation must exceed conductor diameter")
    if overall_diameter <= diameter_over_insulation + 2.0 * sheath_thickness:
        raise ConfigurationError(
            "Overall cable diameter leaves no positive oversheath thickness"
        )

    effective_insulation = (diameter_over_insulation - conductor_diameter) / 2.0
    oversheath = (
        overall_diameter - diameter_over_insulation - 2.0 * sheath_thickness
    ) / 2.0
    fill_factor = area / (math.pi * conductor_diameter**2 / 4.0) * 100.0
    if fill_factor > 100.0:
        raise ConfigurationError(
            "Conductor area exceeds the solid area implied by its diameter"
        )
    conductor_radius_m = conductor_diameter * 0.5e-3
    insulation_outer_radius_m = diameter_over_insulation * 0.5e-3
    capacitance_f_per_m = capacitance_uf_per_km * 1e-9
    vacuum_permittivity_f_per_m = 8.8541878128e-12
    relative_permittivity = (
        capacitance_f_per_m
        * math.log(insulation_outer_radius_m / conductor_radius_m)
        / (2.0 * math.pi * vacuum_permittivity_f_per_m)
    )
    sheath_inner_radius = diameter_over_insulation / 2.0
    sheath_area = math.pi * (
        (sheath_inner_radius + sheath_thickness) ** 2 - sheath_inner_radius**2
    )
    return CableGeometry(
        conductor_area_mm2=area,
        conductor_diameter_mm=conductor_diameter,
        conductor_fill_factor_pct=fill_factor,
        nominal_main_insulation_thickness_mm=nominal_insulation,
        effective_main_insulation_thickness_mm=effective_insulation,
        main_insulation_relative_permittivity=relative_permittivity,
        sheath_thickness_mm=sheath_thickness,
        sheath_area_mm2=sheath_area,
        oversheath_thickness_mm=oversheath,
        overall_diameter_mm=overall_diameter,
    )


def cable_derived_quantities(config: Mapping[str, object]) -> Dict[str, float]:
    """Calculate transparent first-order cable quantities from the study basis."""
    network = config["network"]  # type: ignore[index]
    cable = network["cable"]  # type: ignore[index]
    electrical = cable["electrical"]  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    length_km = float(cable["length_km"])  # type: ignore[index]
    voltage_ll_kv = float(network["nominal_voltage_kv"])  # type: ignore[index]
    capacitance_uf_per_km = float(electrical["capacitance_uf_per_km"])  # type: ignore[index]
    inductance_mh_per_km = float(electrical["inductance_mh_per_km"])  # type: ignore[index]

    capacitance_f_per_km = capacitance_uf_per_km * 1e-6
    inductance_h_per_km = inductance_mh_per_km * 1e-3
    total_capacitance_uf = capacitance_uf_per_km * length_km
    phase_voltage_rms_kv = voltage_ll_kv / np.sqrt(3.0)
    angular_frequency = 2.0 * np.pi * frequency_hz
    charging_current_ka = (
        angular_frequency * total_capacitance_uf * 1e-6 * phase_voltage_rms_kv
    )
    stored_energy_kj = (
        3.0
        * total_capacitance_uf
        * 1e-6
        * (phase_voltage_rms_kv * 1e3) ** 2
        / 1e3
    )
    surge_impedance_ohm = float(np.sqrt(inductance_h_per_km / capacitance_f_per_km))
    propagation_velocity_km_per_s = float(
        1.0 / np.sqrt(inductance_h_per_km * capacitance_f_per_km)
    )
    return {
        "phase_voltage_rms_kv": float(phase_voltage_rms_kv),
        "total_capacitance_uf_per_phase": total_capacitance_uf,
        "steady_state_charging_current_ka": float(charging_current_ka),
        "three_phase_stored_energy_kj": float(stored_energy_kj),
        "surge_impedance_ohm": surge_impedance_ohm,
        "propagation_velocity_km_per_s": propagation_velocity_km_per_s,
        "one_way_travel_time_ms": length_km / propagation_velocity_km_per_s * 1e3,
        "samples_per_travel_time": (
            length_km
            / propagation_velocity_km_per_s
            / float(config["simulation"]["step_s"])  # type: ignore[index]
        ),
    }


def cable_length_sensitivity(
    config: Mapping[str, object],
    lengths_km: np.ndarray | None = None,
) -> pd.DataFrame:
    """Return analytical charging current and stored energy versus cable length."""
    cable = config["network"]["cable"]  # type: ignore[index]
    study_lengths = (
        np.asarray(lengths_km, dtype=float)
        if lengths_km is not None
        else np.linspace(5.0, 80.0, 31)
    )
    rows = []
    for length_km in study_lengths:
        if length_km <= 0.0:
            raise ConfigurationError("Cable sensitivity lengths must be positive")
        variant = {
            **config,
            "network": {
                **config["network"],  # type: ignore[index]
                "cable": {**cable, "length_km": float(length_km)},
            },
        }
        derived = cable_derived_quantities(variant)
        rows.append(
            {
                "length_km": float(length_km),
                "charging_current_ka": derived["steady_state_charging_current_ka"],
                "stored_energy_kj": derived["three_phase_stored_energy_kj"],
                "travel_time_ms": derived["one_way_travel_time_ms"],
            }
        )
    return pd.DataFrame(rows)


def cable_bonding_cases(config: Mapping[str, object]) -> List[Dict[str, object]]:
    """Validate and normalize the declared metallic-screen bonding cases."""
    required = ("grounded_sending", "grounded_receiving", "cross_bonded")
    normalized = []
    for item in config["bonding_cases"]:  # type: ignore[index]
        missing = [key for key in ("id", "label", *required) if key not in item]
        if missing:
            raise ConfigurationError(
                "Bonding case is missing required fields: {}".format(", ".join(missing))
            )
        normalized.append(
            {
                "id": str(item["id"]),
                "label": str(item["label"]),
                **{key: bool(item[key]) for key in required},
            }
        )
    if len({item["id"] for item in normalized}) != len(normalized):
        raise ConfigurationError("Bonding case identifiers must be unique")
    return normalized


def cable_scenarios(config: Mapping[str, object]) -> List[CableScenario]:
    """Expand bonding topologies and switching angles into an auditable campaign."""
    network = config["network"]  # type: ignore[index]
    sweep = config["sweep"]  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    if frequency_hz <= 0.0:
        raise ConfigurationError("network.frequency_hz must be positive")
    base_time_s = float(sweep["base_switching_time_s"])  # type: ignore[index]
    raw_angles = [float(value) for value in sweep["angles_deg"]]  # type: ignore[index]
    angles = [value % 360.0 for value in raw_angles]
    if not angles:
        raise ConfigurationError("sweep.angles_deg must contain at least one angle")
    if len(set(angles)) != len(angles):
        raise ConfigurationError("Switching angles must be unique modulo 360 degrees")

    cable = network["cable"]  # type: ignore[index]
    source = network["source"]  # type: ignore[index]
    scenarios = []
    for bonding in cable_bonding_cases(config):
        for angle in angles:
            angle_token = (
                "{:03d}".format(int(angle))
                if angle.is_integer()
                else "{:07.3f}".format(angle).rstrip("0").rstrip(".").replace(".", "p")
            )
            scenarios.append(
                CableScenario(
                    scenario_id="{}_pow_{}deg".format(bonding["id"], angle_token),
                    bonding_id=str(bonding["id"]),
                    bonding_label=str(bonding["label"]),
                    switching_angle_deg=angle,
                    switching_time_s=switching_time(base_time_s, angle, frequency_hz),
                    grounded_sending=bool(bonding["grounded_sending"]),
                    grounded_receiving=bool(bonding["grounded_receiving"]),
                    cross_bonded=bool(bonding["cross_bonded"]),
                    source_voltage_pu=float(source["voltage_pu"]),
                    cable_length_km=float(cable["length_km"]),
                )
            )
    return scenarios


def export_cable_scenario_manifest(
    scenarios: Iterable[CableScenario], destination: Path
) -> Path:
    """Write the cable scenario campaign as a stable, reviewable CSV manifest."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(scenario) for scenario in scenarios]
    fieldnames = list(CableScenario.__dataclass_fields__.keys())
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output

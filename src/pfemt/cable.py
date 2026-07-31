"""Engineering calculations for the HV cable energization study."""

from __future__ import annotations

from typing import Dict, List, Mapping

import numpy as np
import pandas as pd

from pfemt.errors import ConfigurationError


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

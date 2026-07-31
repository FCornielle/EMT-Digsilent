"""Engineering metrics for EMT switching studies."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from pfemt.errors import ResultFormatError


def _peak(frame: pd.DataFrame, columns: Sequence[str], prefix: str) -> Dict[str, float]:
    values = frame[list(columns)].to_numpy(dtype=float)
    absolute = np.abs(values)
    row, phase = np.unravel_index(int(np.argmax(absolute)), absolute.shape)
    return {
        "{}_peak".format(prefix): float(absolute[row, phase]),
        "{}_peak_signed".format(prefix): float(values[row, phase]),
        "{}_peak_time_s".format(prefix): float(frame["time_s"].iloc[row]),
        "{}_peak_phase".format(prefix): str(columns[phase]),
    }


def line_energization_metrics(
    frame: pd.DataFrame,
    nominal_voltage_kv_ll_rms: float,
    switching_time_s: float,
    voltage_columns: Sequence[str] = ("v_recv_a_kv", "v_recv_b_kv", "v_recv_c_kv"),
    current_columns: Sequence[str] = ("i_send_a_ka", "i_send_b_ka", "i_send_c_ka"),
) -> Dict[str, object]:
    """Calculate phase-ground peak overvoltage and closing-current peak."""
    required = ["time_s", *voltage_columns, *current_columns]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ResultFormatError("Normalized data are missing columns: {}".format(missing))
    post = frame.loc[frame["time_s"] >= float(switching_time_s)].copy()
    if post.empty:
        raise ResultFormatError("No samples exist at or after the switching event")

    voltage = _peak(post, voltage_columns, "voltage_kv")
    current = _peak(post, current_columns, "current_ka")
    nominal_phase_peak_kv = float(nominal_voltage_kv_ll_rms) * np.sqrt(2.0 / 3.0)
    voltage["voltage_peak_pu"] = voltage["voltage_kv_peak"] / nominal_phase_peak_kv
    return {
        "switching_time_s": float(switching_time_s),
        "nominal_voltage_kv_ll_rms": float(nominal_voltage_kv_ll_rms),
        "nominal_phase_peak_kv": float(nominal_phase_peak_kv),
        **voltage,
        **current,
    }


def line_energization_derived_quantities(config: Mapping[str, object]) -> Dict[str, float]:
    """Calculate first-order travelling-wave checks from positive-sequence inputs."""
    network = config["network"]  # type: ignore[index]
    line = network["line"]  # type: ignore[index]
    parameters = line["sequence_parameters"]  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    angular_frequency = 2.0 * np.pi * frequency_hz
    inductance_h_per_km = float(parameters["x1_ohm_per_km"]) / angular_frequency  # type: ignore[index]
    capacitance_f_per_km = (
        float(parameters["b1_us_per_km"]) * 1e-6 / angular_frequency  # type: ignore[index]
    )
    surge_impedance_ohm = float(np.sqrt(inductance_h_per_km / capacitance_f_per_km))
    propagation_velocity_km_per_s = float(
        1.0 / np.sqrt(inductance_h_per_km * capacitance_f_per_km)
    )
    travel_time_s = float(line["length_km"]) / propagation_velocity_km_per_s  # type: ignore[index]
    nominal_phase_peak_kv = float(network["nominal_voltage_kv"]) * np.sqrt(2.0 / 3.0)  # type: ignore[index]
    surge_current_estimate_ka = nominal_phase_peak_kv / surge_impedance_ohm
    return {
        "positive_sequence_inductance_mh_per_km": inductance_h_per_km * 1e3,
        "positive_sequence_capacitance_nf_per_km": capacitance_f_per_km * 1e9,
        "surge_impedance_ohm": surge_impedance_ohm,
        "propagation_velocity_km_per_s": propagation_velocity_km_per_s,
        "one_way_travel_time_ms": travel_time_s * 1e3,
        "nominal_phase_peak_kv": nominal_phase_peak_kv,
        "first_order_surge_current_ka": surge_current_estimate_ka,
        "ideal_open_end_step_pu": 2.0,
    }


def compare_sweep_to_baseline(
    summary: pd.DataFrame,
    baseline: Mapping[str, object],
) -> Dict[str, object]:
    """Compare calculated sweep extrema with the versioned reference tolerances."""
    if summary.empty:
        raise ResultFormatError("Cannot compare an empty sweep summary")
    expected = baseline["results"]  # type: ignore[index]
    tolerances = baseline["tolerances"]  # type: ignore[index]
    actual_voltage = float(summary["voltage_peak_pu"].max())
    actual_current = float(summary["current_ka_peak"].max())
    expected_voltage = float(expected["worst_voltage_peak_pu"])  # type: ignore[index]
    expected_current = float(expected["maximum_closing_current_ka_peak"])  # type: ignore[index]
    voltage_error = abs(actual_voltage - expected_voltage) / expected_voltage
    current_error = abs(actual_current - expected_current) / expected_current
    voltage_tolerance = float(tolerances["voltage_peak_relative"])  # type: ignore[index]
    current_tolerance = float(tolerances["current_peak_relative"])  # type: ignore[index]
    return {
        "status": "pass"
        if voltage_error <= voltage_tolerance and current_error <= current_tolerance
        else "fail",
        "voltage": {
            "actual_peak_pu": actual_voltage,
            "expected_peak_pu": expected_voltage,
            "relative_error": voltage_error,
            "relative_tolerance": voltage_tolerance,
            "within_tolerance": voltage_error <= voltage_tolerance,
        },
        "current": {
            "actual_peak_ka": actual_current,
            "expected_peak_ka": expected_current,
            "relative_error": current_error,
            "relative_tolerance": current_tolerance,
            "within_tolerance": current_error <= current_tolerance,
        },
    }


def worst_case(
    rows: Iterable[Mapping[str, object]],
    metric: str = "voltage_peak_pu",
) -> Mapping[str, object]:
    """Return the scenario with the largest selected metric."""
    materialized = list(rows)
    if not materialized:
        raise ResultFormatError("Cannot rank an empty scenario set")
    return max(materialized, key=lambda row: float(row[metric]))

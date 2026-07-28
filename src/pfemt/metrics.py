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


def worst_case(
    rows: Iterable[Mapping[str, object]],
    metric: str = "voltage_peak_pu",
) -> Mapping[str, object]:
    """Return the scenario with the largest selected metric."""
    materialized = list(rows)
    if not materialized:
        raise ResultFormatError("Cannot rank an empty scenario set")
    return max(materialized, key=lambda row: float(row[metric]))


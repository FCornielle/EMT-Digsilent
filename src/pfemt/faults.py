"""Scenario generation and engineering KPIs for EMT fault studies."""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

import numpy as np
import pandas as pd

from pfemt.errors import ResultFormatError


@dataclass(frozen=True)
class FaultScenario:
    """One short-circuit type and clearing-time combination."""

    scenario_id: str
    fault_id: str
    fault_label: str
    fault_type_code: int
    phase_selector: int
    fault_time_s: float
    clearing_time_s: float


def fault_scenarios(config: Mapping[str, object]) -> List[FaultScenario]:
    """Expand the configured fault-type and clearing-time matrix."""
    sweep = config["sweep"]  # type: ignore[index]
    fault_time = float(sweep["fault_time_s"])  # type: ignore[index]
    scenarios: List[FaultScenario] = []
    for fault in sweep["fault_types"]:  # type: ignore[index]
        for clearing_time in sweep["clearing_times_s"]:  # type: ignore[index]
            duration_ms = (float(clearing_time) - fault_time) * 1000.0
            fault_id = str(fault["id"])
            scenarios.append(
                FaultScenario(
                    scenario_id="{}_{:.0f}ms".format(fault_id, duration_ms),
                    fault_id=fault_id,
                    fault_label=str(fault["label"]),
                    fault_type_code=int(fault["code"]),
                    phase_selector=int(fault.get("phase_selector", 0)),
                    fault_time_s=fault_time,
                    clearing_time_s=float(clearing_time),
                )
            )
    return scenarios


def export_fault_manifest(scenarios: Iterable[FaultScenario], destination: Path) -> Path:
    """Write the deterministic EMT fault campaign."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(item) for item in scenarios]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(FaultScenario.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(rows)
    return output


def _ordered(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop repeated PowerFactory event instants before numerical operations."""
    return frame.sort_values("time_s").drop_duplicates("time_s", keep="last")


def _require(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame]
    if missing:
        raise ResultFormatError("Fault data are missing columns: {}".format(missing))


def fault_metrics(
    frame: pd.DataFrame,
    scenario: FaultScenario,
    config: Mapping[str, object],
) -> Dict[str, float]:
    """Calculate peak, first-cycle RMS, I-squared-t, sag, and recovery KPIs."""
    current_columns = ["i_a_ka", "i_b_ka", "i_c_ka"]
    voltage_columns = ["v_fault_a_kv", "v_fault_b_kv", "v_fault_c_kv"]
    recovery_columns = ["v_source_a_kv", "v_source_b_kv", "v_source_c_kv"]
    _require(frame, ["time_s", *current_columns, *voltage_columns, *recovery_columns])
    ordered = _ordered(frame)
    active = ordered.loc[
        (ordered["time_s"] >= scenario.fault_time_s)
        & (ordered["time_s"] <= scenario.clearing_time_s)
    ]
    if len(active) < 4:
        raise ResultFormatError("Fault data contain insufficient samples during the fault")
    currents = active[current_columns].to_numpy(dtype=float)
    time_s = active["time_s"].to_numpy(dtype=float)
    first_cycle_end = min(
        scenario.clearing_time_s,
        scenario.fault_time_s + 1.0 / float(config["network"]["frequency_hz"]),  # type: ignore[index]
    )
    first_cycle = active.loc[active["time_s"] <= first_cycle_end, current_columns]
    nominal_peak_kv = float(config["network"]["nominal_voltage_kv"]) * math.sqrt(2.0 / 3.0)  # type: ignore[index]
    post = ordered.loc[
        (ordered["time_s"] >= scenario.clearing_time_s)
        & (ordered["time_s"] <= scenario.clearing_time_s + 0.02)
    ]
    post_peak = float(np.nanmax(np.abs(post[recovery_columns].to_numpy(dtype=float))))
    phase_rms = np.sqrt(np.mean(np.square(first_cycle.to_numpy(dtype=float)), axis=0))
    squared_sum = np.sum(np.square(currents), axis=1)
    i2t = np.sum(
        0.5 * (squared_sum[:-1] + squared_sum[1:]) * np.diff(time_s)
    )
    return {
        "fault_duration_ms": (scenario.clearing_time_s - scenario.fault_time_s) * 1000.0,
        "current_peak_ka": float(np.nanmax(np.abs(currents))),
        "first_cycle_rms_max_ka": float(np.nanmax(phase_rms)),
        "i2t_ka2s": float(i2t),
        "fault_bus_voltage_min_pu": float(
            np.nanmin(np.abs(active[voltage_columns].to_numpy(dtype=float))) / nominal_peak_kv
        ),
        "recovery_voltage_peak_pu": post_peak / nominal_peak_kv,
    }


def trv_metrics(
    frame: pd.DataFrame,
    scenario: FaultScenario,
    config: Mapping[str, object],
) -> Dict[str, float]:
    """Calculate ideal-breaker contact TRV and average RRRV from terminal voltages."""
    source_columns = ["v_source_a_kv", "v_source_b_kv", "v_source_c_kv"]
    load_columns = ["v_load_a_kv", "v_load_b_kv", "v_load_c_kv"]
    current_columns = ["i_a_ka", "i_b_ka", "i_c_ka"]
    _require(frame, ["time_s", *source_columns, *load_columns, *current_columns])
    ordered = _ordered(frame)
    post = ordered.loc[
        (ordered["time_s"] >= scenario.clearing_time_s)
        & (ordered["time_s"] <= scenario.clearing_time_s + 0.02)
    ]
    if len(post) < 4:
        raise ResultFormatError("TRV data contain insufficient post-opening samples")
    trv = post[source_columns].to_numpy(dtype=float) - post[load_columns].to_numpy(dtype=float)
    absolute = np.abs(trv)
    flat_index = int(np.nanargmax(absolute))
    row_index, phase_index = np.unravel_index(flat_index, absolute.shape)
    peak = float(absolute[row_index, phase_index])
    time_to_peak_s = max(
        float(post["time_s"].iloc[row_index]) - scenario.clearing_time_s,
        float(config["simulation"]["step_s"]),  # type: ignore[index]
    )
    pre = ordered.loc[
        (ordered["time_s"] >= scenario.fault_time_s)
        & (ordered["time_s"] <= scenario.clearing_time_s)
    ]
    currents = pre[current_columns].to_numpy(dtype=float)
    nominal_peak_kv = float(config["network"]["nominal_voltage_kv"]) * math.sqrt(2.0 / 3.0)  # type: ignore[index]
    return {
        "fault_duration_ms": (scenario.clearing_time_s - scenario.fault_time_s) * 1000.0,
        "interruption_current_peak_ka": float(np.nanmax(np.abs(currents))),
        "trv_peak_kv": peak,
        "trv_peak_pu": peak / nominal_peak_kv,
        "time_to_trv_peak_us": time_to_peak_s * 1e6,
        "average_rrrv_kv_per_us": peak / (time_to_peak_s * 1e6),
        "limiting_phase_index": float(phase_index),
    }

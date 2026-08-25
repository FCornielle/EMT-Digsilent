"""Scenario generation and engineering metrics for lightning travelling waves."""

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
class LightningScenario:
    """One installed ElmImpulse waveform parameter set."""

    scenario_id: str
    label: str
    waveform_code: int
    peak_current_ka: float
    correction_factor: float
    front_time_us: float
    tail_time_us: float
    steepness_factor: int
    maximum_steepness_ka_per_us: float


def lightning_scenarios(config: Mapping[str, object]) -> List[LightningScenario]:
    """Read the ordered native-impulse campaign."""
    return [
        LightningScenario(
            scenario_id=str(row["id"]),
            label=str(row["label"]),
            waveform_code=int(row["waveform_code"]),
            peak_current_ka=float(row["peak_current_ka"]),
            correction_factor=float(row.get("correction_factor", 1.0)),
            front_time_us=float(row["front_time_us"]),
            tail_time_us=float(row["tail_time_us"]),
            steepness_factor=int(row.get("steepness_factor", 10)),
            maximum_steepness_ka_per_us=float(
                row.get("maximum_steepness_ka_per_us", 0.0)
            ),
        )
        for row in config["sweep"]["waveforms"]  # type: ignore[index]
    ]


def export_lightning_manifest(
    scenarios: Iterable[LightningScenario], destination: Path
) -> Path:
    """Write the deterministic lightning-source matrix."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(item) for item in scenarios]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(LightningScenario.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(rows)
    return output


def line_wave_quantities(config: Mapping[str, object]) -> Dict[str, float]:
    """Derive the sequence-parameter surge impedance and travel times."""
    network = config["network"]  # type: ignore[index]
    line = network["line"]
    parameters = line["sequence_parameters"]
    omega = 2.0 * math.pi * float(network["frequency_hz"])
    inductance_h_per_km = float(parameters["x1_ohm_per_km"]) / omega
    capacitance_f_per_km = float(parameters["b1_us_per_km"]) * 1e-6 / omega
    surge_impedance = math.sqrt(inductance_h_per_km / capacitance_f_per_km)
    velocity_km_per_s = 1.0 / math.sqrt(inductance_h_per_km * capacitance_f_per_km)
    section_length = float(line["section_length_km"])
    return {
        "surge_impedance_ohm": surge_impedance,
        "wave_velocity_km_per_s": velocity_km_per_s,
        "section_travel_time_us": section_length / velocity_km_per_s * 1e6,
        "end_to_end_travel_time_us": 2.0 * section_length / velocity_km_per_s * 1e6,
    }


def _first_arrival(time_s: np.ndarray, values: np.ndarray, threshold: float) -> float:
    active = (time_s >= 0.0) & (np.abs(values) >= threshold)
    if not np.any(active):
        raise ResultFormatError("Lightning waveform never crossed the arrival threshold")
    return float(time_s[np.flatnonzero(active)[0]])


def lightning_metrics(
    frame: pd.DataFrame,
    scenario: LightningScenario,
    config: Mapping[str, object],
) -> Dict[str, float]:
    """Calculate travelling-wave peaks, arrival times, velocity, and source charge."""
    columns = [
        "time_s",
        "i_injected_a_ka",
        "v_strike_a_kv",
        "v_mid_a_kv",
        "v_remote_a_kv",
    ]
    missing = [column for column in columns if column not in frame]
    if missing:
        raise ResultFormatError("Lightning data are missing columns: {}".format(missing))
    ordered = frame.sort_values("time_s").drop_duplicates("time_s", keep="last")
    post = ordered.loc[ordered["time_s"] >= 0.0]
    if len(post) < 20:
        raise ResultFormatError("Lightning data contain insufficient post-trigger samples")
    strike = post["v_strike_a_kv"].to_numpy(dtype=float)
    middle = post["v_mid_a_kv"].to_numpy(dtype=float)
    remote = post["v_remote_a_kv"].to_numpy(dtype=float)
    current = post["i_injected_a_ka"].to_numpy(dtype=float)
    post_time = post["time_s"].to_numpy(dtype=float)
    threshold_fraction = float(config["analysis"].get("arrival_threshold_fraction", 0.05))  # type: ignore[index]
    strike_arrival = _first_arrival(
        post_time, strike, threshold_fraction * float(np.nanmax(np.abs(strike)))
    )
    middle_arrival = _first_arrival(
        post_time, middle, threshold_fraction * float(np.nanmax(np.abs(middle)))
    )
    remote_arrival = _first_arrival(
        post_time, remote, threshold_fraction * float(np.nanmax(np.abs(remote)))
    )
    line = config["network"]["line"]  # type: ignore[index]
    end_distance_km = 2.0 * float(line["section_length_km"])
    transit_s = remote_arrival - strike_arrival
    apparent_velocity = end_distance_km / transit_s if transit_s > 0.0 else math.inf
    current_squared = np.abs(current)
    current_peak_index = int(np.nanargmax(current_squared))
    half_level = 0.5 * current_squared[current_peak_index]
    tail_candidates = np.flatnonzero(
        (np.arange(len(current_squared)) > current_peak_index) & (current_squared <= half_level)
    )
    half_value_time_us = (
        float(post_time[tail_candidates[0]]) * 1e6 if len(tail_candidates) else math.nan
    )
    charge_c = float(
        np.sum(0.5 * (current[:-1] + current[1:]) * 1000.0 * np.diff(post_time))
    )
    analytical = line_wave_quantities(config)
    return {
        "configured_peak_current_ka": scenario.peak_current_ka,
        "line_current_peak_ka": float(np.nanmax(current_squared)),
        "strike_voltage_peak_kv": float(np.nanmax(np.abs(strike))),
        "midpoint_voltage_peak_kv": float(np.nanmax(np.abs(middle))),
        "remote_voltage_peak_kv": float(np.nanmax(np.abs(remote))),
        "strike_arrival_us": strike_arrival * 1e6,
        "midpoint_arrival_us": middle_arrival * 1e6,
        "remote_arrival_us": remote_arrival * 1e6,
        "measured_end_to_end_travel_us": transit_s * 1e6,
        "apparent_velocity_km_per_s": apparent_velocity,
        "half_value_time_us": half_value_time_us,
        "source_charge_c": charge_c,
        "arrival_error_percent": (
            (transit_s * 1e6 - analytical["end_to_end_travel_time_us"])
            / analytical["end_to_end_travel_time_us"]
            * 100.0
        ),
        **analytical,
    }

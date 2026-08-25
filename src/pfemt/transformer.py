"""Scenario generation and engineering metrics for transformer energization."""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

import numpy as np
import pandas as pd

from pfemt.errors import ResultFormatError
from pfemt.scenarios import switching_time


@dataclass(frozen=True)
class TransformerScenario:
    """One point-on-wave and residual-flux transformer energization case."""

    scenario_id: str
    switching_angle_deg: float
    switching_time_s: float
    residual_id: str
    residual_label: str
    residual_flux_a_pu: float
    residual_flux_b_pu: float
    residual_flux_c_pu: float
    source_voltage_pu: float


def transformer_scenarios(config: Mapping[str, object]) -> List[TransformerScenario]:
    """Return the deterministic angle by residual-flux campaign."""
    network = config["network"]  # type: ignore[index]
    sweep = config["sweep"]  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    base_time_s = float(sweep["base_switching_time_s"])  # type: ignore[index]
    source_voltage_pu = float(network["source"]["voltage_pu"])  # type: ignore[index]
    scenarios: List[TransformerScenario] = []
    for residual in sweep["residual_flux_cases"]:  # type: ignore[index]
        values = [float(value) for value in residual["phase_pu"]]
        if len(values) != 3:
            raise ValueError("Each residual-flux case must declare three phase values")
        for angle in sweep["angles_deg"]:  # type: ignore[index]
            angle_value = float(angle)
            angle_id = "{:03.0f}".format(angle_value)
            residual_id = str(residual["id"])
            scenarios.append(
                TransformerScenario(
                    scenario_id="{}_pow_{}deg".format(residual_id, angle_id),
                    switching_angle_deg=angle_value,
                    switching_time_s=switching_time(
                        base_time_s,
                        angle_value,
                        frequency_hz,
                    ),
                    residual_id=residual_id,
                    residual_label=str(residual["label"]),
                    residual_flux_a_pu=values[0],
                    residual_flux_b_pu=values[1],
                    residual_flux_c_pu=values[2],
                    source_voltage_pu=source_voltage_pu,
                )
            )
    return scenarios


def export_transformer_manifest(
    scenarios: Iterable[TransformerScenario], destination: Path
) -> Path:
    """Write the versioned transformer scenario matrix."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(scenario) for scenario in scenarios]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(TransformerScenario.__dataclass_fields__),
        )
        writer.writeheader()
        writer.writerows(rows)
    return output


def transformer_derived_quantities(config: Mapping[str, object]) -> Dict[str, float]:
    """Calculate rated bases and first-order flux scales from declared inputs."""
    network = config["network"]  # type: ignore[index]
    transformer = network["transformer"]  # type: ignore[index]
    power_mva = float(transformer["rated_power_mva"])  # type: ignore[index]
    hv_kv = float(transformer["hv_voltage_kv"])  # type: ignore[index]
    lv_kv = float(transformer["lv_voltage_kv"])  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    rated_hv_current_ka = power_mva / (math.sqrt(3.0) * hv_kv)
    rated_lv_current_ka = power_mva / (math.sqrt(3.0) * lv_kv)
    base_impedance_ohm = hv_kv**2 / power_mva
    leakage_impedance_ohm = (
        float(transformer["short_circuit_voltage_pct"]) / 100.0 * base_impedance_ohm
    )
    return {
        "rated_hv_current_ka": rated_hv_current_ka,
        "rated_lv_current_ka": rated_lv_current_ka,
        "hv_base_impedance_ohm": base_impedance_ohm,
        "leakage_impedance_ohm": leakage_impedance_ohm,
        "nominal_hv_phase_peak_kv": hv_kv * math.sqrt(2.0 / 3.0),
        "electrical_period_ms": 1000.0 / frequency_hz,
    }


def reconstruct_flux_proxy(
    frame: pd.DataFrame,
    switching_time_s: float,
    frequency_hz: float,
    nominal_voltage_kv: float,
    residual_flux_pu: Sequence[float],
) -> pd.DataFrame:
    """Integrate measured HV phase voltage into a transparent per-unit flux proxy."""
    voltage_columns = ("v_hv_a_kv", "v_hv_b_kv", "v_hv_c_kv")
    missing = [column for column in ("time_s", *voltage_columns) if column not in frame]
    if missing:
        raise ResultFormatError("Transformer data are missing columns: {}".format(missing))
    result = pd.DataFrame({"time_s": frame["time_s"].to_numpy(dtype=float)})
    time = result["time_s"].to_numpy(dtype=float)
    omega = 2.0 * math.pi * float(frequency_hz)
    nominal_peak = float(nominal_voltage_kv) * math.sqrt(2.0 / 3.0)
    active = time >= float(switching_time_s)
    for phase, column, residual in zip("abc", voltage_columns, residual_flux_pu):
        voltage = frame[column].to_numpy(dtype=float)
        integral = np.zeros_like(voltage)
        active_indices = np.flatnonzero(active)
        if active_indices.size > 1:
            start = int(active_indices[0])
            dt = np.diff(time[start:])
            trapezoids = 0.5 * (voltage[start:-1] + voltage[start + 1 :]) * dt
            integral[start + 1 :] = np.cumsum(trapezoids)
        result["flux_{}_pu".format(phase)] = float(residual) + omega * integral / nominal_peak
    return result


def _harmonic_ratio(
    time_s: np.ndarray,
    values: np.ndarray,
    frequency_hz: float,
    harmonic: int,
) -> float:
    """Estimate one harmonic magnitude relative to the fundamental by projection."""
    if len(time_s) < 4:
        return 0.0
    duration = float(time_s[-1] - time_s[0])
    if duration <= 0:
        return 0.0
    centered = values - float(np.mean(values))
    magnitudes = []
    for order in (1, harmonic):
        angle = 2.0 * math.pi * frequency_hz * order * time_s
        cosine = 2.0 / len(time_s) * float(np.dot(centered, np.cos(angle)))
        sine = 2.0 / len(time_s) * float(np.dot(centered, np.sin(angle)))
        magnitudes.append(math.hypot(cosine, sine))
    return magnitudes[1] / magnitudes[0] if magnitudes[0] > 1e-12 else 0.0


def transformer_energization_metrics(
    frame: pd.DataFrame,
    scenario: TransformerScenario,
    config: Mapping[str, object],
) -> Dict[str, object]:
    """Calculate inrush, voltage, flux-proxy, and second-harmonic KPIs."""
    required = [
        "time_s",
        "i_hv_a_ka",
        "i_hv_b_ka",
        "i_hv_c_ka",
        "v_hv_a_kv",
        "v_hv_b_kv",
        "v_hv_c_kv",
        "v_lv_a_kv",
        "v_lv_b_kv",
        "v_lv_c_kv",
    ]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ResultFormatError("Transformer data are missing columns: {}".format(missing))
    post = frame.loc[frame["time_s"] >= scenario.switching_time_s].copy()
    if post.empty:
        raise ResultFormatError("Transformer data contain no post-closing samples")
    current_columns = ["i_hv_a_ka", "i_hv_b_ka", "i_hv_c_ka"]
    currents = post[current_columns].to_numpy(dtype=float)
    row, phase = np.unravel_index(int(np.nanargmax(np.abs(currents))), currents.shape)
    peak_current = float(abs(currents[row, phase]))
    derived = transformer_derived_quantities(config)
    network = config["network"]  # type: ignore[index]
    residual = (
        scenario.residual_flux_a_pu,
        scenario.residual_flux_b_pu,
        scenario.residual_flux_c_pu,
    )
    flux = reconstruct_flux_proxy(
        frame,
        scenario.switching_time_s,
        float(network["frequency_hz"]),  # type: ignore[index]
        float(network["transformer"]["hv_voltage_kv"]),  # type: ignore[index]
        residual,
    )
    flux_columns = ["flux_a_pu", "flux_b_pu", "flux_c_pu"]
    post_flux = flux.loc[flux["time_s"] >= scenario.switching_time_s]
    flux_values = post_flux[flux_columns].to_numpy(dtype=float)
    flux_row, flux_phase = np.unravel_index(
        int(np.nanargmax(np.abs(flux_values))), flux_values.shape
    )
    harmonic_window = post.loc[
        post["time_s"] <= scenario.switching_time_s + 0.1
    ]
    harmonic_time = harmonic_window["time_s"].to_numpy(dtype=float)
    harmonic_values = harmonic_window[current_columns[phase]].to_numpy(dtype=float)
    harmonic_time = harmonic_time - harmonic_time[0]
    second_harmonic_ratio = _harmonic_ratio(
        harmonic_time,
        harmonic_values,
        float(network["frequency_hz"]),  # type: ignore[index]
        2,
    )
    lv_nominal_peak = float(network["transformer"]["lv_voltage_kv"]) * math.sqrt(2.0 / 3.0)  # type: ignore[index]
    lv_peak = float(np.nanmax(np.abs(post[["v_lv_a_kv", "v_lv_b_kv", "v_lv_c_kv"]])))
    return {
        "current_peak_ka": peak_current,
        "current_peak_pu": peak_current / float(derived["rated_hv_current_ka"]),
        "current_peak_phase": current_columns[phase],
        "current_peak_time_ms": float(
            (post.iloc[row]["time_s"] - scenario.switching_time_s) * 1000.0
        ),
        "flux_proxy_peak_pu": float(abs(flux_values[flux_row, flux_phase])),
        "flux_proxy_peak_phase": flux_columns[flux_phase],
        "flux_proxy_peak_time_ms": float(
            (post_flux.iloc[flux_row]["time_s"] - scenario.switching_time_s) * 1000.0
        ),
        "second_harmonic_ratio": second_harmonic_ratio,
        "lv_voltage_peak_pu": lv_peak / lv_nominal_peak,
        **derived,
    }

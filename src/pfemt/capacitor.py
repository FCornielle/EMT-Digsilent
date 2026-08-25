"""Scenarios, analytical checks, and KPIs for capacitor-bank switching."""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

import numpy as np
import pandas as pd

from pfemt.errors import ResultFormatError
from pfemt.scenarios import switching_time


@dataclass(frozen=True)
class CapacitorScenario:
    """One topology and closing-angle capacitor-bank switching case."""

    scenario_id: str
    topology_id: str
    topology_label: str
    existing_bank_connected: bool
    switching_angle_deg: float
    switching_time_s: float


def capacitor_scenarios(config: Mapping[str, object]) -> List[CapacitorScenario]:
    """Build the deterministic isolated/back-to-back point-on-wave matrix."""
    network = config["network"]  # type: ignore[index]
    sweep = config["sweep"]  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    base_time_s = float(sweep["base_switching_time_s"])  # type: ignore[index]
    scenarios: List[CapacitorScenario] = []
    for topology in sweep["topologies"]:  # type: ignore[index]
        for angle in sweep["angles_deg"]:  # type: ignore[index]
            angle_value = float(angle)
            topology_id = str(topology["id"])
            scenarios.append(
                CapacitorScenario(
                    scenario_id="{}_pow_{:03.0f}deg".format(topology_id, angle_value),
                    topology_id=topology_id,
                    topology_label=str(topology["label"]),
                    existing_bank_connected=bool(topology["existing_bank_connected"]),
                    switching_angle_deg=angle_value,
                    switching_time_s=switching_time(
                        base_time_s,
                        angle_value,
                        frequency_hz,
                    ),
                )
            )
    return scenarios


def export_capacitor_manifest(
    scenarios: Iterable[CapacitorScenario], destination: Path
) -> Path:
    """Write the capacitor-switching scenario matrix."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(scenario) for scenario in scenarios]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(CapacitorScenario.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(rows)
    return output


def capacitor_derived_quantities(config: Mapping[str, object]) -> Dict[str, float]:
    """Calculate bank capacitance and first-order isolated/back-to-back frequencies."""
    network = config["network"]  # type: ignore[index]
    voltage_kv = float(network["nominal_voltage_kv"])  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    bank = network["bank"]  # type: ignore[index]
    reactor = network["reactor"]  # type: ignore[index]
    source = network["source"]  # type: ignore[index]
    q_mvar = float(bank["reactive_power_mvar"])
    capacitance_uf = q_mvar * 1e6 / (
        2.0 * math.pi * frequency_hz * (voltage_kv * 1e3) ** 2
    ) * 1e6
    source_x_ohm = voltage_kv**2 / float(source["short_circuit_mva"])
    source_l_mh = source_x_ohm / (2.0 * math.pi * frequency_hz) * 1e3
    reactor_l_mh = float(reactor["inductance_mh"])
    capacitance_f = capacitance_uf * 1e-6
    isolated_frequency_hz = 1.0 / (
        2.0
        * math.pi
        * math.sqrt((source_l_mh + reactor_l_mh) * 1e-3 * capacitance_f)
    )
    back_to_back_frequency_hz = 1.0 / (
        2.0 * math.pi * math.sqrt(reactor_l_mh * 1e-3 * capacitance_f)
    )
    rated_current_ka = q_mvar / (math.sqrt(3.0) * voltage_kv)
    return {
        "phase_capacitance_uf": capacitance_uf,
        "source_inductance_mh": source_l_mh,
        "reactor_inductance_mh": reactor_l_mh,
        "isolated_frequency_hz": isolated_frequency_hz,
        "back_to_back_frequency_hz": back_to_back_frequency_hz,
        "bank_rated_current_ka": rated_current_ka,
        "nominal_phase_peak_kv": voltage_kv * math.sqrt(2.0 / 3.0),
    }


def capacitor_switching_metrics(
    frame: pd.DataFrame,
    scenario: CapacitorScenario,
    config: Mapping[str, object],
) -> Dict[str, float]:
    """Calculate current, voltage, di/dt, and ringing-frequency KPIs."""
    current_columns = ["i_bank_a_ka", "i_bank_b_ka", "i_bank_c_ka"]
    main_voltage_columns = ["v_main_a_kv", "v_main_b_kv", "v_main_c_kv"]
    bank_voltage_columns = ["v_bank_a_kv", "v_bank_b_kv", "v_bank_c_kv"]
    required = ["time_s", *current_columns, *main_voltage_columns, *bank_voltage_columns]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ResultFormatError("Capacitor data are missing columns: {}".format(missing))
    post = frame.loc[frame["time_s"] >= scenario.switching_time_s].copy()
    if len(post) < 4:
        raise ResultFormatError("Capacitor data contain insufficient post-closing samples")
    currents = post[current_columns].to_numpy(dtype=float)
    time_s = post["time_s"].to_numpy(dtype=float)
    peak_current_ka = float(np.nanmax(np.abs(currents)))
    dt = np.diff(time_s)
    positive_dt = dt > 0.0
    if not np.any(positive_dt):
        raise ResultFormatError("Capacitor data contain no increasing time interval")
    derivatives = np.diff(currents, axis=0)[positive_dt] / dt[positive_dt, None]
    peak_didt_ka_per_ms = float(np.nanmax(np.abs(derivatives))) / 1000.0
    derived = capacitor_derived_quantities(config)
    main_peak = float(np.nanmax(np.abs(post[main_voltage_columns].to_numpy(dtype=float))))
    bank_peak = float(np.nanmax(np.abs(post[bank_voltage_columns].to_numpy(dtype=float))))
    early = post.loc[post["time_s"] <= scenario.switching_time_s + 0.02]
    values = early["i_bank_a_ka"].to_numpy(dtype=float)
    early_time = early["time_s"].to_numpy(dtype=float)
    dominant_frequency_hz = 0.0
    if len(values) > 8:
        sample_step = float(np.median(np.diff(early_time)))
        spectrum = np.abs(np.fft.rfft(values - np.mean(values)))
        frequencies = np.fft.rfftfreq(len(values), sample_step)
        search = frequencies > 100.0
        if np.any(search):
            dominant_frequency_hz = float(frequencies[search][np.argmax(spectrum[search])])
    return {
        "current_peak_ka": peak_current_ka,
        "current_peak_pu_rated": peak_current_ka / derived["bank_rated_current_ka"],
        "peak_didt_ka_per_ms": peak_didt_ka_per_ms,
        "main_bus_voltage_peak_pu": main_peak / derived["nominal_phase_peak_kv"],
        "bank_voltage_peak_pu": bank_peak / derived["nominal_phase_peak_kv"],
        "dominant_frequency_hz": dominant_frequency_hz,
        **derived,
    }

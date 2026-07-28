"""Deterministic point-on-wave and Monte Carlo scenario generation."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Mapping


@dataclass(frozen=True)
class Scenario:
    """One reproducible EMT switching scenario."""

    scenario_id: str
    switching_angle_deg: float
    switching_time_s: float
    source_voltage_pu: float = 1.0
    line_length_km: float = 150.0
    seed: int = 0


def switching_time(base_time_s: float, angle_deg: float, frequency_hz: float) -> float:
    """Convert a point-on-wave electrical angle to an absolute event time."""
    normalized_angle = float(angle_deg) % 360.0
    return float(base_time_s) + normalized_angle / (360.0 * float(frequency_hz))


def point_on_wave_scenarios(config: Mapping[str, object]) -> List[Scenario]:
    """Create deterministic point-on-wave cases from the study YAML."""
    sweep = config["sweep"]  # type: ignore[index]
    network = config["network"]  # type: ignore[index]
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    base_time_s = float(sweep["base_switching_time_s"])  # type: ignore[index]
    line_length_km = float(network["line"]["length_km"])  # type: ignore[index]
    source_voltage_pu = float(network["source"]["voltage_pu"])  # type: ignore[index]
    return [
        Scenario(
            scenario_id="pow_{:03.0f}deg".format(float(angle)),
            switching_angle_deg=float(angle),
            switching_time_s=switching_time(base_time_s, float(angle), frequency_hz),
            source_voltage_pu=source_voltage_pu,
            line_length_km=line_length_km,
        )
        for angle in sweep["angles_deg"]  # type: ignore[index]
    ]


def monte_carlo_scenarios(config: Mapping[str, object]) -> List[Scenario]:
    """Sample reproducible operating conditions using a declared random seed."""
    monte_carlo = config["monte_carlo"]  # type: ignore[index]
    network = config["network"]  # type: ignore[index]
    count = int(monte_carlo["samples"])  # type: ignore[index]
    seed = int(monte_carlo["seed"])  # type: ignore[index]
    rng = random.Random(seed)
    frequency_hz = float(network["frequency_hz"])  # type: ignore[index]
    base_time_s = float(monte_carlo["base_switching_time_s"])  # type: ignore[index]
    voltage = monte_carlo["source_voltage_pu"]  # type: ignore[index]
    line = monte_carlo["line_length_km"]  # type: ignore[index]
    scenarios = []
    for index in range(count):
        angle = rng.uniform(0.0, 360.0)
        scenarios.append(
            Scenario(
                scenario_id="mc_{:04d}".format(index + 1),
                switching_angle_deg=angle,
                switching_time_s=switching_time(base_time_s, angle, frequency_hz),
                source_voltage_pu=rng.uniform(float(voltage["min"]), float(voltage["max"])),
                line_length_km=rng.uniform(float(line["min"]), float(line["max"])),
                seed=seed,
            )
        )
    return scenarios


def export_manifest(scenarios: Iterable[Scenario], destination: Path) -> Path:
    """Write a stable scenario manifest suitable for traceability and Git diffs."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(scenario) for scenario in scenarios]
    fieldnames = list(Scenario.__dataclass_fields__.keys())
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output


def circular_distance_deg(a: float, b: float) -> float:
    """Small utility used when grouping switching angles."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def phase_angle_at(time_s: float, frequency_hz: float) -> float:
    """Return the electrical phase angle in degrees."""
    return math.degrees(2.0 * math.pi * frequency_hz * time_s) % 360.0


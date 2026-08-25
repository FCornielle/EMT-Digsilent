"""One-at-a-time sensitivity scenarios for the transformer magnetic model."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Mapping

from pfemt.scenarios import switching_time
from pfemt.transformer import TransformerScenario


@dataclass(frozen=True)
class SaturationScenario:
    scenario_id: str
    label: str
    knee_flux_pu: float
    air_core_reactance_pu: float
    saturation_exponent: int
    residual_scale: float
    switching_angle_deg: float
    switching_time_s: float
    residual_flux_a_pu: float
    residual_flux_b_pu: float
    residual_flux_c_pu: float

    def transformer_scenario(self) -> TransformerScenario:
        return TransformerScenario(
            scenario_id=self.scenario_id,
            switching_angle_deg=self.switching_angle_deg,
            switching_time_s=self.switching_time_s,
            residual_id=self.scenario_id,
            residual_label=self.label,
            residual_flux_a_pu=self.residual_flux_a_pu,
            residual_flux_b_pu=self.residual_flux_b_pu,
            residual_flux_c_pu=self.residual_flux_c_pu,
            source_voltage_pu=1.0,
        )


def saturation_scenarios(config: Mapping[str, object]) -> List[SaturationScenario]:
    """Return the deterministic one-at-a-time magnetic sensitivity campaign."""
    network = config["network"]  # type: ignore[index]
    sweep = config["sweep"]  # type: ignore[index]
    angle = float(sweep["switching_angle_deg"])  # type: ignore[index]
    close_time = switching_time(
        float(sweep["base_switching_time_s"]),  # type: ignore[index]
        angle,
        float(network["frequency_hz"]),  # type: ignore[index]
    )
    residual = [float(value) for value in sweep["baseline_residual_flux_pu"]]  # type: ignore[index]
    scenarios = []
    for variant in sweep["variants"]:  # type: ignore[index]
        scale = float(variant["residual_scale"])
        scenarios.append(
            SaturationScenario(
                scenario_id=str(variant["id"]),
                label=str(variant["label"]),
                knee_flux_pu=float(variant["knee_flux_pu"]),
                air_core_reactance_pu=float(variant["air_core_reactance_pu"]),
                saturation_exponent=int(variant["saturation_exponent"]),
                residual_scale=scale,
                switching_angle_deg=angle,
                switching_time_s=close_time,
                residual_flux_a_pu=residual[0] * scale,
                residual_flux_b_pu=residual[1] * scale,
                residual_flux_c_pu=residual[2] * scale,
            )
        )
    return scenarios


def export_saturation_manifest(
    scenarios: Iterable[SaturationScenario], destination: Path
) -> Path:
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(scenario) for scenario in scenarios]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(SaturationScenario.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(rows)
    return output

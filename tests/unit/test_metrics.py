import numpy as np
import pandas as pd
import pytest

from pfemt.metrics import (
    compare_sweep_to_baseline,
    line_energization_derived_quantities,
    line_energization_metrics,
    worst_case,
)


def test_line_energization_peak_uses_phase_peak_base() -> None:
    nominal_kv = 230.0
    phase_peak = nominal_kv * np.sqrt(2.0 / 3.0)
    frame = pd.DataFrame(
        {
            "time_s": [0.019, 0.020, 0.021, 0.022],
            "v_recv_a_kv": [999.0, 0.0, 1.8 * phase_peak, 0.0],
            "v_recv_b_kv": [0.0, -phase_peak, 0.0, 0.0],
            "v_recv_c_kv": [0.0, 0.0, 0.0, 0.5 * phase_peak],
            "i_send_a_ka": [0.0, 0.0, -2.5, 0.0],
            "i_send_b_ka": [0.0, 1.2, 0.0, 0.0],
            "i_send_c_ka": [0.0, 0.0, 0.0, 0.0],
        }
    )
    result = line_energization_metrics(frame, nominal_kv, 0.020)
    assert result["voltage_peak_pu"] == pytest.approx(1.8)
    assert result["voltage_kv_peak_time_s"] == pytest.approx(0.021)
    assert result["voltage_kv_peak_phase"] == "v_recv_a_kv"
    assert result["current_ka_peak"] == pytest.approx(2.5)
    # The deliberately large pre-event sample must be excluded.
    assert result["voltage_kv_peak"] < 999.0


def test_worst_case_ranking() -> None:
    cases = [
        {"scenario_id": "a", "voltage_peak_pu": 1.4},
        {"scenario_id": "b", "voltage_peak_pu": 2.1},
    ]
    assert worst_case(cases)["scenario_id"] == "b"


def test_travelling_wave_checks_are_physically_plausible() -> None:
    config = {
        "network": {
            "nominal_voltage_kv": 230.0,
            "frequency_hz": 50.0,
            "source": {"short_circuit_mva": 10000.0},
            "line": {
                "length_km": 150.0,
                "sequence_parameters": {
                    "x1_ohm_per_km": 0.310,
                    "b1_us_per_km": 3.80,
                },
            },
        }
    }
    result = line_energization_derived_quantities(config)
    assert result["surge_impedance_ohm"] == pytest.approx(285.6, rel=0.01)
    assert result["propagation_velocity_km_per_s"] == pytest.approx(289_000, rel=0.02)
    assert result["one_way_travel_time_ms"] == pytest.approx(0.519, rel=0.02)
    assert result["ideal_open_end_step_pu"] == 2.0


def test_baseline_comparison_reports_pass_and_fail() -> None:
    summary = pd.DataFrame({"voltage_peak_pu": [2.257], "current_ka_peak": [0.8656]})
    baseline = {
        "results": {
            "worst_voltage_peak_pu": 2.257,
            "maximum_closing_current_ka_peak": 0.8656,
        },
        "tolerances": {"voltage_peak_relative": 0.005, "current_peak_relative": 0.01},
    }
    assert compare_sweep_to_baseline(summary, baseline)["status"] == "pass"
    summary.loc[0, "voltage_peak_pu"] = 2.5
    assert compare_sweep_to_baseline(summary, baseline)["status"] == "fail"

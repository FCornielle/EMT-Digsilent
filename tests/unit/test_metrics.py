import numpy as np
import pandas as pd
import pytest

from pfemt.metrics import line_energization_metrics, worst_case


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


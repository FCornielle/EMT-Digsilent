from pathlib import Path

import pandas as pd
import pytest

from pfemt.errors import ResultFormatError
from pfemt.io import read_powerfactory_csv


def test_powerfactory_header_fragments_are_normalized(tmp_path: Path) -> None:
    raw = tmp_path / "result.csv"
    pd.DataFrame(
        {
            "time in s": [0.0, 0.1],
            "BUS_RECEIVING m:u:A": [1.0, 2.0],
            "LINE m:i:bus1:A": [3.0, 4.0],
        }
    ).to_csv(raw, index=False)
    result = read_powerfactory_csv(
        raw,
        {
            "time_s": "time",
            "v_recv_a_kv": "m:u:A",
            "i_send_a_ka": "m:i:bus1:A",
        },
    )
    assert list(result.columns) == ["time_s", "v_recv_a_kv", "i_send_a_ka"]
    assert result.iloc[-1]["v_recv_a_kv"] == pytest.approx(2.0)


def test_ambiguous_fragment_fails(tmp_path: Path) -> None:
    raw = tmp_path / "ambiguous.csv"
    pd.DataFrame({"time A": [0.0], "time B": [0.0]}).to_csv(raw, index=False)
    with pytest.raises(ResultFormatError, match="matched 2"):
        read_powerfactory_csv(raw, {"time_s": "time"})


def test_two_level_powerfactory_comres_header(tmp_path: Path) -> None:
    raw = tmp_path / "powerfactory.csv"
    raw.write_text(
        "Results.ElmRes;BUS.ElmTerm;LINE.ElmLne\n"
        '"Time in s";"Phase Voltage A in kV";"Phase Current A/Terminal i in kA"\n'
        "0.000000;10.0;1.0\n"
        "0.000010;20.0;2.0\n",
        encoding="utf-8",
    )
    result = read_powerfactory_csv(
        raw,
        {
            "time_s": "time",
            "v_recv_a_kv": "Phase Voltage A in kV",
            "i_send_a_ka": "Phase Current A/Terminal i in kA",
        },
    )
    assert result.shape == (2, 3)
    assert result.iloc[-1]["i_send_a_ka"] == pytest.approx(2.0)

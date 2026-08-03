"""PowerFactory CSV normalization for pandas-based analysis."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Mapping

import pandas as pd

from pfemt.errors import ResultFormatError


def _normalized(text: object) -> str:
    return " ".join(str(text).replace("\n", " ").replace("\r", " ").split()).lower()


def read_powerfactory_csv(
    path: Path,
    column_map: Mapping[str, str],
    decimal: str = ".",
) -> pd.DataFrame:
    """Read a ComRes text export and map proprietary headers to stable names.

    Mapping values are case-insensitive fragments. This tolerates object paths
    added by PowerFactory while still failing on missing or ambiguous channels.
    """
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ResultFormatError("Result CSV does not exist: {}".format(source))
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        first_line = stream.readline()
        second_line = stream.readline()
    separator = ";" if first_line.count(";") > first_line.count(",") else ","
    first_header = next(csv.reader([first_line], delimiter=separator), [])
    second_header = next(csv.reader([second_line], delimiter=separator), [])
    has_powerfactory_object_header = bool(
        second_header
        and _normalized(second_header[0]).startswith("time")
    )
    if has_powerfactory_object_header:
        if len(first_header) != len(second_header):
            raise ResultFormatError(
                "PowerFactory CSV object and variable header lengths differ: {} versus {}".format(
                    len(first_header), len(second_header)
                )
            )
        combined_header = [second_header[0]] + [
            "{} | {}".format(first_header[index], second_header[index])
            for index in range(1, len(second_header))
        ]
        frame = pd.read_csv(
            source,
            sep=separator,
            skiprows=2,
            header=None,
            names=combined_header,
            decimal=decimal,
        )
    else:
        frame = pd.read_csv(source, sep=separator, decimal=decimal)
    if frame.empty:
        raise ResultFormatError("Result CSV is empty: {}".format(source))

    normalized_columns = {_normalized(column): column for column in frame.columns}
    rename: Dict[object, str] = {}
    for canonical, fragment in column_map.items():
        needle = _normalized(fragment)
        candidates = [
            original
            for normalized, original in normalized_columns.items()
            if needle == normalized or needle in normalized
        ]
        if len(candidates) != 1:
            raise ResultFormatError(
                "Column {!r} matched {} headers using fragment {!r}: {}".format(
                    canonical, len(candidates), fragment, list(frame.columns)
                )
            )
        rename[candidates[0]] = canonical
    normalized = frame.rename(columns=rename)
    required = list(column_map.keys())
    for column in required:
        normalized[column] = pd.to_numeric(normalized[column], errors="raise")
    return normalized[required].sort_values(required[0]).reset_index(drop=True)


def write_normalized_csv(frame: pd.DataFrame, destination: Path) -> Path:
    """Write a stable, analysis-friendly CSV."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False, float_format="%.10g")
    return output

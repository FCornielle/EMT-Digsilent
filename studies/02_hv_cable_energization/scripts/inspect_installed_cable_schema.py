"""Inspect the installed PowerFactory data schema for cable API class metadata."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, List

DEFAULT_DATABASE = Path(
    r"C:\Program Files\DIgSILENT\PowerFactory 2024\datascheme.db"
)
SEARCH_TERMS = ("TypCab", "TypCabsys", "ElmCabsys")
REQUIRED_ATTRIBUTES = {
    "TypCab": (
        "loc_name",
        "typCon",
        "diaTube",
        "has_ins2",
        "has_ins3",
        "has_arm",
        "has_sht",
        "has_scco",
        "has_scio",
        "iShtScreen",
        "diaCon",
        "thSht",
        "thIns",
        "rho",
        "my",
        "epsr",
        "tand",
        "Cf",
        "ralpha",
        "As",
        "tmax",
        "rhoSc",
        "mySc",
        "thSc",
    ),
    "TypCabsys": (
        "loc_name",
        "iopt_bur",
        "systp",
        "nlcir",
        "rhoEarth",
        "frnom",
        "nphas",
        "dInom",
        "red",
        "bond",
        "xy_c",
        "pcab_c",
    ),
    "ElmCabsys": (
        "loc_name",
        "outserv",
        "i_dist",
        "i_model",
        "fd_model",
        "fmin",
        "fmax",
        "ftau",
        "typ_id",
        "plines",
    ),
}


def _identifier(value: str) -> str:
    return '"{}"'.format(value.replace('"', '""'))


def inspect_schema(database: Path) -> Dict[str, object]:
    """Return rows containing the cable class names without modifying the database."""
    resolved = database.resolve()
    if not resolved.is_file():
        raise FileNotFoundError("PowerFactory data schema not found: {}".format(resolved))
    connection = sqlite3.connect("file:{}?mode=ro".format(resolved.as_posix()), uri=True)
    connection.row_factory = sqlite3.Row
    matches: Dict[str, List[Dict[str, object]]] = {term: [] for term in SEARCH_TERMS}
    seen = {term: set() for term in SEARCH_TERMS}
    table_schema: Dict[str, List[str]] = {}
    class_attributes: Dict[str, List[Dict[str, object]]] = {
        term: [] for term in SEARCH_TERMS
    }
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]
        for table in tables:
            columns = [row[1] for row in connection.execute("PRAGMA table_info({})".format(
                _identifier(table)
            ))]
            table_schema[table] = columns
            for column in columns:
                for term in SEARCH_TERMS:
                    query = "SELECT * FROM {} WHERE CAST({} AS TEXT) LIKE ? LIMIT 100".format(
                        _identifier(table), _identifier(column)
                    )
                    for row in connection.execute(query, ("%{}%".format(term),)):
                        payload = {"table": table, **dict(row)}
                        identity = json.dumps(payload, sort_keys=True, default=str)
                        if identity not in seen[term]:
                            matches[term].append(payload)
                            seen[term].add(identity)
        for term in SEARCH_TERMS:
            rows = connection.execute(
                """
                SELECT c.Build AS build, c.Name AS class_name,
                       a.Name AS attribute_name, a.Type AS attribute_type,
                       a.Size AS size, a.Offset AS offset
                FROM Class AS c
                JOIN Attribute AS a
                  ON a.Build = c.Build AND a.ClassId = c.Id
                WHERE c.Name = ?
                ORDER BY c.Build, a.Offset, a.Name
                """,
                (term,),
            )
            class_attributes[term] = [dict(row) for row in rows]
    finally:
        connection.close()
    capability_checks = {}
    for term, required in REQUIRED_ATTRIBUTES.items():
        attributes = class_attributes[term]
        latest_build = max((int(row["build"]) for row in attributes), default=0)
        available = {
            str(row["attribute_name"])
            for row in attributes
            if int(row["build"]) == latest_build
        }
        missing = sorted(set(required) - available)
        capability_checks[term] = {
            "latest_build": latest_build,
            "available_attribute_count": len(available),
            "required_attributes": list(required),
            "missing_attributes": missing,
            "passed": not missing,
        }
    return {
        "database": str(resolved),
        "search_terms": list(SEARCH_TERMS),
        "table_schema": table_schema,
        "matches": matches,
        "class_attributes": class_attributes,
        "capability_checks": capability_checks,
        "passed": all(item["passed"] for item in capability_checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = inspect_schema(arguments.database)
    rendered = json.dumps(report, indent=2, sort_keys=True, default=str)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
        print(arguments.output.resolve())
    else:
        print(rendered)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

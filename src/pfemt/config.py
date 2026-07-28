"""YAML configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import yaml

from pfemt.errors import ConfigurationError


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load a YAML mapping and attach its source directory."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise ConfigurationError("Configuration file does not exist: {}".format(resolved))
    with resolved.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        raise ConfigurationError("YAML root must be a mapping: {}".format(resolved))
    data["_meta"] = {"path": str(resolved), "directory": str(resolved.parent)}
    return data


def require(config: Mapping[str, Any], dotted_keys: Iterable[str]) -> None:
    """Validate that every dotted key exists and is not empty."""
    missing = []
    for dotted_key in dotted_keys:
        value: Any = config
        for part in dotted_key.split("."):
            if not isinstance(value, Mapping) or part not in value:
                missing.append(dotted_key)
                break
            value = value[part]
        else:
            if value is None or value == "":
                missing.append(dotted_key)
    if missing:
        raise ConfigurationError("Missing required configuration: {}".format(", ".join(missing)))


def resolve_from_config(config: Mapping[str, Any], value: str) -> Path:
    """Resolve a path relative to the YAML file that declared it."""
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    metadata = config.get("_meta", {})
    base = Path(str(metadata.get("directory", ".")))
    return (base / candidate).resolve()


def validate_study_config(config: Mapping[str, Any]) -> None:
    """Apply the minimum schema shared by all studies."""
    require(
        config,
        [
            "study.id",
            "powerfactory.project",
            "powerfactory.study_case",
            "simulation.start_s",
            "simulation.stop_s",
            "simulation.step_s",
            "outputs.directory",
        ],
    )
    simulation = config["simulation"]
    start = float(simulation["start_s"])
    stop = float(simulation["stop_s"])
    step = float(simulation["step_s"])
    if stop <= start:
        raise ConfigurationError("simulation.stop_s must be greater than start_s")
    if step <= 0 or step > (stop - start):
        raise ConfigurationError("simulation.step_s must be positive and smaller than duration")


"""PowerFactory Python module discovery and connection management."""

from __future__ import annotations

import importlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping, Optional, Tuple

from pfemt.errors import PowerFactoryUnavailable


@dataclass(frozen=True)
class Installation:
    """A local PowerFactory installation and its compatible Python module."""

    home: Path
    python_module: Path
    version: Tuple[int, ...]


def _version_from_name(name: str) -> Tuple[int, ...]:
    numbers = re.findall(r"\d+", name)
    return tuple(int(number) for number in numbers) or (0,)


def discover_installations(python_version: Optional[str] = None) -> List[Installation]:
    """Find installed PowerFactory versions compatible with this interpreter."""
    py_version = python_version or "{}.{}".format(sys.version_info.major, sys.version_info.minor)
    roots = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value) / "DIgSILENT")
    installations = []
    for root in roots:
        if not root.is_dir():
            continue
        for home in root.glob("PowerFactory *"):
            module_dir = home / "Python" / py_version
            if module_dir.joinpath("powerfactory.pyd").is_file():
                installations.append(
                    Installation(
                        home=home,
                        python_module=module_dir,
                        version=_version_from_name(home.name),
                    )
                )
    return sorted(installations, key=lambda item: item.version, reverse=True)


def import_powerfactory(home: Optional[Path] = None) -> Any:
    """Import the proprietary module without copying it into the repository."""
    if home is None:
        found = discover_installations()
        if not found:
            raise PowerFactoryUnavailable(
                "No compatible PowerFactory Python module was found for Python {}.{}.".format(
                    sys.version_info.major, sys.version_info.minor
                )
            )
        installation = found[0]
    else:
        resolved_home = Path(home).expanduser().resolve()
        py_version = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
        installation = Installation(
            home=resolved_home,
            python_module=resolved_home / "Python" / py_version,
            version=_version_from_name(resolved_home.name),
        )
        if not installation.python_module.joinpath("powerfactory.pyd").is_file():
            raise PowerFactoryUnavailable(
                "powerfactory.pyd not found in {}".format(installation.python_module)
            )

    dll_adder = getattr(os, "add_dll_directory", None)
    if callable(dll_adder):
        dll_adder(str(installation.home))
    module_path = str(installation.python_module)
    if module_path not in sys.path:
        sys.path.insert(0, module_path)
    try:
        return importlib.import_module("powerfactory")
    except Exception as exc:
        raise PowerFactoryUnavailable(
            "Failed to import PowerFactory from {}: {}".format(module_path, exc)
        ) from exc


def connect(config: Mapping[str, Any]) -> Any:
    """Connect internally or start PowerFactory engine mode."""
    pf_config = config.get("connection", config)
    home_value = pf_config.get("home")
    module = import_powerfactory(Path(home_value) if home_value else None)
    mode = os.environ.get(
        "PFEMT_CONNECTION_MODE",
        str(pf_config.get("mode", "internal")),
    ).lower()
    username = os.environ.get("PFEMT_USERNAME", pf_config.get("username"))
    password = os.environ.get("PFEMT_PASSWORD", pf_config.get("password"))
    command_line = pf_config.get("command_line")

    if mode == "internal":
        app = module.GetApplication()
    elif mode == "external":
        try:
            app = module.GetApplicationExt(username, password, command_line)
        except Exception as exc:
            raise PowerFactoryUnavailable(
                "PowerFactory engine mode could not start: {}".format(exc)
            ) from exc
    else:
        raise PowerFactoryUnavailable("Unsupported connection mode: {!r}".format(mode))

    if app is None:
        raise PowerFactoryUnavailable(
            "PowerFactory returned no application object. Check the user and connection mode."
        )
    return app


def installation_report() -> List[Mapping[str, str]]:
    """Return serializable discovery information for the CLI doctor command."""
    return [
        {
            "home": str(item.home),
            "python_module": str(item.python_module),
            "version": ".".join(str(value) for value in item.version),
        }
        for item in discover_installations()
    ]

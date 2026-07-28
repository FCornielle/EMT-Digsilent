"""Simulation event management."""

from __future__ import annotations

from typing import Any

from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import create_or_get, set_attribute


def event_folder(initial_conditions: Any) -> Any:
    """Resolve the event folder assigned to the active ComInc command."""
    folder = getattr(initial_conditions, "p_event", None)
    if folder is None:
        raise PowerFactoryExecutionError("ComInc.p_event is not assigned")
    return folder


def configure_switch_event(
    initial_conditions: Any,
    target: Any,
    name: str,
    time_s: float,
    action: int = 1,
) -> Any:
    """Create/update a three-phase switch event.

    ``action`` follows the PowerFactory EvtSwitch enumeration: 0 opens and 1
    closes. The supplied line-energization study uses the closing action.
    """
    folder = event_folder(initial_conditions)
    event = create_or_get(folder, "EvtSwitch", name)
    set_attribute(event, "time", float(time_s))
    set_attribute(event, "p_target", target)
    set_attribute(event, "i_switch", int(action))
    set_attribute(event, "i_allph", 1, required=False)
    return event

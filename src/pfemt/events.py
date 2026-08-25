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


def configure_short_circuit_event(
    initial_conditions: Any,
    target: Any,
    name: str,
    time_s: float,
    fault_type_code: int,
    clear: bool = False,
    resistance_ohm: float = 0.0,
    reactance_ohm: float = 0.0,
    phase_selector: int = 0,
) -> Any:
    """Create/update an EMT short-circuit application or clearing event.

    PowerFactory 2024 uses ``i_clearShc`` to distinguish a clearing event.
    ``i_shc`` selects the fault family; the phase selectors make the chosen
    conductor pair explicit for unbalanced faults.
    """
    folder = event_folder(initial_conditions)
    event = create_or_get(folder, "EvtShc", name)
    set_attribute(event, "time", float(time_s))
    set_attribute(event, "p_target", target)
    set_attribute(event, "i_shc", int(fault_type_code))
    set_attribute(event, "i_clearShc", int(clear))
    set_attribute(event, "R_f", float(resistance_ohm))
    set_attribute(event, "X_f", float(reactance_ohm))
    set_attribute(event, "i_pspgf", int(phase_selector), required=False)
    set_attribute(event, "i_p2psc", int(phase_selector), required=False)
    set_attribute(event, "i_p2pgf", int(phase_selector), required=False)
    return event


def configure_parameter_event(
    initial_conditions: Any,
    target: Any,
    name: str,
    time_s: float,
    variable: str,
    value: str,
) -> Any:
    """Create/update a parameter event for an unconnected scalar model input."""
    folder = event_folder(initial_conditions)
    event = create_or_get(folder, "EvtParam", name)
    set_attribute(event, "time", float(time_s))
    set_attribute(event, "p_target", target)
    set_attribute(event, "variable", variable)
    set_attribute(event, "value", value)
    return event

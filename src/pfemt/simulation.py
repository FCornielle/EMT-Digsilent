"""Configuration and execution of PowerFactory EMT simulations."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from pfemt.errors import PowerFactoryExecutionError
from pfemt.pfapi import execute, set_attribute


def study_commands(app: Any) -> Tuple[Any, Any]:
    """Return Initial Conditions and Simulation commands from the active Study Case."""
    initial_conditions = app.GetFromStudyCase("ComInc")
    simulation = app.GetFromStudyCase("ComSim")
    if initial_conditions is None or simulation is None:
        raise PowerFactoryExecutionError(
            "The active Study Case must contain ComInc and ComSim commands"
        )
    return initial_conditions, simulation


def configure_emt(
    initial_conditions: Any,
    simulation: Any,
    config: Mapping[str, Any],
) -> None:
    """Configure EMT mode, time interval and fixed/output time steps."""
    sim = config["simulation"]
    set_attribute(initial_conditions, "iopt_sim", sim.get("mode_code", "ins"))
    set_attribute(initial_conditions, "tstart", float(sim["start_s"]))
    set_attribute(initial_conditions, "dtemt", float(sim["step_s"]))
    set_attribute(
        initial_conditions,
        "dtout_emt",
        float(sim.get("output_step_s", sim["step_s"])),
    )
    set_attribute(simulation, "tstop", float(sim["stop_s"]))


def run_emt(initial_conditions: Any, simulation: Any) -> None:
    """Calculate EMT initial conditions and execute the time-domain simulation."""
    execute(initial_conditions, "EMT initial conditions")
    execute(simulation, "EMT simulation")


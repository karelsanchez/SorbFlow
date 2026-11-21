"""Numerical diagnostics: mass balance and state checks of simulation results."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from ..solvers import SimulationResult


@dataclass(frozen=True, slots=True)
class MassBalanceReport:
    max_absolute_residual_kg: float
    max_scaled_residual: float
    passed: bool


def mass_balance(result: SimulationResult) -> MassBalanceReport:
    """Recompute mass closure from exported time samples; internal checks are separate."""
    settings = json.loads(result.options_json)
    residual = (
        result.inventory_kg - result.inventory_kg[0] - result.inlet_mass_kg + result.outlet_mass_kg
    )
    scale = np.maximum(
        np.maximum(result.inventory_kg[0], result.inlet_mass_kg), settings["mass_reference_kg"]
    )
    passed = bool(
        np.all(np.abs(residual) <= settings["atol_mass_kg"] + settings["mass_rtol"] * scale)
        and np.all(np.abs(residual) / scale <= settings["mass_rtol"])
    )
    return MassBalanceReport(
        float(np.max(np.abs(residual))), float(np.max(np.abs(residual) / scale)), passed
    )

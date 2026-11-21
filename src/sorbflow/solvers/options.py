"""Explicit numerical settings with physical absolute tolerances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from .._arrays import FloatArray, real_array
from ..units import finite_scalar


@dataclass(frozen=True, slots=True, kw_only=True)
class SolverOptions:
    """BDF/Radau tolerances; positive finite settings are never silently clamped."""

    method: Literal["BDF", "Radau"] = "BDF"
    rtol: float = 1e-7
    atol_concentration_kg_m3: float = 1e-10
    atol_loading_kg_kg: float = 1e-12
    atol_mass_kg: float = 1e-12
    mass_rtol: float = 1e-6
    mass_reference_kg: float = 1e-12
    max_step_s: float | None = None
    axial_cells: int = 100
    radial_cells: int = 20
    jacobian: Literal["finite_difference", "analytic"] = "finite_difference"
    history: Literal["dense", "streaming"] = "dense"

    def __post_init__(self) -> None:
        if self.method not in ("BDF", "Radau"):
            raise ValueError("Only BDF and Radau are supported")
        if self.jacobian not in ("finite_difference", "analytic"):
            raise ValueError("jacobian must be finite_difference or analytic")
        if self.history not in ("dense", "streaming"):
            raise ValueError("history must be dense or streaming")
        for name in (
            "rtol",
            "atol_concentration_kg_m3",
            "atol_loading_kg_kg",
            "atol_mass_kg",
            "mass_rtol",
            "mass_reference_kg",
            "max_step_s",
        ):
            value = getattr(self, name)
            if name == "max_step_s" and value is None:
                continue
            number = finite_scalar(value, name)
            if number <= 0:
                raise ValueError(f"{name} must be positive")
            object.__setattr__(self, name, number)
        if not 100 * np.finfo(float).eps <= self.rtol < 1:
            raise ValueError("rtol must be >=100*machine epsilon and <1")
        if self.mass_rtol >= 1:
            raise ValueError("mass_rtol must be <1")
        if type(self.axial_cells) is not int or self.axial_cells < 2:
            raise ValueError("axial_cells must be an integer >=2")
        if type(self.radial_cells) is not int or self.radial_cells < 2:
            raise ValueError("radial_cells must be an integer >=2")


def sample_times(duration_s: float, requested: ArrayLike | None) -> FloatArray:
    """Require an ordered full-horizon observation grid, not an integration step size."""
    result = (
        np.linspace(0, duration_s, 201) if requested is None else real_array(requested, "time_s")
    )
    if result.ndim != 1 or result.size < 2:
        raise ValueError("time_s must be a one-dimensional array with at least two points")
    if result[0] != 0 or result[-1] != duration_s or np.any(np.diff(result) <= 0):
        raise ValueError("time_s must strictly increase from zero to duration_s")
    return result

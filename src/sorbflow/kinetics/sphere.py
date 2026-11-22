"""Conservative spherical FV surface diffusion and nonlinear film coupling."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .._arrays import FloatArray
from ..equilibrium import Isotherm
from ..equilibrium.isotherms import trial_loading
from ..solvers.integration import SimulationError
from ..units import finite_scalar


@dataclass(frozen=True, slots=True)
class SphereGrid:
    """Uniform radial faces; exact shell volumes per unit solid angle."""

    radius_m: float
    cells: int

    def __post_init__(self) -> None:
        if finite_scalar(self.radius_m, "radius_m") <= 0:
            raise ValueError("radius_m must be positive")
        if type(self.cells) is not int or self.cells < 2:
            raise ValueError("cells must be an integer >=2")

    @property
    def centers_m(self) -> FloatArray:
        return np.asarray(
            (np.arange(self.cells, dtype=np.float64) + 0.5) * self.radius_m / self.cells
        )

    @property
    def faces_m(self) -> FloatArray:
        return np.linspace(0, self.radius_m, self.cells + 1)

    @property
    def shell_volumes_m3(self) -> FloatArray:
        return np.diff(self.faces_m**3) / 3

    @property
    def mean_weights(self) -> FloatArray:
        volumes = self.shell_volumes_m3
        return volumes / np.sum(volumes)


def diffusion_rhs(
    loading: FloatArray,
    surface_mass_flux: FloatArray,
    *,
    grid: SphereGrid,
    diffusivity_m2_s: float,
    particle_density_kg_m3: float,
) -> FloatArray:
    """q shape (axial cell, radial shell); boundary flux is positive inward."""
    flux = np.zeros((loading.shape[0], grid.cells + 1))
    flux[:, 1:-1] = (
        grid.faces_m[1:-1] ** 2
        * diffusivity_m2_s
        * np.diff(loading, axis=1)
        / (grid.radius_m / grid.cells)
    )
    flux[:, -1] = grid.radius_m**2 * surface_mass_flux / particle_density_kg_m3
    return np.asarray(np.diff(flux, axis=1) / grid.shell_volumes_m3)


def film_flux(
    bulk: FloatArray,
    outer_loading: FloatArray,
    model: Isotherm,
    *,
    grid: SphereGrid,
    diffusivity_m2_s: float,
    particle_density_kg_m3: float,
    film_coefficient_m_s: float,
) -> FloatArray:
    """Solve the implicit monotone surface concentration; no inverse isotherm needed.

    Odd continuation is used exclusively for implicit solver trial states. The same
    returned flux is used in both phases, including desorption.
    """
    conductance = particle_density_kg_m3 * diffusivity_m2_s / (grid.radius_m / (2 * grid.cells))
    target = film_coefficient_m_s * bulk + conductance * outer_loading
    sign = np.sign(target)
    absolute = np.abs(target)
    low = np.zeros_like(bulk)
    high = absolute / film_coefficient_m_s
    eps = np.finfo(float).eps
    tiny = np.finfo(float).tiny
    bound = 512 * eps * np.maximum(absolute, tiny)

    def collapsed(lower: FloatArray, upper: FloatArray) -> npt.NDArray[np.bool_]:
        # The residual is monotone increasing in the surface concentration, so the
        # bracket always contains the root. Once it shrinks to a few units in the last
        # place, the midpoint is the best representable root even when the residual
        # cannot reach ``bound`` (e.g. Freundlich exponents < 1, where dq*/dc is
        # unbounded near c = 0 and one ulp of c spans a large flux increment).
        return np.asarray(upper - lower <= 4 * eps * np.maximum(upper, tiny))

    for _ in range(1100):
        mid = (low + high) / 2
        estimate = film_coefficient_m_s * mid + conductance * model.loading(mid)
        converged = (np.abs(estimate - absolute) <= bound) | collapsed(low, high)
        if np.all(converged):
            keep = collapsed(low, high)
            low, high = np.where(keep, low, mid), np.where(keep, high, mid)
            break
        low = np.where(converged | (estimate < absolute), mid, low)
        high = np.where(converged | (estimate >= absolute), mid, high)
    surface = sign * (low + high) / 2
    residual = film_coefficient_m_s * surface + conductance * trial_loading(model, surface) - target
    accepted = (np.abs(residual) <= bound) | collapsed(low, high)
    if not np.all(np.isfinite(surface)) or not np.all(accepted):
        raise SimulationError("Film/surface equilibrium root did not converge")
    surface_loading = trial_loading(model, surface)
    film_side = film_coefficient_m_s * (bulk - surface)
    solid_side = conductance * (surface_loading - outer_loading)
    # Choose the expression with the smaller absolute cancellation/error scale.
    # A shared but poorly conditioned film-side flux can conserve mass while being
    # physically inaccurate when the film resistance tends to zero.
    film_scale = film_coefficient_m_s * (np.abs(bulk) + np.abs(surface))
    solid_scale = conductance * (np.abs(surface_loading) + np.abs(outer_loading))
    return np.asarray(np.where(film_scale <= solid_scale, film_side, solid_side))

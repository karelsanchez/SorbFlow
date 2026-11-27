"""Conservative spherical FV surface diffusion and nonlinear film coupling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from .._arrays import FloatArray
from ..equilibrium import Isotherm
from ..equilibrium.isotherms import (
    FreundlichIsotherm,
    LangmuirIsotherm,
    LinearIsotherm,
    _loading_kernel,
)
from ..solvers.integration import SimulationError
from ..units import finite_scalar

_EPS = float(np.finfo(float).eps)
_TINY = float(np.finfo(float).tiny)
_MAX_ITERATIONS = 1100


@dataclass(frozen=True, slots=True)
class SphereGrid:
    """Radial shells with exact volumes per unit solid angle.

    ``growth`` is the width ratio of consecutive shells from the centre outward.
    The default ``1.0`` is the uniform grid; ``0 < growth < 1`` refines the shells
    geometrically toward the particle surface, where HSDM gradients are steepest.
    Cell centres are shell mid-radii; face gradients use centre-to-centre distances
    and the film/solid conductance uses the outermost centre-to-surface distance.
    Shell volumes are exact for every spacing, so the scheme conserves mass.
    """

    radius_m: float
    cells: int
    growth: float = 1.0
    _faces: FloatArray = field(init=False, repr=False, compare=False)
    _centers: FloatArray = field(init=False, repr=False, compare=False)
    _volumes: FloatArray = field(init=False, repr=False, compare=False)
    _weights: FloatArray = field(init=False, repr=False, compare=False)
    _spacing: FloatArray = field(init=False, repr=False, compare=False)
    _surface_distance: float = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if finite_scalar(self.radius_m, "radius_m") <= 0:
            raise ValueError("radius_m must be positive")
        if type(self.cells) is not int or self.cells < 2:
            raise ValueError("cells must be an integer >=2")
        growth = finite_scalar(self.growth, "growth")
        if not 0 < growth <= 1:
            raise ValueError("growth must satisfy 0 < growth <= 1")
        radius, cells = self.radius_m, self.cells
        if growth == 1:
            faces = np.linspace(0, radius, cells + 1)
            centers = np.asarray((np.arange(cells, dtype=np.float64) + 0.5) * radius / cells)
            spacing = np.full(cells - 1, radius / cells)
            surface_distance = radius / (2 * cells)
        else:
            widths = growth ** np.arange(cells, dtype=np.float64)
            faces = np.concatenate(([0.0], np.cumsum(widths)))
            faces = faces * (radius / faces[-1])
            faces[-1] = radius
            centers = (faces[:-1] + faces[1:]) / 2
            spacing = np.diff(centers)
            surface_distance = float(radius - centers[-1])
        volumes = np.diff(faces**3) / 3
        for name, value in (
            ("_faces", faces),
            ("_centers", centers),
            ("_volumes", volumes),
            ("_weights", volumes / np.sum(volumes)),
            ("_spacing", spacing),
        ):
            value = np.asarray(value, dtype=np.float64)
            value.setflags(write=False)
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_surface_distance", float(surface_distance))

    @property
    def centers_m(self) -> FloatArray:
        return self._centers.copy()

    @property
    def faces_m(self) -> FloatArray:
        return self._faces.copy()

    @property
    def shell_volumes_m3(self) -> FloatArray:
        return self._volumes.copy()

    @property
    def mean_weights(self) -> FloatArray:
        return self._weights.copy()

    @property
    def surface_distance_m(self) -> float:
        """Distance from the outermost shell centre to the particle surface."""
        return self._surface_distance


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
        grid._faces[1:-1] ** 2 * diffusivity_m2_s * np.diff(loading, axis=1) / grid._spacing
    )
    flux[:, -1] = grid.radius_m**2 * surface_mass_flux / particle_density_kg_m3
    return np.asarray(np.diff(flux, axis=1) / grid._volumes)


# A residual evaluator returns (kf*x + G*q*(x) - T, q*(x)); a step proposer returns a
# Newton candidate from (x, residual, q*(x)), NaN where it has none.
_Residual = Callable[[FloatArray], tuple[FloatArray, FloatArray]]
_Step = Callable[[FloatArray, FloatArray, FloatArray], FloatArray]


def _collapsed(lower: FloatArray, upper: FloatArray) -> npt.NDArray[np.bool_]:
    # The residual is monotone increasing in the surface concentration, so the
    # bracket always contains the root. Once it shrinks to a few units in the last
    # place, the bracket is the best representable root even when the residual
    # cannot reach the tolerance (e.g. Freundlich exponents < 1, where dq*/dc is
    # unbounded near c = 0 and one ulp of c spans a large flux increment).
    return np.asarray(upper - lower <= 4 * _EPS * np.maximum(upper, _TINY))


def _bisect(lower: FloatArray, upper: FloatArray) -> FloatArray:
    # Geometric bisection once the bracket spans orders of magnitude, so that
    # roots near zero (strongly favourable isotherms) are reached in few steps.
    geometric = np.sqrt(lower) * np.sqrt(upper)
    return np.asarray(np.where((lower > 0) & (upper > 4 * lower), geometric, (lower + upper) / 2))


def _safeguarded_root(
    guess: FloatArray,
    lower: FloatArray,
    upper: FloatArray,
    residual: _Residual,
    step: _Step | None,
    bound: FloatArray,
) -> tuple[FloatArray, FloatArray, FloatArray, npt.NDArray[np.bool_]]:
    """Vectorised safeguarded Newton for a monotone increasing residual.

    Newton candidates are accepted only strictly inside the current bracket and
    while the residual at least halves; otherwise the bracket is bisected. A step
    that stalls below one ulp is nudged across the root so that a collapsed
    bracket can certify it. Returns root, q*(root), residual and acceptance.
    """
    # Invariant: lower <= x <= upper; both ends are valid bounds of the root.
    x = guess
    f, q = residual(x)
    previous = np.full_like(x, np.inf)
    accepted = np.zeros(x.shape, dtype=bool)
    with np.errstate(all="ignore"):
        for _ in range(_MAX_ITERATIONS):
            negative = f < 0
            lower = np.where(negative, x, lower)
            upper = np.where(negative, upper, x)
            magnitude = np.abs(f)
            accepted = magnitude <= bound
            if accepted.all():
                break
            accepted |= _collapsed(lower, upper)
            if accepted.all():
                break
            if step is None:
                candidate = _bisect(lower, upper)
            else:
                candidate = step(x, f, q)
                # NaN candidates fail every comparison and fall back to bisection.
                usable = (candidate > lower) & (candidate < upper) & (magnitude <= 0.5 * previous)
                if not usable.all():
                    candidate = np.where(usable, candidate, _bisect(lower, upper))
                stalled = usable & (np.abs(candidate - x) <= 2 * _EPS * x)
                if stalled.any():
                    nudge = np.where(
                        negative,
                        np.minimum(x * (1 + 2 * _EPS), upper),
                        np.maximum(x * (1 - 2 * _EPS), lower),
                    )
                    candidate = np.where(stalled, nudge, candidate)
            previous = magnitude
            x = np.where(accepted, x, candidate)
            f, q = residual(x)
    return x, q, f, accepted


def _solve_surface(
    absolute: FloatArray, model: Isotherm, kf: float, conductance: float, bound: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray, npt.NDArray[np.bool_]]:
    """Root of kf*x + G*q*(x) = T for T >= 0 with x in [0, T/kf].

    Closed forms (linear, Langmuir) and the unsafeguarded log-Newton fast path
    (Freundlich) are accepted only when the residual meets ``bound`` everywhere;
    otherwise the safeguarded bracketing iteration takes over from their result.
    """

    def residual(x: FloatArray) -> tuple[FloatArray, FloatArray]:
        q = _loading_kernel(model, x)
        return np.asarray(kf * x + conductance * q - absolute), q

    lower = np.zeros_like(absolute)
    upper = absolute / kf
    step: _Step | None
    with np.errstate(all="ignore"):
        if isinstance(model, LinearIsotherm):
            guess = absolute / (kf + conductance * model.parameters.distribution_m3_kg)
            step = _derivative_step(model, kf, conductance)
        elif isinstance(model, LangmuirIsotherm):
            # kf*b*x^2 + (kf + G*qmax*b - T*b)*x - T = 0; the positive root is taken
            # from whichever formula adds terms of equal sign (no cancellation).
            b, qmax = model.parameters.affinity_m3_kg, model.parameters.qmax_kg_kg
            linear_term = kf + conductance * qmax * b - absolute * b
            root = np.hypot(linear_term, 2 * np.sqrt(kf * b * absolute))
            guess = np.where(
                linear_term >= 0,
                2 * absolute / (linear_term + root),
                (root - linear_term) / (2 * kf * b),
            )
            step = _derivative_step(model, kf, conductance)
        elif isinstance(model, FreundlichIsotherm):
            # kf*x + G*a*x^n = T. Each single-term root bounds the true root from
            # above, half of each target bounds it from below, so the bracket spans
            # at most a factor 2^(1/n). Newton in u = log(x) on a convex, increasing
            # sum of exponentials converges monotonically from the upper bound, and
            # its slope x*dF/dx = kf*x + n*G*q*(x) stays finite even where dq*/dc is
            # unbounded (exponent < 1 near c = 0).
            p = model.parameters
            n = p.exponent
            log_ga = float(np.log(conductance) + np.log(p.q_ref_kg_kg) - n * np.log(p.c_ref_kg_m3))
            # Relative rounding bound of exp((log T - log Ga)/n) for any finite T, so
            # widened bounds cannot cross the root.
            margin = 8 * _EPS * (2 + (746 + abs(log_ga)) / n)
            power_root = np.exp((np.log(absolute) - log_ga) / n)
            upper = np.minimum(upper, power_root * (1 + margin))
            lower = np.minimum(absolute / (2 * kf), power_root * 2 ** (-1 / n)) * (1 - margin)
            lower = np.minimum(lower, upper)
            slope_factor = n * conductance

            def log_newton(x: FloatArray, f: FloatArray, q: FloatArray) -> FloatArray:
                # TINY keeps x = 0 (zero target) a fixed point instead of 0/0.
                return np.asarray(x * np.exp(-f / (kf * x + slope_factor * q + _TINY)))

            step = log_newton
            x = upper
            for _ in range(12):
                f, q = residual(x)
                if (np.abs(f) <= bound).all():
                    return x, q, f, np.ones(x.shape, dtype=bool)
                x = log_newton(x, f, q)
            guess = x
        else:
            guess = upper / 2
            step = _derivative_step(model, kf, conductance)
        if not isinstance(model, FreundlichIsotherm):
            f, q = residual(guess)
            if (np.abs(f) <= bound).all():
                return guess, q, f, np.ones(guess.shape, dtype=bool)
        # NaN-safe projection into the bracket before the safeguarded iteration.
        guess = np.fmin(np.fmax(guess, lower), upper)
    return _safeguarded_root(guess, lower, upper, residual, step, bound)


def _derivative_step(model: Isotherm, kf: float, conductance: float) -> _Step | None:
    """Plain Newton step from the isotherm slope, or None (bisection only)."""
    unchecked = getattr(model, "_derivative_unchecked", None)
    public = getattr(model, "derivative", None)
    slope_of = unchecked if callable(unchecked) else public
    if not callable(slope_of):
        return None

    def step(x: FloatArray, f: FloatArray, _q: FloatArray) -> FloatArray:
        try:
            slope = np.asarray(slope_of(x), dtype=np.float64)
        except (ValueError, ArithmeticError):
            return np.full_like(x, np.nan)
        return np.asarray(x - f / (kf + conductance * slope))

    return step


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

    Linear and Langmuir isotherms use closed forms, Freundlich a safeguarded Newton
    in log concentration and any other isotherm a safeguarded Newton (or bisection
    without a derivative); every root is certified by the residual or a collapsed
    bracket. Odd continuation is used exclusively for implicit solver trial states.
    The same returned flux is used in both phases, including desorption.
    """
    conductance = particle_density_kg_m3 * diffusivity_m2_s / grid._surface_distance
    target = film_coefficient_m_s * bulk + conductance * outer_loading
    if not np.all(np.isfinite(target)):
        raise SimulationError("Film/surface equilibrium root did not converge")
    sign = np.sign(target)
    absolute = np.abs(target)
    bound = 512 * _EPS * np.maximum(absolute, _TINY)
    root, root_loading, _residual, accepted = _solve_surface(
        absolute, model, film_coefficient_m_s, conductance, bound
    )
    surface = sign * root
    if not np.all(np.isfinite(surface)) or not np.all(accepted):
        raise SimulationError("Film/surface equilibrium root did not converge")
    # Odd continuation: identical to trial_loading(model, surface).
    surface_loading = sign * root_loading
    if not np.all(np.isfinite(surface_loading)):
        raise SimulationError("Film/surface equilibrium root did not converge")
    film_side = film_coefficient_m_s * (bulk - surface)
    solid_side = conductance * (surface_loading - outer_loading)
    # Choose the expression with the smaller absolute cancellation/error scale.
    # A shared but poorly conditioned film-side flux can conserve mass while being
    # physically inaccurate when the film resistance tends to zero.
    film_scale = film_coefficient_m_s * (np.abs(bulk) + np.abs(surface))
    solid_scale = conductance * (np.abs(surface_loading) + np.abs(outer_loading))
    return np.asarray(np.where(film_scale <= solid_scale, film_side, solid_side))

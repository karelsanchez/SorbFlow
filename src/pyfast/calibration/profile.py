"""Experimental known-sigma Gaussian profiles on an explicit physical grid.

Finite multi-start searches and asymptotic cutoffs never establish global
identifiability. See docs/profile_likelihood.md for the observation contract.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike
from scipy.optimize import least_squares
from scipy.stats import chi2

from .._arrays import FloatArray, real_array
from ..units import finite_scalar, quantity

WeightedResidual = Callable[[FloatArray], ArrayLike]
EdgeStatus = Literal["REJECTED", "GRID_TRUNCATED", "BOUND_LIMITED", "UNAVAILABLE"]


@dataclass(frozen=True, slots=True)
class ProfileParameter:
    """Positive physical coordinate; unit metadata never converts magnitudes."""

    name: str
    unit: str
    lower: float
    upper: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Parameter name must be nonempty")
        quantity(1.0, self.unit)
        lower = finite_scalar(self.lower, "lower")
        upper = finite_scalar(self.upper, "upper")
        if not 0 < lower < upper or not np.log(lower) < np.log(upper):
            raise ValueError("Bounds must satisfy 0 < lower < upper in log coordinates")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)


@dataclass(frozen=True, slots=True)
class ProfileTrial:
    """One attempted optimization, including failed and budget-skipped starts."""

    start: tuple[float, ...]
    parameters: tuple[float, ...] | None
    chi2: float | None
    success: bool
    status: str
    message: str
    callback_calls: int
    bound_parameters: tuple[str, ...]
    lowest_evaluated_chi2: float | None = None


@dataclass(frozen=True, slots=True)
class ProfilePoint:
    value: float
    trials: tuple[ProfileTrial, ...]
    parameters: tuple[float, ...] | None
    chi2: float | None
    delta_chi2: float | None
    accepted: bool | None
    bound_limited: bool


@dataclass(frozen=True, slots=True)
class GaussianProfile:
    """Grid evidence only: accepted_grid is not a continuous confidence interval."""

    parameters: tuple[ProfileParameter, ...]
    parameter_name: str
    confidence: float
    cutoff: float
    baseline_trials: tuple[ProfileTrial, ...]
    baseline_parameters: tuple[float, ...] | None
    baseline_chi2: float | None
    points: tuple[ProfilePoint, ...]
    accepted_grid: tuple[float, ...]
    edge_status: tuple[EdgeStatus, EdgeStatus]
    callback_calls: int
    budget_exhausted: bool
    baseline_inconsistent: bool
    status: str
    edge_diagnostics: tuple[str, str] = ("UNAVAILABLE", "UNAVAILABLE")
    requested_grid: tuple[float, ...] = ()
    bound_log_tolerance: float = 1e-7


class _BudgetExhausted(RuntimeError):
    pass


@dataclass
class _Evaluator:
    callback: WeightedResidual
    limit: int | None
    calls: int = 0
    size: int | None = None
    exhausted: bool = False
    lowest_chi2: float | None = None

    def __call__(self, values: FloatArray) -> FloatArray:
        if self.limit is not None and self.calls >= self.limit:
            self.exhausted = True
            raise _BudgetExhausted("Global callback budget exhausted")
        readonly = np.array(values, dtype=np.float64, copy=True)
        readonly.setflags(write=False)
        self.calls += 1
        residual = real_array(self.callback(readonly), "weighted residual")
        if residual.ndim != 1 or not residual.size:
            raise ValueError("Weighted residual must be a nonempty 1D vector")
        if self.size is not None and residual.size != self.size:
            raise ValueError("Weighted residual length changed")
        self.size = residual.size
        with np.errstate(over="ignore", invalid="ignore"):
            score = float(np.dot(residual, residual))
        if np.isfinite(score):
            self.lowest_chi2 = score if self.lowest_chi2 is None else min(self.lowest_chi2, score)
        return residual


def _bounds_at(
    values: FloatArray, specs: tuple[ProfileParameter, ...], tolerance: float,
) -> tuple[str, ...]:
    return tuple(spec.name for value, spec in zip(values, specs, strict=True)
                 if abs(np.log(value) - np.log(spec.lower)) <= tolerance
                 or abs(np.log(value) - np.log(spec.upper)) <= tolerance)


def _trial(
    evaluate: _Evaluator,
    specs: tuple[ProfileParameter, ...],
    start: FloatArray,
    max_nfev: int,
    fixed: tuple[int, float] | None,
    bound_log_tolerance: float,
) -> ProfileTrial:
    initial = start.copy()
    if fixed is not None:
        initial[fixed[0]] = fixed[1]
    indices = [i for i in range(len(specs)) if fixed is None or i != fixed[0]]
    lower = np.array([specs[i].lower for i in indices])
    upper = np.array([specs[i].upper for i in indices])
    count = evaluate.calls
    last_values: FloatArray | None = None
    last_chi2: float | None = None
    lowest_chi2: float | None = None
    active_names: tuple[str, ...] = ()

    def residual(log_values: FloatArray) -> FloatArray:
        nonlocal last_values, last_chi2, lowest_chi2
        values = initial.copy()
        values[indices] = np.clip(np.exp(log_values), lower, upper)
        r = evaluate(values)
        with np.errstate(over="ignore", invalid="ignore"):
            objective = float(np.dot(r, r))
        if not np.isfinite(objective):
            raise ValueError("Sum of squared residuals is not finite")
        last_values, last_chi2 = values, objective
        lowest_chi2 = objective if lowest_chi2 is None else min(lowest_chi2, objective)
        return r

    try:
        if indices:
            fitted = least_squares(
                residual, np.log(initial[indices]), bounds=(np.log(lower), np.log(upper)),
                jac="3-point", max_nfev=max_nfev, ftol=1e-10, xtol=1e-10, gtol=1e-10,
            )
            values = initial.copy()
            values[indices] = np.clip(np.exp(fitted.x), lower, upper)
            objective = float(np.dot(fitted.fun, fitted.fun))
            success = bool(fitted.success)
            active_names = tuple(specs[i].name for i, mask in zip(
                indices, fitted.active_mask, strict=True) if mask != 0)
            status, message = ("CONVERGED" if success else "OPTIMIZER_FAILED"), str(fitted.message)
        else:
            residual(np.empty(0))
            assert last_chi2 is not None
            values, objective = initial, last_chi2
            success, status, message = True, "EVALUATED", "No nuisance parameters"
    except Exception as exc:
        return ProfileTrial(
            tuple(initial), None if last_values is None else tuple(last_values), last_chi2,
            False, "BUDGET_EXHAUSTED" if isinstance(exc, _BudgetExhausted) else "ERROR",
            f"{type(exc).__name__}: {exc}", evaluate.calls - count,
            () if last_values is None else _bounds_at(last_values, specs, bound_log_tolerance),
            lowest_chi2,
        )
    return ProfileTrial(tuple(initial), tuple(values), objective, success, status, message,
                        evaluate.calls - count,
                        tuple(dict.fromkeys((
                            *_bounds_at(values, specs, bound_log_tolerance), *active_names))),
                        lowest_chi2)


def _best(trials: tuple[ProfileTrial, ...]) -> ProfileTrial | None:
    valid = [trial for trial in trials if trial.success and trial.chi2 is not None]
    return min(
        valid, key=lambda trial: trial.chi2 if trial.chi2 is not None else np.inf,
    ) if valid else None


def profile_gaussian_known_sigma(
    weighted_residual: WeightedResidual,
    parameters: Sequence[ProfileParameter],
    starts: ArrayLike,
    *,
    parameter: str,
    grid: ArrayLike,
    confidence: float = 0.95,
    max_nfev: int = 200,
    max_callback_calls: int | None = None,
    baseline_tolerance: float = 1e-6,
    bound_log_tolerance: float = 1e-7,
) -> GaussianProfile:
    """Reoptimize nuisance on a supplied grid, recording every multi-start attempt.

    Errors in configuration raise ValueError; evaluator/optimizer errors are
    retained as trials. The hard budget counts actual callback invocations, not
    scipy nfev or physical solves inside the callback. Sigma must be known.
    """
    specs = tuple(parameters)
    if not specs or not all(isinstance(spec, ProfileParameter) for spec in specs):
        raise ValueError("parameters must contain ProfileParameter instances")
    names = tuple(spec.name for spec in specs)
    if len(set(names)) != len(names) or parameter not in names:
        raise ValueError("Names must be unique and parameter must be present")
    if not callable(weighted_residual):
        raise ValueError("weighted_residual must be callable")
    confidence = finite_scalar(confidence, "confidence")
    tolerance = finite_scalar(baseline_tolerance, "baseline_tolerance")
    bound_log_tolerance = finite_scalar(bound_log_tolerance, "bound_log_tolerance")
    if bound_log_tolerance < 0:
        raise ValueError("bound_log_tolerance must be nonnegative")
    if not 0 < confidence < 1 or tolerance < 0:
        raise ValueError("Require 0 < confidence < 1 and nonnegative baseline_tolerance")
    if type(max_nfev) is not int or max_nfev < 1:
        raise ValueError("max_nfev must be a positive integer")
    if max_callback_calls is not None and (
        type(max_callback_calls) is not int or max_callback_calls < 1
    ):
        raise ValueError("max_callback_calls must be a positive integer or None")
    initial = real_array(starts, "starts")
    lower = np.array([spec.lower for spec in specs])
    upper = np.array([spec.upper for spec in specs])
    if initial.ndim != 2 or initial.shape[1] != len(specs) or not initial.shape[0]:
        raise ValueError("starts must have shape (n_starts, n_parameters), n_starts > 0")
    if np.any(initial < lower) or np.any(initial > upper):
        raise ValueError("starts must lie inside physical bounds")
    index = names.index(parameter)
    values = real_array(grid, "grid")
    if values.ndim != 1 or not values.size or np.any(np.diff(values) <= 0):
        raise ValueError("grid must be a nonempty strictly increasing 1D vector")
    requested_grid = tuple(float(value) for value in values)
    values = values.copy()
    # Canonicalize endpoint roundoff only; do not use the proximity diagnostic tolerance.
    for bound in (lower[index], upper[index]):
        rounding = 4 * abs(np.spacing(bound))
        values[np.abs(values - bound) <= rounding] = bound
    if np.any(np.diff(values) <= 0):
        raise ValueError("grid has duplicate points after endpoint rounding")
    if np.any(values < lower[index]) or np.any(values > upper[index]):
        raise ValueError("grid must lie inside physical bounds")

    evaluate = _Evaluator(weighted_residual, max_callback_calls)
    baseline_trials = tuple(
        _trial(evaluate, specs, start, max_nfev, None, bound_log_tolerance)
        for start in initial
    )
    baseline = _best(baseline_trials)
    profiled: list[tuple[float, tuple[ProfileTrial, ...], ProfileTrial | None]] = []
    for value in values:
        trials = (() if baseline is None else tuple(
            _trial(evaluate, specs, start, max_nfev, (index, float(value)), bound_log_tolerance)
            for start in initial
        ))
        profiled.append((float(value), trials, _best(trials)))
    reference = None if baseline is None else baseline.chi2
    inconsistent = (reference is not None and evaluate.lowest_chi2 is not None
                    and evaluate.lowest_chi2 < reference - tolerance)
    cutoff = float(chi2.ppf(confidence, 1))
    points: list[ProfilePoint] = []
    for value, trials, best in profiled:
        score = None if best is None else best.chi2
        delta = None if score is None or reference is None else score - reference
        accepted = None if delta is None or inconsistent else delta <= cutoff
        at_bound = value in (specs[index].lower, specs[index].upper)
        nuisance_bound = best is not None and any(
            name != parameter for name in best.bound_parameters
        )
        points.append(ProfilePoint(value, trials, None if best is None else best.parameters,
                                   score, delta, accepted, at_bound or nuisance_bound))

    def edge(point: ProfilePoint, physical_bound: float) -> EdgeStatus:
        if point.accepted is None:
            return "UNAVAILABLE"
        if not point.accepted:
            return "REJECTED"
        return "BOUND_LIMITED" if point.value == physical_bound else "GRID_TRUNCATED"

    status = ("BASELINE_INCONSISTENT" if inconsistent else
              "BUDGET_EXHAUSTED" if evaluate.exhausted else
              "BASELINE_FAILED" if baseline is None else
              "INCOMPLETE" if any(point.chi2 is None for point in points) else "COMPLETE")

    def diagnostic(point: ProfilePoint, physical_bound: float) -> str:
        coarse = edge(point, physical_bound)
        best = _best(point.trials)
        nuisance = best is not None and any(name != parameter for name in best.bound_parameters)
        return f"{coarse}_WITH_NUISANCE_BOUND_EVIDENCE" if nuisance else coarse

    return GaussianProfile(
        specs, parameter, confidence, cutoff, baseline_trials,
        None if baseline is None else baseline.parameters, reference, tuple(points),
        tuple(point.value for point in points if point.accepted),
        (edge(points[0], float(lower[index])), edge(points[-1], float(upper[index]))),
        evaluate.calls, evaluate.exhausted,
        inconsistent, status,
        (diagnostic(points[0], float(lower[index])),
         diagnostic(points[-1], float(upper[index]))), requested_grid, bound_log_tolerance,
    )

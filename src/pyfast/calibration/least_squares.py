"""Initial inverse workflows with explicit local identifiability diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import ArrayLike
from scipy.optimize import least_squares

from .._arrays import FloatArray, nonnegative_array
from ..equilibrium import isotherm_from_parameters
from ..reactors.batch import simulate_batch
from ..schemas import LDF, BatchConfig, Freundlich, Langmuir, Linear, Observations
from ..solvers import SolverOptions

Parameters = Langmuir | Freundlich | Linear | LDF


class FitError(RuntimeError):
    """The inverse problem did not converge or left the numerical model domain."""


@dataclass(frozen=True, slots=True, kw_only=True)
class FitResult:
    """Local least-squares evidence, never a declaration of global identifiability.

    Covariance is in log-parameter coordinates. With known measurement sigma it
    assumes that error model; otherwise residual variance is estimated from DOF.
    """

    parameters: Parameters
    parameter_names: tuple[str, ...]
    predicted: FloatArray
    residuals: FloatArray
    singular_values: FloatArray
    covariance_log_parameters: FloatArray | None
    jacobian_rank: int
    jacobian_condition: float
    locally_identifiable: bool
    nfev: int

    def __post_init__(self) -> None:
        for name in ("predicted", "residuals", "singular_values", "covariance_log_parameters"):
            array = getattr(self, name)
            if array is not None:
                value = np.array(array, dtype=np.float64, copy=True)
                value.setflags(write=False)
                object.__setattr__(self, name, value)


def _fit(
    measured: FloatArray,
    initial: FloatArray,
    names: tuple[str, ...],
    build: Callable[[FloatArray], Parameters],
    predict: Callable[[Parameters], FloatArray],
    std: ArrayLike | None,
    max_nfev: int,
    diff_step: float | None = None,
) -> FitResult:
    if type(max_nfev) is not int or max_nfev < 1:
        raise ValueError("max_nfev must be a positive integer")
    if measured.ndim != 1 or measured.size <= initial.size:
        raise ValueError("More observations than fitted parameters are required")
    if np.any(initial <= 0):
        raise ValueError("Fitted parameters must start strictly positive")
    if std is None:
        sigma = np.full_like(measured, max(float(np.max(np.abs(measured))), 1e-30))
    else:
        sigma = nonnegative_array(std, "standard deviation")
        if sigma.shape != measured.shape or np.any(sigma == 0):
            raise ValueError("Positive standard deviations must match measurements")

    def residual(log_parameters: FloatArray) -> FloatArray:
        with np.errstate(over="raise", invalid="raise"):
            parameters = build(np.exp(log_parameters))
        return np.asarray((predict(parameters) - measured) / sigma)

    try:
        fitted = least_squares(
            residual,
            np.log(initial),
            method="trf",
            jac="3-point",
            x_scale="jac",
            diff_step=None if diff_step is None else np.asarray(diff_step),
            max_nfev=max_nfev,
            ftol=1e-10,
            xtol=1e-10,
            gtol=1e-10,
        )
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise FitError(f"Fit left the supported numerical domain: {exc}") from exc
    if not fitted.success:
        raise FitError(f"Fit did not converge: {fitted.message}")
    parameters = build(np.exp(fitted.x))
    predicted = predict(parameters)
    jacobian = np.asarray(fitted.jac)
    _, singular, vt = np.linalg.svd(jacobian, full_matrices=False)
    threshold = np.finfo(float).eps * max(jacobian.shape) * singular[0]
    rank = int(np.sum(singular > threshold))
    condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else float("inf")
    identified = rank == initial.size and condition <= 1e8
    covariance = None
    if identified:
        covariance = (vt.T / singular**2) @ vt
        if std is None:
            covariance *= float(np.dot(fitted.fun, fitted.fun) / (measured.size - initial.size))
    return FitResult(
        parameters=parameters,
        parameter_names=names,
        predicted=predicted,
        residuals=predicted - measured,
        singular_values=singular,
        covariance_log_parameters=covariance,
        jacobian_rank=rank,
        jacobian_condition=condition,
        locally_identifiable=identified,
        nfev=fitted.nfev,
    )


def fit_isotherm(
    concentration_kg_m3: ArrayLike,
    loading_kg_kg: ArrayLike,
    initial: Langmuir | Freundlich | Linear,
    *,
    std_loading_kg_kg: ArrayLike | None = None,
    max_nfev: int = 1000,
) -> FitResult:
    """Fit one equilibrium model at a fixed, common experimental temperature.

    All values are SI. Concentration error, censoring, mixtures and thermal effects
    are not handled here. Freundlich c_ref stays fixed to avoid redundant parameters.
    """
    c = nonnegative_array(concentration_kg_m3, "concentration_kg_m3")
    q = nonnegative_array(loading_kg_kg, "loading_kg_kg")
    if c.ndim != 1 or c.shape != q.shape or c.size == 0:
        raise ValueError("Matched one-dimensional equilibrium data are required")
    names: tuple[str, ...]
    if isinstance(initial, Langmuir):
        values = np.array([initial.qmax_kg_kg, initial.affinity_m3_kg])
        names = ("qmax_kg_kg", "affinity_m3_kg")

        def build(values: FloatArray) -> Parameters:
            return Langmuir(qmax_kg_kg=float(values[0]), affinity_m3_kg=float(values[1]))
    elif isinstance(initial, Freundlich):
        reference = initial.c_ref_kg_m3
        values = np.array([initial.q_ref_kg_kg, initial.exponent])
        names = ("q_ref_kg_kg", "exponent")

        def build(values: FloatArray) -> Parameters:
            return Freundlich(
                q_ref_kg_kg=float(values[0]), exponent=float(values[1]), c_ref_kg_m3=reference
            )
    elif isinstance(initial, Linear):
        values = np.array([initial.distribution_m3_kg])
        names = ("distribution_m3_kg",)

        def build(values: FloatArray) -> Parameters:
            return Linear(distribution_m3_kg=float(values[0]))
    else:
        raise ValueError("Unsupported equilibrium model")

    def predict(parameters: Parameters) -> FloatArray:
        if isinstance(parameters, LDF):
            raise ValueError("An equilibrium model is required")
        return isotherm_from_parameters(parameters).loading(c)

    return _fit(q, values, names, build, predict, std_loading_kg_kg, max_nfev)


def fit_batch_rate(
    config: BatchConfig, observations: Observations, *, max_nfev: int = 100
) -> FitResult:
    """Estimate only k_LDF with all other physical parameters treated as known.

    This does not identify separate film and surface diffusion coefficients.
    Observations must include zero and the full configured simulation duration.
    """
    if observations.species_name != config.species.name:
        raise ValueError("Observation species does not match the problem")
    times = np.asarray(observations.time_s)
    measured = np.asarray(observations.concentration_kg_m3)
    options = SolverOptions(rtol=1e-9, atol_concentration_kg_m3=1e-13, atol_loading_kg_kg=1e-15)

    def build(values: FloatArray) -> Parameters:
        return LDF(rate_s_inv=float(values[0]))

    def predict(parameters: Parameters) -> FloatArray:
        if not isinstance(parameters, LDF):
            raise ValueError("LDF rate parameters required")
        result = simulate_batch(replace(config, kinetics=parameters), time_s=times, options=options)
        return result.outlet_concentration_kg_m3

    return _fit(
        measured,
        np.array([config.kinetics.rate_s_inv]),
        ("rate_s_inv",),
        build,
        predict,
        observations.std_kg_m3,
        max_nfev,
        diff_step=1e-4,
    )

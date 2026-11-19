"""Thin integration boundary; model equations and conservation live in reactors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import csc_matrix

from .._arrays import FloatArray
from .options import SolverOptions


class SimulationError(RuntimeError):
    """Integration, physical-state or conservation checks failed; no success result."""


@dataclass(frozen=True, slots=True)
class IntegrationOutput:
    samples: FloatArray
    checkpoints: FloatArray
    nfev: int
    njev: int
    nlu: int
    accepted_steps: int


def integrate(
    rhs: Callable[[float, FloatArray], FloatArray],
    initial: FloatArray,
    times: FloatArray,
    atol: FloatArray,
    options: SolverOptions,
    sparsity: csc_matrix | None = None,
) -> IntegrationOutput:
    """Retain internal accepted states as well as dense output for diagnostics."""
    try:
        solution = solve_ivp(
            rhs,
            (0, float(times[-1])),
            initial,
            method=options.method,
            rtol=options.rtol,
            atol=atol,
            dense_output=True,
            max_step=np.inf if options.max_step_s is None else options.max_step_s,
            jac_sparsity=sparsity,
        )
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise SimulationError(f"Integration failed: {exc}") from exc
    if not solution.success or solution.sol is None:
        raise SimulationError(f"Integrator did not complete: {solution.message}")
    sampled = np.asarray(solution.sol(times), dtype=np.float64)
    checkpoints = np.concatenate((solution.y, sampled), axis=1)
    if not np.all(np.isfinite(checkpoints)):
        raise SimulationError("Nonfinite integration state")
    return IntegrationOutput(
        sampled, checkpoints, solution.nfev, solution.njev, solution.nlu, solution.t.size - 1
    )

"""Thin integration boundary; model equations and conservation live in reactors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import BDF, Radau, solve_ivp
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


@dataclass(frozen=True, slots=True)
class StreamingIntegrationOutput:
    """Requested samples and counters; internal states are consumed by a callback."""

    samples: FloatArray
    nfev: int
    njev: int
    nlu: int
    accepted_steps: int


STREAMING_METHODS = {"BDF": BDF, "Radau": Radau}
StateCallback = Callable[[FloatArray, str, int, float], None]


def integrate(
    rhs: Callable[[float, FloatArray], FloatArray],
    initial: FloatArray,
    times: FloatArray,
    atol: FloatArray,
    options: SolverOptions,
    sparsity: csc_matrix | None = None,
    jac: Callable[[float, FloatArray], csc_matrix] | None = None,
) -> IntegrationOutput:
    """Retain internal accepted states as well as dense output for diagnostics."""
    if options.history != "dense":
        raise ValueError("Streaming history is not implemented for this reactor/model")
    if options.jacobian == "analytic" and jac is None:
        raise ValueError("Analytic Jacobian is not implemented for this reactor/model")
    jac_options = {"jac_sparsity": sparsity} if jac is None else {"jac": jac}
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
            **jac_options,
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


def integrate_streaming(
    rhs: Callable[[float, FloatArray], FloatArray],
    initial: FloatArray,
    times: FloatArray,
    atol: FloatArray,
    options: SolverOptions,
    sparsity: csc_matrix | None = None,
    jac: Callable[[float, FloatArray], csc_matrix] | None = None,
    on_state: StateCallback | None = None,
) -> StreamingIntegrationOutput:
    """Consume every accepted state and discard each dense interpolant after sampling.

    The caller must accumulate physical diagnostics through on_state, then consume
    returned samples. Samples have Fortran layout, matching solve_ivp's OdeSolution.
    BDF assigns an exact internal boundary to the next segment, Radau to the previous
    one; this mirrors solve_ivp's alt_segment selection without retaining its history.
    Callback state arrays are transient and must not be mutated or retained without
    copying. No scipy private integration interfaces are used.
    """
    if options.jacobian == "analytic" and jac is None:
        raise ValueError("Analytic Jacobian is not implemented for this reactor/model")
    if times.ndim != 1 or times.size < 2 or times[0] != 0:
        raise ValueError("Streaming times must start at zero and contain at least two points")
    if not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0):
        raise ValueError("Streaming times must be finite and strictly increasing")
    jac_options = {"jac_sparsity": sparsity} if jac is None else {"jac": jac}
    samples = np.empty((initial.size, times.size), dtype=np.float64, order="F")
    ptr, steps = 0, 0
    finite_states = bool(np.all(np.isfinite(initial)))
    try:
        solver = STREAMING_METHODS[options.method](
            rhs, float(0), initial, float(times[-1]), vectorized=False,
            rtol=options.rtol, atol=atol,
            max_step=np.inf if options.max_step_s is None else options.max_step_s,
            **jac_options,
        )
        if on_state is not None:
            on_state(initial, "accepted", 0, float(0))
        while solver.status == "running":
            message = solver.step()
            if solver.status == "failed":
                raise SimulationError(f"Integrator did not complete: {message}")
            interpolant = solver.dense_output()
            start = ptr
            if options.method == "BDF":
                # The last segment additionally owns the final integration time.
                while ptr < times.size and (
                    times[ptr] < solver.t
                    or (solver.status == "finished" and times[ptr] <= solver.t)
                ):
                    ptr += 1
            else:
                while ptr < times.size and times[ptr] <= solver.t:
                    ptr += 1
            if ptr > start:
                samples[:, start:ptr] = interpolant(times[start:ptr])
            del interpolant
            steps += 1
            finite_states = finite_states and bool(np.all(np.isfinite(solver.y)))
            if on_state is not None:
                on_state(solver.y, "accepted", steps, float(solver.t))
    except (ValueError, FloatingPointError, OverflowError) as exc:
        raise SimulationError(f"Integration failed: {exc}") from exc
    if ptr != times.size:
        raise SimulationError(f"Streaming sampler assigned {ptr} of {times.size} requested times")
    if not finite_states or not np.all(np.isfinite(samples)):
        raise SimulationError("Nonfinite integration state")
    return StreamingIntegrationOutput(samples, solver.nfev, solver.njev, solver.nlu, steps)

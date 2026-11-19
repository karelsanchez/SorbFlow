"""Optional NSGA-II orchestration; the evolutionary engine is pymoo, not FAST."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from .._arrays import FloatArray, real_array


class OptimizationError(RuntimeError):
    """No valid feasible solution, or an invalid objective evaluation."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Evaluation:
    """All objectives are minimized; normalized inequality constraints satisfy g<=0."""

    objectives: ArrayLike
    constraints: ArrayLike = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ParetoResult:
    decisions_si: FloatArray
    objectives_si: FloatArray
    normalized_constraints: FloatArray
    evaluations: int
    seed: int
    specification_json: str

    def __post_init__(self) -> None:
        for name in ("decisions_si", "objectives_si", "normalized_constraints"):
            array = np.array(getattr(self, name), dtype=np.float64, copy=True)
            array.setflags(write=False)
            object.__setattr__(self, name, array)


def nsga2(
    evaluate: Callable[[FloatArray], Evaluation],
    lower_bounds_si: ArrayLike,
    upper_bounds_si: ArrayLike,
    *,
    objective_units: tuple[str, ...],
    variable_units: tuple[str, ...],
    problem_id: str,
    seed: int,
    n_constraints: int = 0,
    population_size: int = 80,
    generations: int = 100,
) -> ParetoResult:
    """Find a feasible nondominated approximation and re-evaluate every returned point.

    Requires the optional 'optimize' extra. User supplies units, SI bounds, all
    objectives to minimize, and scaled g<=0 constraints. Use a frozen common set
    of uncertainty scenarios for robust objectives. No global optimum is certified.
    problem_id must reference the versioned evaluator and all fixed physical inputs.
    """
    low, high = (
        real_array(lower_bounds_si, "lower bounds"),
        real_array(upper_bounds_si, "upper bounds"),
    )
    if low.ndim != 1 or not low.size or low.shape != high.shape or np.any(high <= low):
        raise ValueError("Matched nonempty bounds with upper>lower are required")
    if len(variable_units) != low.size or len(objective_units) < 2:
        raise ValueError("Units must name every variable and at least two objectives")
    if any(
        not isinstance(unit, str) or not unit.strip()
        for unit in (*variable_units, *objective_units)
    ):
        raise ValueError("Units must be nonempty strings")
    for name, value, minimum in (
        ("population_size", population_size, 4),
        ("generations", generations, 2),
        ("n_constraints", n_constraints, 0),
    ):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be an integer >={minimum}")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be an unsigned 32-bit integer")
    if not isinstance(problem_id, str) or not problem_id.strip():
        raise ValueError("problem_id must identify the versioned physical problem")
    try:
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import ElementwiseProblem
        from pymoo.optimize import minimize
    except ImportError as exc:
        raise ImportError("Install pyfast-adsorption[optimize] to use NSGA-II") from exc

    def checked(x: FloatArray) -> tuple[FloatArray, FloatArray]:
        output = evaluate(x.copy())
        if not isinstance(output, Evaluation):
            raise OptimizationError("Evaluator must return Evaluation")
        f = real_array(output.objectives, "objectives")
        g = real_array(output.constraints, "constraints")
        if f.shape != (len(objective_units),) or g.shape != (n_constraints,):
            raise OptimizationError("Objective or constraint shape does not match the problem")
        return f, g

    class Problem(ElementwiseProblem):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__(
                n_var=low.size,
                n_obj=len(objective_units),
                n_ieq_constr=n_constraints,
                xl=low,
                xu=high,
            )

        def _evaluate(self, x: FloatArray, out: dict[str, Any], *args: Any, **kwargs: Any) -> None:
            f, g = checked(x)
            out["F"], out["G"] = f, g

    result = minimize(
        Problem(),
        NSGA2(pop_size=population_size, eliminate_duplicates=True),
        ("n_gen", generations),
        seed=seed,
        verbose=False,
    )
    if result.X is None or result.F is None:
        raise OptimizationError("No feasible nondominated solutions were found")
    decisions = real_array(np.atleast_2d(result.X), "Pareto decisions")
    verified = [checked(x) for x in decisions]
    objectives = np.stack([v[0] for v in verified])
    constraints = np.stack([v[1] for v in verified])
    if np.any(decisions < low) or np.any(decisions > high) or np.any(constraints > 0):
        raise OptimizationError("Returned Pareto points fail physical constraints or bounds")
    if not np.allclose(objectives, result.F, rtol=1e-10, atol=1e-12):
        raise OptimizationError("Evaluator is not repeatable; freeze uncertainty scenarios")
    specification = json.dumps(
        {
            "problem_id": problem_id,
            "seed": seed,
            "algorithm": "pymoo.NSGA2",
            "pymoo_version": version("pymoo"),
            "population_size": population_size,
            "generations": generations,
            "lower_bounds_si": low.tolist(),
            "upper_bounds_si": high.tolist(),
            "variable_units": variable_units,
            "objective_units": objective_units,
            "n_constraints": n_constraints,
        },
        sort_keys=True,
        allow_nan=False,
    )
    return ParetoResult(
        decisions_si=decisions,
        objectives_si=objectives,
        normalized_constraints=constraints,
        evaluations=int(result.algorithm.evaluator.n_eval) + len(verified),
        seed=seed,
        specification_json=specification,
    )

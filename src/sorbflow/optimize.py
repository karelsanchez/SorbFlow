"""Public multiobjective API. The NSGA-II engine is an optional dependency."""

from .optimization.nsga2 import Evaluation, OptimizationError, ParetoResult, nsga2

__all__ = ["Evaluation", "OptimizationError", "ParetoResult", "nsga2"]

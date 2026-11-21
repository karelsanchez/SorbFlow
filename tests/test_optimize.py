import json

import numpy as np
import pytest
from numpy.testing import assert_allclose

from sorbflow.optimize import Evaluation, OptimizationError, nsga2

pytest.importorskip("pymoo")


def optimize(evaluate, **kwargs):
    settings = dict(
        objective_units=("1", "1"),
        variable_units=("1",),
        problem_id="analytic-constrained-biobjective-v1",
        seed=42,
        n_constraints=2,
        population_size=40,
        generations=20,
    )
    return nsga2(evaluate, [-1], [2], **(settings | kwargs))


def model(x):
    return Evaluation(objectives=[x[0] ** 2, (x[0] - 1) ** 2], constraints=[0.2 - x[0], x[0] - 0.8])


def test_constrained_nsga2_known_pareto_front_and_repeatability():
    a, b = optimize(model), optimize(model)
    assert_allclose(a.decisions_si, b.decisions_si, atol=0, rtol=0)
    assert np.all(a.normalized_constraints <= 0)
    assert np.ptp(a.decisions_si[:, 0]) > 0.5
    assert_allclose(a.objectives_si[:, 0], a.decisions_si[:, 0] ** 2)
    assert_allclose(a.objectives_si[:, 1], (a.decisions_si[:, 0] - 1) ** 2)
    assert json.loads(a.specification_json)["seed"] == 42
    assert a.evaluations > 800


def test_nsga2_infeasible_and_wrong_evaluator():
    with pytest.raises(OptimizationError, match="No feasible"):
        optimize(lambda x: Evaluation(objectives=[x[0], -x[0]], constraints=[1, 1]))
    with pytest.raises(OptimizationError, match="Evaluation"):
        optimize(lambda x: [1, 2])
    with pytest.raises(OptimizationError, match="shape"):
        optimize(lambda x: Evaluation(objectives=[1], constraints=[0, 0]))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"population_size": 3},
        {"generations": 1},
        {"seed": True},
        {"seed": -1},
        {"n_constraints": -1},
        {"problem_id": ""},
        {"variable_units": ()},
        {"objective_units": ("1",)},
        {"objective_units": ("", "1")},
    ],
)
def test_invalid_optimizer_settings(kwargs):
    with pytest.raises(ValueError):
        optimize(model, **kwargs)

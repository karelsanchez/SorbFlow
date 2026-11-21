import numpy as np
import pytest
from numpy.testing import assert_allclose

from sorbflow.uncertainty import local_sensitivity, monte_carlo


def test_monte_carlo_linear_gaussian_reference_and_reproducibility():
    def sampler(rng, n):
        return rng.multivariate_normal([1, 2], [[1, 0.5], [0.5, 4]], size=n)

    def evaluate(x):
        return [x[0] + 2 * x[1]]

    a = monte_carlo(evaluate, sampler, n_samples=20000, seed=42, model_id="analytic-linear-v1")
    b = monte_carlo(evaluate, sampler, n_samples=20000, seed=42, model_id="analytic-linear-v1")
    # Analytic mean=5 and variance=1+4*4+4*0.5=19.
    assert abs(a.mean[0] - 5) < 4 * a.standard_error_mean[0]
    assert a.standard_deviation[0] ** 2 == pytest.approx(19, rel=0.04)
    assert a.quantiles.shape == (3, 1)
    assert a.samples_sha256 == b.samples_sha256
    assert_allclose(a.outputs_si, b.outputs_si, rtol=0, atol=0)
    with pytest.raises(ValueError):
        a.inputs_si[0, 0] = 10


def test_sampler_failure_not_conditioned_on_survivors():
    def broken(x):
        if x[0] > 0.5:
            raise ValueError("physical infeasibility")
        return x[0]

    with pytest.raises(RuntimeError, match="sample 1"):
        monte_carlo(broken, lambda rng, n: [[0], [1]], n_samples=2, seed=0, model_id="test")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_samples": 1},
        {"seed": True},
        {"seed": -1},
        {"model_id": ""},
        {"probabilities": [0.5, 0.5]},
        {"probabilities": [-1, 1]},
    ],
)
def test_bad_monte_carlo_settings(kwargs):
    defaults = dict(n_samples=2, seed=0, model_id="test") | kwargs
    with pytest.raises(ValueError):
        monte_carlo(lambda x: x, lambda rng, n: np.zeros((n, 1)), **defaults)


def test_bad_sampler_output_shape():
    with pytest.raises(ValueError):
        monte_carlo(lambda x: x, lambda rng, n: [1, 2], n_samples=2, seed=0, model_id="test")


def test_central_sensitivity_known_polynomial_and_shape_errors():
    derivative = local_sensitivity(
        lambda x: [x[0] ** 2 + 3 * x[1], x[0] * x[1]], [2, 4], [1e-4, 1e-4]
    )
    assert_allclose(derivative, [[4, 3], [4, 2]], rtol=1e-9)
    with pytest.raises(ValueError):
        local_sensitivity(lambda x: x, [1, 2], [0, 1])
    with pytest.raises(ValueError):
        local_sensitivity(lambda x: [1] if x[0] > 1 else [1, 2], [1], [1e-3])

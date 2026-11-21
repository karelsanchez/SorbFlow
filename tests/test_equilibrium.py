import numpy as np
import pytest
from numpy.testing import assert_allclose

from sorbflow import Freundlich, Langmuir, Linear
from sorbflow.equilibrium import isotherm_from_parameters


@pytest.mark.parametrize(
    "parameters,expected",
    [
        (Langmuir(qmax_kg_kg=0.1, affinity_m3_kg=2), [0, 0.05, 0.08]),
        (Freundlich(q_ref_kg_kg=0.1, c_ref_kg_m3=0.5, exponent=0.5), [0, 0.1, 0.2]),
        (Linear(distribution_m3_kg=0.2), [0, 0.1, 0.4]),
    ],
)
def test_known_equilibria_and_scalar_shape(parameters, expected):
    model = isotherm_from_parameters(parameters)
    assert_allclose(model.loading([0, 0.5, 2]), expected)
    assert model.loading(0.5).shape == ()
    assert model.loading([[0, 0.5], [2, 3]]).shape == (2, 2)


@pytest.mark.parametrize(
    "parameters",
    [
        Langmuir(qmax_kg_kg=0.1, affinity_m3_kg=2),
        Freundlich(q_ref_kg_kg=0.1, c_ref_kg_m3=0.5, exponent=0.5),
        Freundlich(q_ref_kg_kg=0.1, c_ref_kg_m3=0.5, exponent=1.5),
        Linear(distribution_m3_kg=0.2),
    ],
)
def test_derivative_against_central_difference(parameters):
    model = isotherm_from_parameters(parameters)
    c = np.array([0.01, 0.1, 1, 10])
    h = c * 1e-5
    reference = (model.loading(c + h) - model.loading(c - h)) / (2 * h)
    assert_allclose(model.derivative(c), reference, rtol=1e-7)


@pytest.mark.parametrize("exponent,expected", [(1, 0.2), (2, 0)])
def test_freundlich_derivative_zero_limits(exponent, expected):
    model = isotherm_from_parameters(
        Freundlich(q_ref_kg_kg=0.1, c_ref_kg_m3=0.5, exponent=exponent)
    )
    assert float(model.derivative(0)) == pytest.approx(expected)


def test_singular_derivative_is_not_silently_regularized():
    model = isotherm_from_parameters(Freundlich(q_ref_kg_kg=0.1, c_ref_kg_m3=0.5, exponent=0.5))
    assert float(model.loading(0)) == 0
    with pytest.raises(ValueError, match="singular"):
        model.derivative([0, 1])


def test_extreme_langmuir_avoids_intermediate_overflow():
    model = isotherm_from_parameters(Langmuir(qmax_kg_kg=1e100, affinity_m3_kg=1e200))
    assert_allclose(model.loading([0, 1e200]), [0, 1e100])
    assert_allclose(model.derivative([0, 1e100]), [1e300, 1e-300], rtol=1e-12, atol=0)


@pytest.mark.parametrize("value", [-1, [0, -1], np.nan, np.inf, True, [1j], ["1"]])
def test_nonphysical_concentrations_rejected(value):
    model = isotherm_from_parameters(Linear(distribution_m3_kg=1))
    with pytest.raises(ValueError):
        model.loading(value)
    with pytest.raises(ValueError):
        model.derivative(value)


def test_finite_output_range_and_unsupported_model():
    model = isotherm_from_parameters(Freundlich(q_ref_kg_kg=1, c_ref_kg_m3=1, exponent=10))
    with pytest.raises(ValueError, match="range"):
        model.loading(1e200)
    with pytest.raises(ValueError, match="Unsupported"):
        isotherm_from_parameters(object())

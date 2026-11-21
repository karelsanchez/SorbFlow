from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose

from sorbflow import LDF, BatchConfig, Freundlich, Langmuir, Linear, Observations, Species
from sorbflow.equilibrium import isotherm_from_parameters
from sorbflow.fit import FitError, batch_rate, isotherm


@pytest.mark.parametrize(
    "truth,start",
    [
        (Langmuir(qmax_kg_kg=0.03, affinity_m3_kg=10), Langmuir(qmax_kg_kg=0.01, affinity_m3_kg=3)),
        (
            Freundlich(q_ref_kg_kg=0.02, c_ref_kg_m3=0.01, exponent=0.7),
            Freundlich(q_ref_kg_kg=0.01, c_ref_kg_m3=0.01, exponent=0.5),
        ),
        (Linear(distribution_m3_kg=0.2), Linear(distribution_m3_kg=0.1)),
    ],
)
def test_synthetic_isotherm_parameter_recovery_and_local_rank(truth, start):
    c = np.geomspace(0.0001, 10, 50)
    exact = isotherm_from_parameters(truth).loading(c)
    fit = isotherm(c, exact, start, std_loading_kg_kg=np.full(c.size, 0.001))
    assert fit.locally_identifiable
    assert fit.jacobian_rank == len(fit.parameter_names)
    assert fit.covariance_log_parameters.shape == (len(fit.parameter_names),) * 2
    for name in fit.parameter_names:
        assert getattr(fit.parameters, name) == pytest.approx(getattr(truth, name), rel=1e-7)
    assert_allclose(fit.predicted, exact, rtol=1e-7, atol=1e-12)
    with pytest.raises(ValueError):
        fit.residuals[0] = 1


def test_nonidentifiable_duplicate_concentrations_are_flagged():
    initial = Langmuir(qmax_kg_kg=0.01, affinity_m3_kg=10)
    fit = isotherm([0.1] * 10, [0.005] * 10, initial)
    assert not fit.locally_identifiable
    assert fit.covariance_log_parameters is None
    assert fit.jacobian_rank < 2 or fit.jacobian_condition > 1e8


def test_unweighted_covariance_and_failed_fit():
    c = np.linspace(0.01, 1, 20)
    observed = 0.2 * c + np.random.default_rng(123).normal(0, 0.001, c.size)
    fit = isotherm(c, observed, Linear(distribution_m3_kg=0.1))
    assert fit.covariance_log_parameters[0, 0] > 0
    assert fit.parameters.distribution_m3_kg == pytest.approx(0.2, rel=0.02)
    with pytest.raises(FitError, match="converge"):
        isotherm(c, observed, Linear(distribution_m3_kg=0.001), max_nfev=1)


@pytest.mark.parametrize(
    "c,q,std,initial",
    [
        ([0, 1], [0], None, Linear(distribution_m3_kg=1)),
        ([], [], None, Linear(distribution_m3_kg=1)),
        ([0, 1], [0, 1], [0, 1], Linear(distribution_m3_kg=1)),
        ([0, 1], [0, 1], [1], Linear(distribution_m3_kg=1)),
        ([0, 1], [0, 1], None, Linear(distribution_m3_kg=0)),
        ([0, 1], [0, 1], None, LDF(rate_s_inv=1)),
    ],
)
def test_invalid_inverse_problems(c, q, std, initial):
    with pytest.raises(ValueError):
        isotherm(c, q, initial, std_loading_kg_kg=std)


def test_batch_rate_against_analytic_synthetic_observations():
    config = BatchConfig(
        species=Species(name="test-species"),
        material="test-material",
        liquid_volume_m3=0.001,
        adsorbent_mass_kg=0.002,
        duration_s=100,
        initial_concentration_kg_m3=0.01,
        initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=0.5),
        kinetics=LDF(rate_s_inv=0.005),
    )
    times = np.linspace(0, 100, 21)
    c = 0.005 + 0.005 * np.exp(-0.02 * 2 * times)
    observations = Observations(
        experiment_id="analytic-reference",
        species_name="test-species",
        time_s=times.tolist(),
        concentration_kg_m3=c.tolist(),
        source_sha256="a" * 64,
        std_kg_m3=(1e-5,) * len(times),
    )
    fit = batch_rate(config, observations)
    assert fit.locally_identifiable
    assert fit.parameters.rate_s_inv == pytest.approx(0.02, rel=1e-5)
    with pytest.raises(ValueError, match="species"):
        batch_rate(config, replace(observations, species_name="other-species"))

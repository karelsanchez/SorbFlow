import json
from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose

from sorbflow import LDF, BatchConfig, Freundlich, Langmuir, Linear, Species
from sorbflow.simulate import batch
from sorbflow.solvers import SimulationError, SolverOptions
from sorbflow.validate import mass_balance


@pytest.fixture
def problem():
    return BatchConfig(
        species=Species(name="synthetic"),
        material="generic-adsorbent",
        liquid_volume_m3=0.001,
        adsorbent_mass_kg=0.002,
        duration_s=300,
        initial_concentration_kg_m3=0.01,
        initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=0.5),
        kinetics=LDF(rate_s_inv=0.02),
    )


@pytest.mark.parametrize("method", ["BDF", "Radau"])
@pytest.mark.parametrize("q0", [0, 0.02])
def test_linear_batch_against_exact_solution_and_mass(problem, method, q0):
    problem = replace(problem, initial_loading_kg_kg=q0)
    options = SolverOptions(
        method=method, rtol=1e-9, atol_concentration_kg_m3=1e-13, atol_loading_kg_kg=1e-14
    )
    result = batch(problem, options=options)
    v, m, k = problem.liquid_volume_m3, problem.adsorbent_mass_kg, 0.02
    mass = v * 0.01 + m * q0
    ceq = mass / (v + m * 0.5)
    c = ceq + (0.01 - ceq) * np.exp(-k * (1 + m * 0.5 / v) * result.time_s)
    q = (mass - v * c) / m
    assert_allclose(result.concentration_kg_m3[:, 0], c, rtol=1e-8, atol=1e-12)
    assert_allclose(result.loading_kg_kg[:, 0], q, rtol=1e-8, atol=1e-12)
    assert_allclose(result.inventory_kg, mass, rtol=1e-12, atol=1e-20)
    assert result.diagnostics.max_scaled_mass_residual < 1e-12
    assert mass_balance(result).passed


@pytest.mark.parametrize(
    "equilibrium",
    [
        Langmuir(qmax_kg_kg=0.05, affinity_m3_kg=20),
        Freundlich(q_ref_kg_kg=0.01, c_ref_kg_m3=0.01, exponent=0.7),
    ],
)
def test_nonlinear_batch_both_integrators_and_monotonicity(problem, equilibrium):
    problem = replace(problem, equilibrium=equilibrium)
    a = batch(problem, options=SolverOptions(method="BDF", rtol=1e-9))
    b = batch(problem, options=SolverOptions(method="Radau", rtol=1e-9))
    assert_allclose(a.concentration_kg_m3, b.concentration_kg_m3, rtol=1e-6, atol=1e-10)
    assert np.max(np.diff(a.concentration_kg_m3[:, 0])) <= 1e-10
    assert np.min(np.diff(a.loading_kg_kg[:, 0])) >= -1e-12
    assert a.diagnostics.max_scaled_mass_residual < 1e-10


def test_equilibrium_empty_system_and_result_metadata(problem):
    fixed = batch(replace(problem, initial_loading_kg_kg=0.005))
    assert_allclose(fixed.concentration_kg_m3, 0.01, atol=1e-14)
    empty = batch(replace(problem, initial_concentration_kg_m3=0))
    assert_allclose(empty.concentration_kg_m3, 0, atol=0)
    data = json.loads(empty.to_json())
    assert data["result_kind"] == "numerical_simulation"
    assert data["z_m"] is None
    with pytest.raises(ValueError):
        empty.concentration_kg_m3[0, 0] = 1


def test_reproducible_fingerprint_and_explicit_revision(problem):
    a = batch(problem, time_s=[0, 300], code_revision="a" * 40)
    b = batch(problem, time_s=[0, 300], code_revision="a" * 40)
    c = batch(problem, time_s=[0, 300], options=SolverOptions(method="Radau"))
    assert a.numerical_sha256 == b.numerical_sha256 != c.numerical_sha256
    assert a.manifest.run_id != b.manifest.run_id
    assert a.manifest.config_sha256 == problem.sha256
    assert a.manifest.code_revision == "a" * 40
    assert_allclose(a.concentration_kg_m3, b.concentration_kg_m3, rtol=0, atol=0)


@pytest.mark.parametrize("times", [[1, 300], [0, 299], [0, 0, 300], [0], [[0, 300]], [0, np.nan]])
def test_invalid_output_times(problem, times):
    with pytest.raises(ValueError):
        batch(problem, time_s=times)


def test_invalid_problem_options_and_failed_integration(problem, monkeypatch):
    with pytest.raises(ValueError):
        batch({})
    with pytest.raises(ValueError):
        batch(problem, options={})

    def fail(*args, **kwargs):
        raise ValueError("forced solver failure")

    monkeypatch.setattr("sorbflow.solvers.integration.solve_ivp", fail)
    with pytest.raises(SimulationError, match="forced solver failure"):
        batch(problem)

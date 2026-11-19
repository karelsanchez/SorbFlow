from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.integrate import trapezoid
from scipy.special import gammainc

from pyfast import (
    HSDM,
    LDF,
    Bed,
    Freundlich,
    Langmuir,
    Linear,
    Operation,
    SimulationConfig,
    Species,
)
from pyfast.simulate import column
from pyfast.solvers import SolverOptions
from pyfast.validate import mass_balance


@pytest.fixture
def tracer():
    bed = Bed(
        length_m=0.1,
        diameter_m=0.01,
        particle_diameter_m=0.0001,
        porosity=0.4,
        particle_density_kg_m3=1000,
        material="any-sorbent",
    )
    residence = bed.porosity * bed.volume_m3 / 1e-7
    return SimulationConfig(
        species=Species(name="any-solute"),
        bed=bed,
        operation=Operation(
            flow_m3_s=1e-7, inlet_concentration_kg_m3=0.01, duration_s=3 * residence
        ),
        equilibrium=Linear(distribution_m3_kg=0),
        kinetics=LDF(rate_s_inv=0.1),
    )


def test_tracer_against_exact_finite_volume_tanks_solution(tracer):
    n = 40
    result = column(
        tracer, options=SolverOptions(axial_cells=n, rtol=1e-9, atol_concentration_kg_m3=1e-13)
    )
    tau = tracer.bed.porosity * tracer.bed.volume_m3 / tracer.operation.flow_m3_s
    exact = 0.01 * gammainc(n, n * result.time_s / tau)
    assert_allclose(result.outlet_concentration_kg_m3, exact, rtol=1e-6, atol=2e-11)
    assert result.diagnostics.max_scaled_mass_residual < 1e-10
    assert mass_balance(result).passed
    assert result.z_m.size == n


def test_tracer_spatial_convergence_to_advection_front(tracer):
    tau = tracer.bed.porosity * tracer.bed.volume_m3 / tracer.operation.flow_m3_s
    times = np.linspace(0, tracer.operation.duration_s, 1201)
    exact = (times >= tau).astype(float)
    errors = []
    for n in (25, 50, 100, 200):
        result = column(tracer, time_s=times, options=SolverOptions(axial_cells=n, rtol=1e-9))
        relative = result.outlet_concentration_kg_m3 / 0.01
        errors.append(float(trapezoid(np.abs(relative - exact), times) / tau))
        if n == 200:
            arrival = np.interp(0.5, relative, times)
            assert abs(arrival / tau - 1) < 0.01
    # Upwind convergence for a discontinuous front is integral, not pointwise order 1.
    assert all(b < 0.8 * a for a, b in zip(errors[:-1], errors[1:], strict=True))


@pytest.mark.parametrize(
    "equilibrium",
    [
        Langmuir(qmax_kg_kg=0.01, affinity_m3_kg=10),
        Freundlich(q_ref_kg_kg=0.001, c_ref_kg_m3=0.01, exponent=0.8),
    ],
)
@pytest.mark.parametrize("desorb", [False, True])
def test_column_adsorption_desorption_dispersion_and_mass(tracer, equilibrium, desorb):
    operation = replace(
        tracer.operation,
        duration_s=1000,
        axial_dispersion_m2_s=1e-5,
        inlet_concentration_kg_m3=0 if desorb else 0.01,
        initial_loading_kg_kg=0.001 if desorb else 0,
    )
    problem = replace(tracer, equilibrium=equilibrium, operation=operation)
    result = column(problem, options=SolverOptions(axial_cells=40))
    assert result.diagnostics.max_scaled_mass_residual < 1e-8
    assert mass_balance(result).passed
    assert result.diagnostics.min_concentration_kg_m3 >= -1e-9
    if desorb:
        assert np.max(result.outlet_concentration_kg_m3) > 0
        assert result.inventory_kg[-1] < result.inventory_kg[0]
    else:
        assert result.inventory_kg[-1] > 0


def test_column_temporal_refinement_and_integrator_agreement(tracer):
    problem = replace(tracer, equilibrium=Linear(distribution_m3_kg=0.001))
    # Relax mass acceptance explicitly only to quantify the coarse temporal error.
    loose = column(problem, options=SolverOptions(axial_cells=30, rtol=1e-4, mass_rtol=1e-3))
    tight = column(
        problem,
        options=SolverOptions(
            axial_cells=30, rtol=1e-9, atol_concentration_kg_m3=1e-13, atol_loading_kg_kg=1e-15
        ),
    )
    ref = column(
        problem,
        options=SolverOptions(
            axial_cells=30,
            rtol=1e-10,
            atol_concentration_kg_m3=1e-14,
            atol_loading_kg_kg=1e-16,
            method="Radau",
            max_step_s=1,
        ),
    )
    error_loose = np.linalg.norm(loose.outlet_concentration_kg_m3 - ref.outlet_concentration_kg_m3)
    error_tight = np.linalg.norm(tight.outlet_concentration_kg_m3 - ref.outlet_concentration_kg_m3)
    assert error_tight < 0.02 * error_loose
    assert_allclose(
        tight.outlet_concentration_kg_m3, ref.outlet_concentration_kg_m3, rtol=2e-5, atol=1e-10
    )


def test_uniform_equilibrium_column_and_hsdm_tracer(tracer):
    problem = replace(
        tracer,
        equilibrium=Linear(distribution_m3_kg=0.01),
        operation=replace(
            tracer.operation, initial_concentration_kg_m3=0.01, initial_loading_kg_kg=0.0001
        ),
    )
    result = column(problem, options=SolverOptions(axial_cells=20))
    assert_allclose(result.concentration_kg_m3, 0.01, atol=1e-12)
    assert_allclose(result.loading_kg_kg, 0.0001, atol=1e-14)
    hsdm = column(
        replace(tracer, kinetics=HSDM(surface_diffusivity_m2_s=1e-12, film_coefficient_m_s=1e-5)),
        options=SolverOptions(axial_cells=10, radial_cells=4),
    )
    ldf = column(tracer, options=SolverOptions(axial_cells=10))
    assert_allclose(
        hsdm.outlet_concentration_kg_m3, ldf.outlet_concentration_kg_m3, rtol=1e-5, atol=1e-9
    )

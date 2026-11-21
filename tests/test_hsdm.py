import json
from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.integrate import solve_ivp

from sorbflow import HSDM, Bed, Freundlich, Langmuir, Linear, Operation, SimulationConfig, Species
from sorbflow.equilibrium import isotherm_from_parameters
from sorbflow.kinetics.sphere import SphereGrid, diffusion_rhs, film_flux
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions


def test_sphere_diffusion_against_series_and_radial_convergence():
    times = np.array([0.01, 0.03, 0.1, 0.3, 1.0])
    terms = np.arange(1, 1001)[:, None]
    exact = 1 - 6 / np.pi**2 * np.sum(np.exp(-(terms**2) * np.pi**2 * times) / terms**2, axis=0)
    errors = []
    for n in (10, 20, 40, 80):
        grid = SphereGrid(1.0, n)

        def rhs(t, q, grid=grid):
            flux = np.array([(1 - q[-1]) / (1 - grid.centers_m[-1])])
            return diffusion_rhs(
                q[None], flux, grid=grid, diffusivity_m2_s=1, particle_density_kg_m3=1
            )[0]

        result = solve_ivp(
            rhs, (0, 1), np.zeros(n), method="BDF", t_eval=times, rtol=1e-10, atol=1e-12
        )
        assert result.success
        mean = grid.mean_weights @ result.y
        errors.append(np.max(np.abs(mean - exact)))
    assert errors[-1] < 1e-3
    assert all(b < 0.6 * a for a, b in zip(errors[:-1], errors[1:], strict=True))


def test_film_flux_against_linear_closed_form_and_particle_mass():
    grid = SphereGrid(0.001, 12)
    ds, rho, kf, coefficient = 1e-12, 1000, 1e-5, 0.3
    c = np.array([0, 0.01, 0.001])
    q = np.array([0, 0, 0.01])
    g = rho * ds / (grid.radius_m / (2 * grid.cells))
    cs = (kf * c + g * q) / (kf + g * coefficient)
    model = isotherm_from_parameters(Linear(distribution_m3_kg=coefficient))
    flux = film_flux(
        c,
        q,
        model,
        grid=grid,
        diffusivity_m2_s=ds,
        particle_density_kg_m3=rho,
        film_coefficient_m_s=kf,
    )
    assert_allclose(flux, kf * (c - cs), rtol=1e-11, atol=1e-25)
    radial = np.broadcast_to(q[:, None], (3, grid.cells)).copy()
    derivative = diffusion_rhs(
        radial, flux, grid=grid, diffusivity_m2_s=ds, particle_density_kg_m3=rho
    )
    assert_allclose(derivative @ grid.mean_weights, 3 * flux / (rho * grid.radius_m), atol=1e-20)
    assert flux[-1] < 0  # Desorption reverses both phase sources.


@pytest.mark.parametrize("kf", [1e-12, 1e-5, 1e6, 1e9])
def test_film_resistance_limits_do_not_lose_flux_by_cancellation(kf):
    grid = SphereGrid(0.001, 12)
    ds, rho, coefficient = 1e-12, 1000, 0.3
    c = np.array([0.01, 0.01])
    q = np.array([0, 0.003])
    conductance = rho * ds / (grid.radius_m / (2 * grid.cells))
    exact = conductance * (coefficient * c - q) / (1 + conductance * coefficient / kf)
    model = isotherm_from_parameters(Linear(distribution_m3_kg=coefficient))
    actual = film_flux(
        c,
        q,
        model,
        grid=grid,
        diffusivity_m2_s=ds,
        particle_density_kg_m3=rho,
        film_coefficient_m_s=kf,
    )
    assert_allclose(actual, exact, rtol=1e-9, atol=1e-18)


@pytest.fixture
def problem():
    return SimulationConfig(
        species=Species(name="generic-water-solute"),
        bed=Bed(
            length_m=0.1,
            diameter_m=0.01,
            particle_diameter_m=0.0002,
            porosity=0.4,
            particle_density_kg_m3=1000,
            material="generic-biochar",
        ),
        operation=Operation(
            flow_m3_s=1e-7,
            inlet_concentration_kg_m3=0.01,
            duration_s=300,
            axial_dispersion_m2_s=1e-6,
        ),
        equilibrium=Langmuir(qmax_kg_kg=0.001, affinity_m3_kg=10),
        kinetics=HSDM(surface_diffusivity_m2_s=1e-11, film_coefficient_m_s=1e-5),
    )


@pytest.mark.parametrize("desorb", [False, True])
def test_hsdm_mass_radial_output_and_integrator_agreement(problem, desorb):
    if desorb:
        problem = replace(
            problem,
            operation=replace(
                problem.operation, inlet_concentration_kg_m3=0, initial_loading_kg_kg=0.0005
            ),
        )
    options = SolverOptions(axial_cells=10, radial_cells=6, rtol=1e-7)
    bdf = column(problem, options=options, time_s=[0, 50, 100, 200, 300])
    radau = column(problem, options=replace(options, method="Radau"), time_s=[0, 50, 100, 200, 300])
    assert bdf.diagnostics.max_scaled_mass_residual < 1e-8
    assert radau.diagnostics.max_scaled_mass_residual < 1e-8
    assert_allclose(
        bdf.outlet_concentration_kg_m3, radau.outlet_concentration_kg_m3, rtol=1e-4, atol=1e-9
    )
    assert bdf.radial_loading_kg_kg.shape == (5, 10, 6)
    assert bdf.r_m.size == 6
    doc = json.loads(bdf.to_json())
    assert np.shape(doc["radial_loading_kg_kg"]) == (5, 10, 6)
    assert doc["config"]["kinetics"]["kind"] == "hsdm"


def test_hsdm_clean_freundlich_singular_surface_and_refinement(problem):
    problem = replace(
        problem, equilibrium=Freundlich(q_ref_kg_kg=0.0001, c_ref_kg_m3=0.01, exponent=0.5)
    )
    values = []
    for n in (4, 8, 16):
        result = column(
            problem, options=SolverOptions(axial_cells=8, radial_cells=n), time_s=[0, 100, 200, 300]
        )
        values.append(result.outlet_concentration_kg_m3)
        assert result.diagnostics.max_scaled_mass_residual < 1e-8
    assert np.linalg.norm(values[2] - values[1]) < np.linalg.norm(values[1] - values[0])


@pytest.mark.parametrize("radius,cells", [(0, 10), (-1, 10), (1, 1), (1, True)])
def test_invalid_sphere_grid(radius, cells):
    with pytest.raises(ValueError):
        SphereGrid(radius, cells)

"""Film/surface root solver against an independent bracketing reference."""

from dataclasses import dataclass

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

import sorbflow.kinetics.sphere as sphere
from sorbflow import Freundlich, Langmuir, Linear
from sorbflow.equilibrium import isotherm_from_parameters
from sorbflow.kinetics.sphere import SphereGrid, diffusion_rhs, film_flux
from sorbflow.solvers.integration import SimulationError

GRID = SphereGrid(0.0005, 12)
DS, RHO, KF = 1e-14, 800.0, 2e-5
G = RHO * DS / GRID.surface_distance_m
MAGNITUDES = np.logspace(-30, -1, 30)

MODELS = {
    "linear": Linear(distribution_m3_kg=5.0),
    "langmuir": Langmuir(qmax_kg_kg=0.05, affinity_m3_kg=100.0),
    "langmuir-steep": Langmuir(qmax_kg_kg=0.05, affinity_m3_kg=1e8),
    **{
        f"freundlich-{n}": Freundlich(q_ref_kg_kg=0.05, c_ref_kg_m3=0.01, exponent=n)
        for n in (0.3, 0.43, 0.6, 0.8, 1.0, 1.5)
    },
}


def odd(model, x):
    return float(np.sign(x) * model.loading(np.array([abs(x)]))[0])


def reference_flux(model, c, q):
    target = KF * c + G * q
    if target == 0:
        return 0.0, 0.0
    span = abs(target) / KF
    root = brentq(
        lambda x: KF * x + G * odd(model, x) - target,
        -span if target < 0 else 0.0,
        span if target > 0 else 0.0,
        xtol=1e-320,
        rtol=4 * np.finfo(float).eps,
        maxiter=2000,
    )
    loading = odd(model, root)
    # Both sides agree at the root; use the one free of cancellation, as the solver.
    if KF * (abs(c) + abs(root)) <= G * (abs(loading) + abs(q)):
        return root, KF * (c - root)
    return root, G * (loading - q)


def check(model, bulk, outer):
    flux = film_flux(
        bulk,
        outer,
        model,
        grid=GRID,
        diffusivity_m2_s=DS,
        particle_density_kg_m3=RHO,
        film_coefficient_m_s=KF,
    )
    for c, q, j in zip(bulk, outer, flux, strict=True):
        _, expected = reference_flux(model, c, q)
        scale = KF * abs(c) + G * abs(q)
        assert abs(j - expected) <= 1e-10 * abs(expected) + 1e-14 * scale, (c, q, j, expected)
    return flux


@pytest.mark.parametrize("name", MODELS)
@pytest.mark.parametrize("direction", ["adsorption", "desorption"])
def test_film_flux_matches_brentq_across_magnitudes(name, direction):
    model = isotherm_from_parameters(MODELS[name])
    bulk = MAGNITUDES.copy()
    equilibrium = model.loading(bulk)
    # Adsorption: particle surface below equilibrium; desorption: above it.
    outer = equilibrium * (0.3 if direction == "adsorption" else 3.0)
    flux = check(model, bulk, outer)
    assert np.all(flux > 0) if direction == "adsorption" else np.all(flux < 0)


@pytest.mark.parametrize("name", MODELS)
def test_film_flux_odd_continuation_for_trial_states(name):
    model = isotherm_from_parameters(MODELS[name])
    bulk = MAGNITUDES.copy()
    outer = model.loading(bulk[::-1])
    positive = film_flux(
        bulk,
        outer,
        model,
        grid=GRID,
        diffusivity_m2_s=DS,
        particle_density_kg_m3=RHO,
        film_coefficient_m_s=KF,
    )
    negative = film_flux(
        -bulk,
        -outer,
        model,
        grid=GRID,
        diffusivity_m2_s=DS,
        particle_density_kg_m3=RHO,
        film_coefficient_m_s=KF,
    )
    assert_array_equal(negative, -positive)
    # Mixed-sign trial states, with the root on either side of zero.
    check(model, np.concatenate((-bulk, bulk)), np.concatenate((outer, -outer)))
    check(model, np.array([0.0, -1e-3, 1e-3]), np.array([0.0, 0.0, 0.0]))


@pytest.mark.parametrize("exponent", [0.3, 0.43, 0.6])
def test_freundlich_root_is_reached_in_few_isotherm_evaluations(exponent, monkeypatch):
    model = isotherm_from_parameters(
        Freundlich(q_ref_kg_kg=0.05, c_ref_kg_m3=0.01, exponent=exponent)
    )
    calls = []
    kernel = sphere._loading_kernel

    def counting(model_, x):
        calls.append(1)
        return kernel(model_, x)

    monkeypatch.setattr(sphere, "_loading_kernel", counting)
    bulk = MAGNITUDES.copy()
    check(model, bulk, model.loading(bulk) * 0.5)
    # Bisection needed 50-80 evaluations; the log-Newton path needs a handful.
    assert len(calls) <= 10


def test_linear_and_langmuir_closed_forms_need_one_evaluation(monkeypatch):
    calls = []
    kernel = sphere._loading_kernel

    def counting(model_, x):
        calls.append(1)
        return kernel(model_, x)

    monkeypatch.setattr(sphere, "_loading_kernel", counting)
    for name in ("linear", "langmuir", "langmuir-steep"):
        model = isotherm_from_parameters(MODELS[name])
        calls.clear()
        film_flux(
            MAGNITUDES[10:],
            model.loading(MAGNITUDES[10:]) * 0.5,
            model,
            grid=GRID,
            diffusivity_m2_s=DS,
            particle_density_kg_m3=RHO,
            film_coefficient_m_s=KF,
        )
        assert len(calls) == 1, name


@dataclass(frozen=True)
class Sips:
    """A protocol-only isotherm, unknown to the solver's closed forms."""

    qmax: float = 0.05
    b: float = 30.0
    n: float = 0.5

    def loading(self, c):
        c = np.asarray(c, dtype=float)
        bc = (self.b * c) ** self.n
        return self.qmax * bc / (1 + bc)

    def derivative(self, c):
        c = np.asarray(c, dtype=float)
        if np.any(c == 0):
            raise ValueError("singular")
        bc = (self.b * c) ** self.n
        return self.qmax * self.n * bc / (c * (1 + bc) ** 2)


@dataclass(frozen=True)
class NoDerivative:
    qmax: float = 0.05
    b: float = 30.0

    def loading(self, c):
        c = np.asarray(c, dtype=float)
        return self.qmax * np.tanh(self.b * c)


@pytest.mark.parametrize("model", [Sips(), NoDerivative()])
def test_generic_protocol_isotherm_uses_safeguarded_fallback(model):
    bulk = MAGNITUDES.copy()
    check(model, bulk, model.loading(bulk) * 0.5)
    check(model, -bulk, -model.loading(bulk) * 2)


@dataclass(frozen=True)
class Broken:
    def loading(self, c):
        return np.full_like(np.asarray(c, dtype=float), np.nan)


def test_genuine_failure_raises_simulation_error():
    kwargs = dict(
        grid=GRID, diffusivity_m2_s=DS, particle_density_kg_m3=RHO, film_coefficient_m_s=KF
    )
    with pytest.raises(SimulationError):
        film_flux(np.array([1e-3]), np.array([0.0]), Broken(), **kwargs)
    model = isotherm_from_parameters(MODELS["freundlich-0.43"])
    with pytest.raises(SimulationError):
        film_flux(np.array([np.nan]), np.array([0.0]), model, **kwargs)


def test_uniform_grid_default_is_unchanged():
    grid = SphereGrid(0.002, 7)
    assert grid.growth == 1.0
    assert_array_equal(grid.faces_m, np.linspace(0, 0.002, 8))
    assert_array_equal(grid.centers_m, (np.arange(7) + 0.5) * 0.002 / 7)
    assert grid.surface_distance_m == 0.002 / (2 * 7)
    assert grid == SphereGrid(0.002, 7)
    grid.faces_m[:] = 0  # Public arrays are copies.
    assert grid.faces_m[-1] == 0.002


@pytest.mark.parametrize("growth", [0, -0.5, 1.5, float("nan")])
def test_invalid_growth(growth):
    with pytest.raises(ValueError):
        SphereGrid(1.0, 10, growth=growth)


@pytest.mark.parametrize("growth", [1.0, 0.9, 0.7])
def test_refined_grid_exact_volumes_and_mass_conservation(growth):
    grid = SphereGrid(0.001, 15, growth=growth)
    faces = grid.faces_m
    assert faces[0] == 0 and faces[-1] == 0.001
    widths = np.diff(faces)
    assert np.all(widths > 0)
    if growth < 1:
        assert_allclose(widths[1:] / widths[:-1], growth, rtol=1e-12)
    assert_allclose(np.sum(grid.shell_volumes_m3), 0.001**3 / 3, rtol=1e-14)
    rng = np.random.default_rng(1)
    loading = rng.random((4, grid.cells))
    flux = rng.normal(size=4)
    dq = diffusion_rhs(loading, flux, grid=grid, diffusivity_m2_s=1e-12, particle_density_kg_m3=900)
    assert_allclose(dq @ grid.shell_volumes_m3, grid.radius_m**2 * flux / 900, rtol=1e-11)


def test_surface_refinement_is_more_accurate_at_equal_cells():
    times = np.array([0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0])
    terms = np.arange(1, 4001)[:, None]
    exact = 1 - 6 / np.pi**2 * np.sum(np.exp(-(terms**2) * np.pi**2 * times) / terms**2, axis=0)

    def error(cells, growth):
        grid = SphereGrid(1.0, cells, growth=growth)

        def rhs(_t, q):
            flux = np.array([(1 - q[-1]) / grid.surface_distance_m])
            return diffusion_rhs(
                q[None], flux, grid=grid, diffusivity_m2_s=1, particle_density_kg_m3=1
            )[0]

        result = solve_ivp(
            rhs, (0, 1), np.zeros(cells), method="BDF", t_eval=times, rtol=1e-10, atol=1e-12
        )
        assert result.success
        return np.max(np.abs(grid.mean_weights @ result.y - exact))

    for cells in (10, 20):
        assert error(cells, 0.85) < 0.5 * error(cells, 1.0)

"""Second-order TVD axial advection: accuracy, positivity, conservation, Jacobians."""
from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.integrate import quad
from scipy.special import i0e

from sorbflow import HSDM, LDF, Bed, Langmuir, Linear, Operation, SimulationConfig, Species
from sorbflow.equilibrium import isotherm_from_parameters
from sorbflow.equilibrium.isotherms import trial_loading
from sorbflow.reactors._ldf_jacobian import LDFColumnJacobian
from sorbflow.reactors.column import (
    AxialTransport,
    _jacobian_pattern,
    effluent_concentration,
    outlet_face_value,
)
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions
from sorbflow.validate import mass_balance

BED = Bed(length_m=.1, diameter_m=.01, particle_diameter_m=1e-4, porosity=.4,
          particle_density_kg_m3=1000, material="generic")
FLOW = 1e-7
VELOCITY = FLOW / (BED.volume_m3 / BED.length_m)
K, XI = 1e-3, 20.0
RATE = XI * VELOCITY / (BED.bulk_density_kg_m3 * K * BED.length_m)
T_STOICH = BED.length_m * (BED.porosity + BED.bulk_density_kg_m3 * K) / VELOCITY


def klinkenberg_config(duration=2.5 * T_STOICH, dispersion=0.0):
    return SimulationConfig(
        species=Species(name="independent-test-solute"), bed=BED,
        operation=Operation(flow_m3_s=FLOW, inlet_concentration_kg_m3=1.0,
                            duration_s=duration, axial_dispersion_m2_s=dispersion),
        equilibrium=Linear(distribution_m3_kg=K), kinetics=LDF(rate_s_inv=RATE))


def thomas_outlet(times):
    """Exact linear-LDF plug-flow outlet c/c0 = 1 - int_0^xi e^{-tau-s} I0(2 sqrt(tau s)) ds."""
    out = np.zeros_like(times)
    for j, t in enumerate(times):
        tau = RATE * (t - BED.porosity * BED.length_m / VELOCITY)
        if tau > 0:
            def integrand(s, tau=tau):
                return i0e(2*np.sqrt(tau*s)) * np.exp(-(np.sqrt(tau)-np.sqrt(s))**2)
            out[j] = 1 - quad(integrand, 0, XI, limit=400, epsabs=1e-14, epsrel=1e-12,
                              points=[tau] if tau < XI else None)[0]
    return out


@pytest.fixture(scope="module")
def klinkenberg_errors():
    times = np.linspace(0, 2.5 * T_STOICH, 151)
    exact = thomas_outlet(times)
    errors = {}
    for scheme in ("upwind1", "tvd"):
        for cells in (25, 50, 100):
            result = column(klinkenberg_config(), time_s=times,
                            options=SolverOptions(axial_cells=cells, axial_scheme=scheme))
            effluent = effluent_concentration(result)
            errors[scheme, cells] = (float(np.sqrt(np.mean((effluent - exact)**2))),
                                     float(np.max(np.abs(effluent - exact))))
            assert result.diagnostics.max_scaled_mass_residual < 1e-8
    return errors


def test_observed_order_of_accuracy_on_smooth_klinkenberg_breakthrough(klinkenberg_errors):
    # xi=20: the initial jump exp(-xi) is 2e-9, so the effluent profile is smooth.
    for scheme, low, high in (("upwind1", .7, 1.1), ("tvd", 1.8, 2.3)):
        for norm in (0, 1):
            e = [klinkenberg_errors[scheme, n][norm] for n in (25, 50, 100)]
            orders = np.log2(np.array(e[:-1]) / np.array(e[1:]))
            assert np.all((orders > low) & (orders < high)), (scheme, norm, orders)


def test_tvd_is_more_accurate_than_upwind_at_equal_cells(klinkenberg_errors):
    for cells in (25, 50, 100):
        upwind, tvd = klinkenberg_errors["upwind1", cells], klinkenberg_errors["tvd", cells]
        assert tvd[0] < upwind[0] / 10 and tvd[1] < upwind[1] / 10
    assert klinkenberg_errors["tvd", 100][1] < 1e-3


@pytest.mark.parametrize("desorb", [False, True])
def test_step_front_has_no_new_extrema_and_is_nonnegative(desorb):
    operation = Operation(flow_m3_s=FLOW, inlet_concentration_kg_m3=0. if desorb else .01,
                          initial_concentration_kg_m3=.01 if desorb else 0., duration_s=60.)
    tracer = SimulationConfig(species=Species(name="tracer"), bed=BED, operation=operation,
                              equilibrium=Linear(distribution_m3_kg=0), kinetics=LDF(rate_s_inv=.1))
    options = SolverOptions(axial_cells=80, axial_scheme="tvd")
    result = column(tracer, options=options)
    c = result.concentration_kg_m3
    assert result.diagnostics.min_concentration_kg_m3 >= -10 * options.atol_concentration_kg_m3
    assert np.max(c) <= .01 * (1 + 1e-6)
    assert np.min(effluent_concentration(result)) >= -10 * options.atol_concentration_kg_m3
    # Monotone initial/boundary data stay monotone in z (no spurious oscillation).
    slope = np.diff(c, axis=1)
    tol = 1e-6 * .01
    assert np.all(slope >= -tol) if desorb else np.all(slope <= tol)
    assert result.diagnostics.max_scaled_mass_residual < 1e-8
    assert mass_balance(result).passed


@pytest.mark.parametrize("dispersion", [0., 1e-6])
def test_semi_discrete_transport_is_local_extremum_diminishing(dispersion):
    rng = np.random.default_rng(7)
    cells, inlet = 30, .004
    transport = AxialTransport(cells=cells, dz=.1/cells, velocity=VELOCITY, porosity=.4,
                               dispersion_m2_s=dispersion, inlet_concentration_kg_m3=inlet,
                               scheme="tvd")
    for _ in range(200):
        c = rng.uniform(0, .01, cells) * (rng.uniform(size=cells) > .3)
        dc = -np.diff(transport.face_flux(c))
        left = np.concatenate(([inlet], c[:-1]))
        right = np.concatenate((c[1:], [c[-1]]))
        minimum = (c <= left) & (c <= right)
        maximum = (c >= left) & (c >= right)
        scale = 1e-12 * VELOCITY * .01
        assert np.all(dc[minimum] >= -scale) and np.all(dc[maximum] <= scale)
        assert np.all(transport.face_values(c) >= 0)


def test_outlet_face_value_is_second_order_extrapolation_and_nonnegative():
    assert_allclose(outlet_face_value([.3], [.2]), [.35], rtol=1e-14)
    falling = outlet_face_value(np.full(50, 1e-6), np.geomspace(1e-6, 1., 50))
    assert np.all(falling >= 0) and np.all(falling <= 1e-6)
    assert_allclose(outlet_face_value([1.], [1.]), [1.])


def independent_rhs(config, cells, state):
    """Scalar MUSCL/van Albada assembly written independently of AxialTransport."""
    bed, op = config.bed, config.operation
    dz, u = bed.length_m / cells, op.flow_m3_s / (bed.volume_m3 / bed.length_m)
    eps, disp = bed.porosity, op.axial_dispersion_m2_s
    c, q = state[:cells], state[cells:2*cells]

    def va(a, b):
        return a*b*(a+b)/(a*a+b*b) if a*b > 0 else 0.

    w = 2*eps*disp/dz / (u + 2*eps*disp/dz)
    face_b = op.inlet_concentration_kg_m3 + w*(c[0]-op.inlet_concentration_kg_m3)
    flux = [u*op.inlet_concentration_kg_m3]
    for f in range(1, cells):
        i = f - 1
        back = 2*(c[0]-face_b) if i == 0 else c[i]-c[i-1]
        flux.append(u*(c[i] + .5*va(back, c[i+1]-c[i])) - eps*disp*(c[i+1]-c[i])/dz)
    a = c[-1]-c[-2]
    g = a if a >= 0 else a*max(c[-1], 0)/(max(c[-1], 0)-a)
    flux.append(u*(c[-1] + .5*va(a, g)))
    model = isotherm_from_parameters(config.equilibrium)
    source = config.kinetics.rate_s_inv*(trial_loading(model, c) - q)
    dc = [-(flux[i+1]-flux[i])/(eps*dz) - bed.bulk_density_kg_m3/eps*source[i]
          for i in range(cells)]
    area = bed.volume_m3/bed.length_m
    return np.concatenate((dc, source, [area*flux[0], area*flux[-1]]))


@pytest.mark.parametrize("cells", [2, 3, 8])
@pytest.mark.parametrize("dispersion", [0., 1e-6])
def test_tvd_analytic_jacobian_directional_derivative(cells, dispersion):
    config = replace(klinkenberg_config(dispersion=dispersion),
                     equilibrium=Langmuir(qmax_kg_kg=.0002, affinity_m3_kg=20))
    transport = AxialTransport.from_config(config, cells, "tvd")
    jac = LDFColumnJacobian(config, cells, transport=transport)
    pattern = _jacobian_pattern(cells, "tvd").toarray() != 0
    rng = np.random.default_rng(cells)
    for profile in (np.linspace(.9, .1, cells)**2, rng.uniform(.01, 1., cells)):
        state = np.concatenate((profile, rng.uniform(0, 1e-4, cells), [0., 0.]))
        direction = rng.normal(size=state.size)
        step = 1e-7
        numeric = (independent_rhs(config, cells, state + step*direction)
                   - independent_rhs(config, cells, state - step*direction)) / (2*step)
        matrix = jac(0., state)
        assert_allclose(matrix @ direction, numeric, rtol=1e-6, atol=1e-9*np.max(abs(numeric)))
        assert np.all(pattern[matrix.toarray() != 0])
    flux = AxialTransport.from_config(config, cells, "tvd").face_flux(state[:cells])
    area = BED.volume_m3 / BED.length_m
    assert_allclose(independent_rhs(config, cells, state)[-1], area*flux[-1], rtol=1e-14)


@pytest.mark.parametrize("history", ["dense", "streaming"])
def test_tvd_analytic_and_finite_difference_agree_and_conserve(history):
    config = replace(klinkenberg_config(duration=120., dispersion=1e-6),
                     equilibrium=Langmuir(qmax_kg_kg=.002, affinity_m3_kg=5))
    settings = SolverOptions(axial_cells=40, axial_scheme="tvd", history=history,
                             rtol=1e-8, atol_concentration_kg_m3=1e-12)
    fd = column(config, options=settings)
    analytic = column(config, options=replace(settings, jacobian="analytic"))
    assert_allclose(analytic.concentration_kg_m3, fd.concentration_kg_m3, rtol=0, atol=1e-5)
    for result in (fd, analytic):
        assert result.diagnostics.max_scaled_mass_residual < 1e-8
        assert result.diagnostics.min_concentration_kg_m3 >= -1e-11
    assert fd.numerical_sha256 != column(config, options=replace(
        settings, axial_scheme="upwind1")).numerical_sha256


def test_cumulative_outlet_mass_uses_the_effluent_face_flux():
    times = np.linspace(0, 2.5 * T_STOICH, 2001)
    result = column(klinkenberg_config(), time_s=times,
                    options=SolverOptions(axial_cells=40, axial_scheme="tvd", rtol=1e-9))
    rate = FLOW * effluent_concentration(result)
    cumulative = np.concatenate(([0.], np.cumsum(.5*(rate[1:]+rate[:-1])*np.diff(times))))
    scale = FLOW * times[-1]
    assert np.max(np.abs(cumulative - result.outlet_mass_kg)) < 1e-5 * scale
    cell = np.concatenate(([0.], np.cumsum(.5*FLOW*np.diff(times)*(
        result.outlet_concentration_kg_m3[1:]+result.outlet_concentration_kg_m3[:-1]))))
    assert np.max(np.abs(cell - result.outlet_mass_kg)) > 1e-3 * scale


def test_dispersive_column_converges_faster_with_tvd():
    config = klinkenberg_config(dispersion=2e-7)
    times = np.linspace(0, config.operation.duration_s, 101)
    reference = effluent_concentration(column(config, time_s=times, options=SolverOptions(
        axial_cells=800, axial_scheme="tvd")))
    errors = {}
    for scheme in ("upwind1", "tvd"):
        for cells in (25, 50):
            effluent = effluent_concentration(column(config, time_s=times, options=SolverOptions(
                axial_cells=cells, axial_scheme=scheme)))
            errors[scheme, cells] = np.max(np.abs(effluent - reference))
    assert errors["tvd", 50] < errors["upwind1", 50] / 5
    assert errors["tvd", 25] / errors["tvd", 50] > 3


def test_scheme_validation_default_and_hsdm_guard():
    assert SolverOptions().axial_scheme == "upwind1"
    for bad in ("TVD", "muscl", None, 2):
        with pytest.raises(ValueError):
            SolverOptions(axial_scheme=bad)
    hsdm = replace(klinkenberg_config(duration=10.),
                   kinetics=HSDM(surface_diffusivity_m2_s=1e-12, film_coefficient_m_s=1e-5))
    with pytest.raises(ValueError, match="HSDM"):
        column(hsdm, options=SolverOptions(axial_cells=4, radial_cells=3, axial_scheme="tvd"))


def test_upwind1_default_matches_historical_face_fluxes():
    transport = AxialTransport.from_config(klinkenberg_config(dispersion=1e-6), 6)
    c = np.linspace(.2, .9, 6)
    eps_d = BED.porosity * 1e-6
    dz = BED.length_m / 6
    expected = np.concatenate(([VELOCITY], VELOCITY*c[:-1] - eps_d*np.diff(c)/dz,
                               [VELOCITY*c[-1]]))
    assert_allclose(transport.face_flux(c), expected, rtol=1e-15)

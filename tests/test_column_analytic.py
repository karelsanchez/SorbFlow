"""Analytic-Jacobian checks with physical, predeclared comparison scales."""
import json
from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose

from pyfast import (
    HSDM,
    LDF,
    BatchConfig,
    Bed,
    Freundlich,
    Langmuir,
    Linear,
    Operation,
    SimulationConfig,
    Species,
)
from pyfast.equilibrium import isotherm_from_parameters
from pyfast.equilibrium.isotherms import trial_loading
from pyfast.reactors._ldf_jacobian import LDFColumnJacobian
from pyfast.simulate import batch, column
from pyfast.solvers import SolverOptions


def problem(equilibrium=None):
    return SimulationConfig(
        species=Species(name="independent-test-solute"),
        bed=Bed(length_m=.1, diameter_m=.01, particle_diameter_m=.0001,
                porosity=.4, particle_density_kg_m3=1000, material="generic"),
        operation=Operation(flow_m3_s=1e-7, inlet_concentration_kg_m3=.01,
                            duration_s=90., axial_dispersion_m2_s=1e-6),
        equilibrium=Linear(distribution_m3_kg=.002) if equilibrium is None else equilibrium,
        kinetics=LDF(rate_s_inv=.03),
    )


def independent_rhs(config, cells, state):
    """Flux balance assembled with scalar faces, independently of Jacobian storage."""
    bed, op = config.bed, config.operation
    dz = bed.length_m / cells
    u = op.flow_m3_s / (bed.volume_m3 / bed.length_m)
    c, q = state[:cells], state[cells:2*cells]
    model = isotherm_from_parameters(config.equilibrium)
    source = config.kinetics.rate_s_inv * (trial_loading(model, c) - q)
    flux = [u * op.inlet_concentration_kg_m3]
    for i in range(1, cells):
        flux.append(u*c[i-1] - bed.porosity*op.axial_dispersion_m2_s*(c[i]-c[i-1])/dz)
    flux.append(u*c[-1])
    dc = [-(flux[i+1]-flux[i])/(bed.porosity*dz)
          - bed.bulk_density_kg_m3/bed.porosity*source[i] for i in range(cells)]
    return np.concatenate((dc, source,
                           [op.flow_m3_s*op.inlet_concentration_kg_m3,
                            op.flow_m3_s*c[-1]]))


@pytest.mark.parametrize("cells", [2, 7])
@pytest.mark.parametrize("equilibrium", [Linear(distribution_m3_kg=0),
    Linear(distribution_m3_kg=.002), Langmuir(qmax_kg_kg=.0002, affinity_m3_kg=20)])
def test_jacobian_directional_derivative_including_trial_states(cells, equilibrium):
    config = problem(equilibrium)
    jac = LDFColumnJacobian(config, cells)
    for c in (np.linspace(-.003, .01, cells), np.zeros(cells),
              np.linspace(-1e-12, 1e-12, cells)):
        state = np.concatenate((c, np.linspace(0, 1e-5, cells), [0., 0.]))
        direction = np.linspace(-.01, .01, len(state))
        step = 1e-6
        numeric = (independent_rhs(config, cells, state+step*direction)
                   - independent_rhs(config, cells, state-step*direction))/(2*step)
        actual = jac(0., state) @ direction
        # Central differences crossing the odd extension at zero have O(step) error.
        assert_allclose(actual, numeric, rtol=2e-5, atol=1e-10)
        assert_allclose(actual[-2:], [0., config.operation.flow_m3_s*direction[cells-1]],
                        rtol=1e-14, atol=1e-18)
        assert jac(0., state).shape == (2*cells+2, 2*cells+2)


@pytest.mark.parametrize("method", ["BDF", "Radau"])
@pytest.mark.parametrize("rtol", [1e-6, 1e-8, 1e-10])
@pytest.mark.parametrize("case", ["tracer", "linear", "langmuir", "desorption"])
def test_analytic_matches_finite_difference_across_methods_and_tolerances(method, rtol, case):
    config = problem()
    if case == "tracer":
        config = replace(config, equilibrium=Linear(distribution_m3_kg=0))
    elif case in ("langmuir", "desorption"):
        config = replace(config, equilibrium=Langmuir(qmax_kg_kg=.0002, affinity_m3_kg=20))
    if case == "desorption":
        config = replace(config, operation=replace(config.operation,
            inlet_concentration_kg_m3=0, initial_concentration_kg_m3=.003,
            initial_loading_kg_kg=1e-5))
    settings = SolverOptions(method=method, rtol=rtol, axial_cells=12,
        atol_concentration_kg_m3=1e-13, atol_loading_kg_kg=1e-14, atol_mass_kg=1e-14)
    fd = column(config, options=settings)
    analytic = column(config, options=replace(settings, jacobian="analytic"))
    op, bed = config.operation, config.bed
    cscale = max(op.inlet_concentration_kg_m3, op.initial_concentration_kg_m3)
    qscale = max(op.initial_loading_kg_kg,
                 float(isotherm_from_parameters(config.equilibrium).loading([cscale])[0]))
    initial_mass = bed.volume_m3*(bed.porosity*op.initial_concentration_kg_m3
                                 + bed.bulk_density_kg_m3*op.initial_loading_kg_kg)
    mscale = max(initial_mass, op.flow_m3_s*op.inlet_concentration_kg_m3*op.duration_s)
    # Fixed physical scales work for tracer q=0 and desorption inlet mass=0.
    assert_allclose(analytic.concentration_kg_m3, fd.concentration_kg_m3,
                    rtol=0, atol=1e-5*cscale+1e-11)
    assert_allclose(analytic.loading_kg_kg, fd.loading_kg_kg,
                    rtol=0, atol=1e-5*qscale+1e-12)
    for name in ("inventory_kg", "inlet_mass_kg", "outlet_mass_kg"):
        assert_allclose(getattr(analytic, name), getattr(fd, name),
                        rtol=0, atol=1e-5*mscale+1e-13)
    assert analytic.diagnostics.max_scaled_mass_residual < 1e-7
    assert fd.diagnostics.max_scaled_mass_residual < 1e-7
    assert json.loads(analytic.options_json)["jacobian"] == "analytic"
    assert json.loads(fd.options_json)["jacobian"] == "finite_difference"
    assert analytic.numerical_sha256 != fd.numerical_sha256


@pytest.mark.parametrize("bad", [None, True, "auto", "exact", 1])
def test_invalid_jacobian_mode_rejected(bad):
    with pytest.raises(ValueError):
        SolverOptions(jacobian=bad)


def test_unsupported_models_do_not_silently_fall_back():
    config = problem(Freundlich(q_ref_kg_kg=.001, c_ref_kg_m3=.01, exponent=.8))
    options = SolverOptions(jacobian="analytic", axial_cells=4, radial_cells=3)
    with pytest.raises(ValueError):
        column(config, options=options)
    hsdm = replace(problem(), kinetics=HSDM(surface_diffusivity_m2_s=1e-12,
                                            film_coefficient_m_s=1e-5))
    with pytest.raises(ValueError):
        column(hsdm, options=options)
    closed = BatchConfig(species=config.species, material="generic", liquid_volume_m3=.001,
        adsorbent_mass_kg=.001, duration_s=10., initial_concentration_kg_m3=.01,
        initial_loading_kg_kg=0, equilibrium=Linear(distribution_m3_kg=.1),
        kinetics=LDF(rate_s_inv=.03))
    with pytest.raises(ValueError):
        batch(closed, options=options)

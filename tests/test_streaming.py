"""Dense/streaming equivalence and retention of internal-state physical checks."""
import json
from dataclasses import asdict, replace

import numpy as np
import pytest
from numpy.testing import assert_allclose

from sorbflow import (
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
from sorbflow.simulate import batch, column
from sorbflow.solvers import SolverOptions
from sorbflow.solvers.integration import IntegrationOutput, integrate_streaming
from sorbflow.solvers.results import PhysicsViolation, StreamingPhysics, check_physics


def problem(case="langmuir"):
    eq = Langmuir(qmax_kg_kg=.0002, affinity_m3_kg=20)
    if case == "tracer":
        eq = Linear(distribution_m3_kg=0)
    elif case == "linear":
        eq = Linear(distribution_m3_kg=.002)
    elif case == "freundlich":
        eq = Freundlich(q_ref_kg_kg=.0001, c_ref_kg_m3=.01, exponent=.8)
    op = Operation(flow_m3_s=1e-7, inlet_concentration_kg_m3=.01,
                   duration_s=90, axial_dispersion_m2_s=1e-6)
    if case == "desorption":
        op = replace(op, inlet_concentration_kg_m3=0, initial_concentration_kg_m3=.002,
                     initial_loading_kg_kg=.0001)
    return SimulationConfig(species=Species(name="test"),
        bed=Bed(length_m=.1, diameter_m=.01, particle_diameter_m=.0001,
                porosity=.4, particle_density_kg_m3=1000, material="generic"),
        operation=op, equilibrium=eq, kinetics=LDF(rate_s_inv=.03))


@pytest.mark.parametrize("method", ["BDF", "Radau"])
@pytest.mark.parametrize("rtol", [1e-6, 1e-8, 1e-10])
@pytest.mark.parametrize("case", ["tracer", "linear", "langmuir", "desorption", "freundlich"])
def test_dense_streaming_equivalent_for_all_supported_paths(method, rtol, case):
    cfg = problem(case)
    # Irregular requested times include very early states and a full horizon.
    times = np.array([0., 1e-5, .23, 2.7, 13., 49.1, 90.])
    modes = ["finite_difference"] if case == "freundlich" else ["analytic", "finite_difference"]
    for jac in modes:
        opts = SolverOptions(method=method, rtol=rtol, axial_cells=12,
            atol_concentration_kg_m3=1e-12, atol_loading_kg_kg=1e-13, jacobian=jac)
        dense = column(cfg, time_s=times, options=opts)
        stream = column(cfg, time_s=times, options=replace(opts, history="streaming"))
        for field in ["concentration_kg_m3", "loading_kg_kg", "inventory_kg",
                      "inlet_mass_kg", "outlet_mass_kg", "mass_residual_kg"]:
            # Same trajectory and arithmetic order: tight absolute floor for zero tracer.
            assert_allclose(getattr(stream, field), getattr(dense, field),
                            rtol=1e-12, atol=1e-20)
        assert asdict(stream.diagnostics) == asdict(dense.diagnostics)
        assert json.loads(stream.options_json)["history"] == "streaming"
        assert stream.numerical_sha256 != dense.numerical_sha256


def physics():
    return StreamingPhysics(cells=2, area=1., dz=1., epsilon=1., rho_b=0.,
        initial_mass=0., options=SolverOptions(), n_states=6, block=2)


def test_accumulator_matches_dense_and_mass_failure_message():
    states = np.asfortranarray([[0., .1, .2], [0., .2, .3], [0., 0., 0.],
                               [0., 0., 0.], [0., .3, .5], [0., 0., 0.]])
    opts = SolverOptions()
    for broken in [False, True]:
        y = states.copy(order="F")
        if broken:
            y[-1, 1] = .1
        p = physics()
        for i in range(y.shape[1]):
            p.push_state(y[:, i], "accepted", i, float(i))
        args = (y[:2], y[2:4], p.inventory(y), y[-2], y[-1], 0., opts,
                IntegrationOutput(y, y, 1, 2, 3, 4))
        if broken:
            with pytest.raises(Exception) as dense:
                check_physics(*args)
            with pytest.raises(PhysicsViolation) as stream:
                p.finalize(1, 2, 3, 4)
            assert str(stream.value) == str(dense.value)
            assert stream.value.location["index"] == 1
        else:
            assert p.finalize(1, 2, 3, 4) == check_physics(*args)


@pytest.mark.parametrize("method,expected", [("BDF", [1, 2, 2]), ("Radau", [1, 1, 2])])
def test_step_boundary_ownership_and_internal_violation(monkeypatch, method, expected):
    import sorbflow.solvers.integration as module

    class Fake:
        def __init__(self, rhs, t, y, tf, **kw):
            self.status, self.t, self.t_old = "running", 0., 0.
            self.y = y.copy()
            self.nfev, self.njev, self.nlu = 2, 0, 0
            self.step_index = 0

        def step(self):
            self.step_index += 1
            self.t_old, self.t = self.t, float(self.step_index)
            self.y[:] = 0
            if self.step_index == 1:
                self.y[0] = -1e-6
            else:
                self.status = "finished"

        def dense_output(self):
            step = self.step_index
            return lambda t: np.full((self.y.size, len(t)), float(step))

    monkeypatch.setitem(module.STREAMING_METHODS, method, Fake)
    opts = SolverOptions(method=method, history="streaming")
    sampled = integrate_streaming(lambda t, y: y, np.zeros(1), np.array([0., 1., 2.]),
                                  np.ones(1), opts)
    assert list(sampled.samples[0]) == expected
    # Requested states can be benign while an accepted state violates physics.
    p = physics()
    integrate_streaming(lambda t, y: y, np.zeros(6), np.array([0., 2.]),
                        np.ones(6), opts, on_state=p.push_state)
    with pytest.raises(PhysicsViolation, match="Negative liquid") as exc:
        p.finalize(2, 0, 0, 2)
    assert exc.value.location["kind"] == "accepted"
    assert exc.value.location["index"] == 1


def test_nonfinite_and_missing_samples_are_not_hidden():
    p = physics()
    y = np.zeros(6)
    y[0] = np.nan
    p.push_state(y, "accepted", 1, .5)
    with pytest.raises(PhysicsViolation, match="Nonfinite"):
        p.finalize(1, 0, 0, 1)
    with pytest.raises(ValueError):
        p.push_block(np.zeros((5, 2)), [("sample", 0, 0.), ("sample", 1, 1.)])


def test_bad_history_and_unsupported_batch_rejected():
    with pytest.raises(ValueError):
        SolverOptions(history="invalid")
    cfg = BatchConfig(species=Species(name="test"), material="generic",
        liquid_volume_m3=.001, adsorbent_mass_kg=.001, duration_s=1,
        initial_concentration_kg_m3=.01, initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=.1),
        kinetics=LDF(rate_s_inv=.1))
    with pytest.raises(ValueError, match="Streaming"):
        batch(cfg, options=SolverOptions(history="streaming"))


def test_streaming_hsdm_rejected_without_fallback():
    cfg = replace(problem(), kinetics=HSDM(surface_diffusivity_m2_s=1e-12,
                                          film_coefficient_m_s=1e-5))
    with pytest.raises(ValueError, match="Streaming"):
        column(cfg, options=SolverOptions(history="streaming"))

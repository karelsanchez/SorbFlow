"""Independent finite-volume tracer reference for sampled mass observations."""
import numpy as np
from numpy.testing import assert_allclose
from scipy.special import gammainc

from sorbflow import LDF, Bed, Linear, Operation, SimulationConfig, Species
from sorbflow.observation import CollectionWindow, SampledSignal, fraction_average
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions


def test_tracer_fraction_means_from_solver_mass_at_requested_endpoints():
    bed = Bed(length_m=.1, diameter_m=.01, particle_diameter_m=.0001,
              porosity=.4, particle_density_kg_m3=1000, material="generic")
    flow, c0, cells, delay = 1e-7, .01, 12, 1.25
    tau = bed.porosity * bed.volume_m3 / flow
    edges = [(delay - 1, delay + 3), (delay + .5 * tau, delay + 1.5 * tau),
             (delay + 2 * tau, delay + 3 * tau)]
    windows = [CollectionWindow(a, b, flow * (b - a)) for a, b in edges]
    times = np.unique([0., *[t - delay for pair in edges for t in pair if t >= delay]])
    config = SimulationConfig(species=Species(name="tracer"), bed=bed,
        operation=Operation(flow_m3_s=flow, inlet_concentration_kg_m3=c0,
                            duration_s=float(times[-1])),
        equilibrium=Linear(distribution_m3_kg=0), kinetics=LDF(rate_s_inv=.1))
    result = column(config, time_s=times, options=SolverOptions(
        axial_cells=cells, rtol=1e-10, atol_concentration_kg_m3=1e-13))
    sampled = SampledSignal(tuple(result.time_s), tuple(result.outlet_mass_kg))

    def exact_mass(time):
        if time <= 0:
            return 0.
        x = cells * time / tau
        return flow * c0 * (time * gammainc(cells, x) - tau * gammainc(cells + 1, x))

    actual = [fraction_average(sampled, w, delay_s=delay, initially_at_rest=True)
              for w in windows]
    expected = [(exact_mass(b-delay)-exact_mass(a-delay))/(flow*(b-a)) for a,b in edges]
    # Predeclared numerical tolerance; this compares the semi-discrete tracer, not PDE error.
    assert_allclose(actual, expected, rtol=1e-6, atol=2e-10)
    assert result.diagnostics.max_scaled_mass_residual < 1e-8

"""Closed batch balance with a conservative LDF source or HSDM particle diffusion."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike
from scipy.sparse import csc_matrix

from .._arrays import FloatArray
from ..equilibrium import isotherm_from_parameters
from ..equilibrium.isotherms import trial_loading
from ..kinetics.sphere import SphereGrid, diffusion_rhs, film_flux
from ..schemas import HSDM, BatchConfig, RunManifest
from ..solvers.integration import integrate
from ..solvers.options import SolverOptions, sample_times
from ..solvers.results import SimulationResult, check_physics, result_metadata
from ..units import finite_scalar


def simulate_batch(
    config: BatchConfig,
    *,
    time_s: ArrayLike | None = None,
    options: SolverOptions | None = None,
    code_revision: str = "uncommitted",
) -> SimulationResult:
    """Integrate c and q for a closed, single-solute, isothermal batch.

    LDF kinetics integrate the mean loading directly. HSDM kinetics (batch schema
    v2 with a declared particle) resolve the radial loading inside one particle
    size class with the shared spherical finite-volume grid and film solver.
    Tolerances use physical SI units. Internal accepted states are checked for
    nonnegativity and mass conservation before any success result is returned.
    """
    if not isinstance(config, BatchConfig):
        raise ValueError("config must be a BatchConfig")
    settings = SolverOptions() if options is None else options
    if not isinstance(settings, SolverOptions):
        raise ValueError("options must be SolverOptions")
    times = sample_times(config.duration_s, time_s)
    options_json, fingerprint, manifest = result_metadata(
        config.to_json(), times, settings, "batch", code_revision
    )
    if isinstance(config.kinetics, HSDM):
        return _simulate_hsdm_batch(config, times, settings, options_json, fingerprint, manifest)
    model = isotherm_from_parameters(config.equilibrium)
    ratio = finite_scalar(config.adsorbent_mass_kg / config.liquid_volume_m3, "mass/volume")
    initial = np.array([config.initial_concentration_kg_m3, config.initial_loading_kg_kg])
    initial_mass = finite_scalar(
        config.liquid_volume_m3 * initial[0] + config.adsorbent_mass_kg * initial[1], "initial_mass"
    )
    rate = config.kinetics.rate_s_inv

    def rhs(_time: float, state: FloatArray) -> FloatArray:
        source = rate * (trial_loading(model, state[:1])[0] - state[1])
        return np.array([-ratio * source, source])

    solution = integrate(
        rhs,
        initial,
        times,
        np.array([settings.atol_concentration_kg_m3, settings.atol_loading_kg_kg]),
        settings,
    )
    checked = solution.checkpoints
    inventory_checked = config.liquid_volume_m3 * checked[0] + config.adsorbent_mass_kg * checked[1]
    diagnostics = check_physics(
        checked[0],
        checked[1],
        inventory_checked,
        np.zeros(checked.shape[1]),
        np.zeros(checked.shape[1]),
        initial_mass,
        settings,
        solution,
    )
    c, q = solution.samples
    inventory = config.liquid_volume_m3 * c + config.adsorbent_mass_kg * q
    zeros = np.zeros(times.size)
    return SimulationResult(
        reactor="batch",
        time_s=times,
        concentration_kg_m3=c[:, None],
        loading_kg_kg=q[:, None],
        inventory_kg=inventory,
        inlet_mass_kg=zeros,
        outlet_mass_kg=zeros,
        mass_residual_kg=inventory - initial_mass,
        z_m=None,
        config_json=config.to_json(),
        options_json=options_json,
        numerical_sha256=fingerprint,
        manifest=manifest,
        diagnostics=diagnostics,
    )


def _simulate_hsdm_batch(
    config: BatchConfig,
    times: FloatArray,
    settings: SolverOptions,
    options_json: str,
    fingerprint: str,
    manifest: RunManifest,
) -> SimulationResult:
    """V_L dc/dt = -m_s d(q_mean)/dt with spherical surface diffusion and a film.

    The liquid source is the volume-weighted sum of the shell sources, so
    V_L*c + m_s*q_mean is a linear invariant of the discrete right-hand side
    (to rounding of m_s/V_L). BDF/Radau preserve a linear invariant only if the
    iteration matrix does too, so the Jacobian is assembled with the same structure:
    the exact (constant) linear diffusion block, the two film partial derivatives
    by centred finite differences of the scalar film solve, and the liquid row as
    -m_s/V_L times the weighted shell rows. A plain column-wise finite-difference
    Jacobian breaks that identity for nearly empty shells (tiny steps) and lets the
    inventory drift by ~1e-8 relative at default tolerances.

    Particle pore liquid is excluded (HSDM assumption); there are no inlet/outlet
    streams, so the accumulated exchange masses are identically zero as in the LDF
    batch.
    """
    if settings.jacobian == "analytic":
        raise ValueError(
            "Analytic Jacobian is not implemented for HSDM batch; the default "
            "finite_difference option uses a conservation-structured Jacobian"
        )
    kinetics, particle = config.kinetics, config.particle
    if not isinstance(kinetics, HSDM) or particle is None:
        raise ValueError("HSDM batch requires HSDM kinetics and a declared particle")
    nr = settings.radial_cells
    # Uniform shells unless the solver options carry a geometric surface refinement
    # (``radial_growth`` < 1), exactly as in the HSDM column; options are fingerprinted.
    grid = SphereGrid(particle.diameter_m / 2, nr, growth=settings.radial_growth)
    ds, kf, rho = (
        kinetics.surface_diffusivity_m2_s,
        kinetics.film_coefficient_m_s,
        particle.density_kg_m3,
    )
    volume, mass = config.liquid_volume_m3, config.adsorbent_mass_kg
    ratio = finite_scalar(mass / volume, "mass/volume")
    model = isotherm_from_parameters(config.equilibrium)
    weights = grid.mean_weights
    initial = np.concatenate(
        ([config.initial_concentration_kg_m3], np.full(nr, config.initial_loading_kg_kg))
    )
    initial_mass = finite_scalar(
        volume * config.initial_concentration_kg_m3 + mass * config.initial_loading_kg_kg,
        "initial_mass",
    )

    def film(bulk: FloatArray, outer: FloatArray) -> FloatArray:
        return film_flux(
            bulk,
            outer,
            model,
            grid=grid,
            diffusivity_m2_s=ds,
            particle_density_kg_m3=rho,
            film_coefficient_m_s=kf,
        )

    def rhs(_time: float, state: FloatArray) -> FloatArray:
        q = state[1:]
        transfer = film(state[:1], q[-1:])
        dq = diffusion_rhs(
            q[None], transfer, grid=grid, diffusivity_m2_s=ds, particle_density_kg_m3=rho
        )[0]
        # sum_r w_r dq_r equals 3 N / (rho_p R) for the exact shell volumes; using the
        # weighted sum keeps the discrete invariant exact instead of to O(eps) of N.
        return np.concatenate(([-ratio * float(weights @ dq)], dq))

    atol = np.concatenate(
        ([settings.atol_concentration_kg_m3], np.full(nr, settings.atol_loading_kg_kg))
    )
    # Linear diffusion operator with zero surface flux (exact, state independent)
    # and the sensitivity of the outer-shell source to the surface mass flux.
    diffusion = np.stack(
        [
            diffusion_rhs(
                unit[None], np.zeros(1), grid=grid, diffusivity_m2_s=ds, particle_density_kg_m3=rho
            )[0]
            for unit in np.eye(nr)
        ],
        axis=1,
    )
    outer_gain = grid.radius_m**2 / (rho * grid.shell_volumes_m3[-1])
    step = float(np.cbrt(np.finfo(float).eps))
    c_scale, q_scale = settings.atol_concentration_kg_m3, settings.atol_loading_kg_kg

    def jacobian(_time: float, state: FloatArray) -> csc_matrix:
        c, outer = state[:1], state[-1:]
        hc = step * np.maximum(np.abs(c), c_scale)
        hq = step * np.maximum(np.abs(outer), q_scale)
        # Centred differences; trial states below zero use the odd continuation.
        d_c = float(((film(c + hc, outer) - film(c - hc, outer)) / (2 * hc))[0])
        d_q = float(((film(c, outer + hq) - film(c, outer - hq)) / (2 * hq))[0])
        matrix = np.zeros((nr + 1, nr + 1))
        matrix[1:, 1:] = diffusion
        matrix[-1, 0] += outer_gain * d_c
        matrix[-1, -1] += outer_gain * d_q
        matrix[0] = -ratio * (weights @ matrix[1:])
        return csc_matrix(matrix)

    solution = integrate(rhs, initial, times, atol, settings, jac=jacobian)

    def inventory(states: FloatArray) -> FloatArray:
        return np.asarray(volume * states[0] + mass * (weights @ states[1:]))

    checked = solution.checkpoints
    zeros_checked = np.zeros(checked.shape[1])
    diagnostics = check_physics(
        checked[0],
        checked[1:],
        inventory(checked),
        zeros_checked,
        zeros_checked,
        initial_mass,
        settings,
        solution,
    )
    sampled = solution.samples
    held = inventory(sampled)
    zeros = np.zeros(times.size)
    return SimulationResult(
        reactor="batch",
        time_s=times,
        concentration_kg_m3=sampled[0][:, None],
        loading_kg_kg=(weights @ sampled[1:])[:, None],
        inventory_kg=held,
        inlet_mass_kg=zeros,
        outlet_mass_kg=zeros,
        mass_residual_kg=held - initial_mass,
        z_m=None,
        radial_loading_kg_kg=sampled[1:].T.reshape(times.size, 1, nr),
        r_m=grid.centers_m,
        config_json=config.to_json(),
        options_json=options_json,
        numerical_sha256=fingerprint,
        manifest=manifest,
        diagnostics=diagnostics,
    )

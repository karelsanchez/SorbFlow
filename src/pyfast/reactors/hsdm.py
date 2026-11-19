"""Aqueous HSDM column: axial FV, spherical radial FV and finite film resistance."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike
from scipy.sparse import csc_matrix

from .._arrays import FloatArray
from ..equilibrium import isotherm_from_parameters
from ..kinetics.sphere import SphereGrid, diffusion_rhs, film_flux
from ..schemas import HSDM, SimulationConfig
from ..solvers.integration import integrate
from ..solvers.options import SolverOptions, sample_times
from ..solvers.results import SimulationResult, check_physics, result_metadata
from ..units import finite_scalar


def _pattern(axial: int, radial: int) -> csc_matrix:
    rows: list[int] = []
    cols: list[int] = []
    for i in range(axial):
        for j in range(max(0, i - 1), min(axial, i + 2)):
            rows.append(i)
            cols.append(j)
        rows.append(i)
        cols.append(axial + (i + 1) * radial - 1)
        for r in range(radial):
            index = axial + i * radial + r
            for k in range(max(0, r - 1), min(radial, r + 2)):
                rows.append(index)
                cols.append(axial + i * radial + k)
            if r == radial - 1:
                rows.append(index)
                cols.append(i)
    states = axial * (radial + 1) + 2
    rows.append(states - 1)
    cols.append(axial - 1)
    return csc_matrix((np.ones(len(rows)), (rows, cols)), shape=(states, states))


def simulate_hsdm_column(
    config: SimulationConfig,
    *,
    time_s: ArrayLike | None = None,
    options: SolverOptions | None = None,
    code_revision: str = "uncommitted",
) -> SimulationResult:
    """Solve spherical surface diffusion coupled to an aqueous column and a film.

    Particle liquid storage is excluded by the HSDM assumption. A single particle
    size, dry-mass density and fixed T apply. Internal and sampled states are checked.
    """
    if not isinstance(config.kinetics, HSDM):
        raise ValueError("HSDM parameter contract is required")
    settings = SolverOptions() if options is None else options
    if not isinstance(settings, SolverOptions):
        raise ValueError("options must be SolverOptions")
    times = sample_times(config.operation.duration_s, time_s)
    options_json, fingerprint, manifest = result_metadata(
        config.to_json(), times, settings, "column", code_revision
    )
    bed, op, kinetics = config.bed, config.operation, config.kinetics
    n, nr = settings.axial_cells, settings.radial_cells
    grid = SphereGrid(bed.particle_diameter_m / 2, nr)
    dz = bed.length_m / n
    area = finite_scalar(bed.volume_m3 / bed.length_m, "cross-sectional area")
    velocity = finite_scalar(op.flow_m3_s / area, "superficial velocity")
    eps, rho = bed.porosity, bed.particle_density_kg_m3
    specific_area = 3 * (1 - eps) / grid.radius_m
    model = isotherm_from_parameters(config.equilibrium)
    initial = np.concatenate(
        (
            np.full(n, op.initial_concentration_kg_m3),
            np.full(n * nr, op.initial_loading_kg_kg),
            np.zeros(2),
        )
    )
    initial_mass = finite_scalar(
        bed.volume_m3
        * (
            eps * op.initial_concentration_kg_m3 + bed.bulk_density_kg_m3 * op.initial_loading_kg_kg
        ),
        "initial mass",
    )

    def rhs(_time: float, state: FloatArray) -> FloatArray:
        c, q = state[:n], state[n:-2].reshape(n, nr)
        transfer = film_flux(
            c,
            q[:, -1],
            model,
            grid=grid,
            diffusivity_m2_s=kinetics.surface_diffusivity_m2_s,
            particle_density_kg_m3=rho,
            film_coefficient_m_s=kinetics.film_coefficient_m_s,
        )
        dq = diffusion_rhs(
            q,
            transfer,
            grid=grid,
            diffusivity_m2_s=kinetics.surface_diffusivity_m2_s,
            particle_density_kg_m3=rho,
        )
        flux = np.empty(n + 1)
        flux[0] = velocity * op.inlet_concentration_kg_m3
        flux[1:n] = velocity * c[:-1] - eps * op.axial_dispersion_m2_s * np.diff(c) / dz
        flux[-1] = velocity * c[-1]
        dc = (-np.diff(flux) / dz - specific_area * transfer) / eps
        return np.concatenate(
            (dc, dq.ravel(), [op.flow_m3_s * op.inlet_concentration_kg_m3, op.flow_m3_s * c[-1]])
        )

    atol = np.concatenate(
        (
            np.full(n, settings.atol_concentration_kg_m3),
            np.full(n * nr, settings.atol_loading_kg_kg),
            np.full(2, settings.atol_mass_kg),
        )
    )
    solution = integrate(rhs, initial, times, atol, settings, _pattern(n, nr))

    def average(states: FloatArray) -> FloatArray:
        q = states[n:-2].reshape(n, nr, states.shape[1])
        return np.asarray(np.einsum("irt,r->it", q, grid.mean_weights))

    def inventory(states: FloatArray) -> FloatArray:
        return np.asarray(
            area
            * dz
            * (
                eps * np.sum(states[:n], axis=0)
                + bed.bulk_density_kg_m3 * np.sum(average(states), axis=0)
            )
        )

    checked = solution.checkpoints
    diagnostics = check_physics(
        checked[:n],
        checked[n:-2],
        inventory(checked),
        checked[-2],
        checked[-1],
        initial_mass,
        settings,
        solution,
    )
    sampled = solution.samples
    mass = inventory(sampled)
    return SimulationResult(
        reactor="column",
        time_s=times,
        concentration_kg_m3=sampled[:n].T,
        loading_kg_kg=average(sampled).T,
        inventory_kg=mass,
        inlet_mass_kg=sampled[-2],
        outlet_mass_kg=sampled[-1],
        mass_residual_kg=mass - initial_mass - sampled[-2] + sampled[-1],
        z_m=np.asarray((np.arange(n, dtype=np.float64) + 0.5) * dz),
        radial_loading_kg_kg=sampled[n:-2].T.reshape(times.size, n, nr),
        r_m=grid.centers_m,
        config_json=config.to_json(),
        options_json=options_json,
        numerical_sha256=fingerprint,
        manifest=manifest,
        diagnostics=diagnostics,
    )

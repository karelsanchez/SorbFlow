"""Conservative method-of-lines fixed-bed LDF model, independent of FAST."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike
from scipy.sparse import csc_matrix

from .._arrays import FloatArray
from ..equilibrium import isotherm_from_parameters
from ..equilibrium.isotherms import trial_loading
from ..schemas import LDF, Langmuir, Linear, SimulationConfig
from ..solvers.integration import integrate, integrate_streaming
from ..solvers.options import SolverOptions, sample_times
from ..solvers.results import SimulationResult, StreamingPhysics, check_physics, result_metadata
from ..units import finite_scalar
from ._ldf_jacobian import LDFColumnJacobian


def _jacobian_pattern(cells: int) -> csc_matrix:
    rows: list[int] = []
    cols: list[int] = []
    for i in range(cells):
        for j in range(max(0, i - 1), min(cells, i + 2)):
            rows.append(i)
            cols.append(j)
        rows.extend((i, cells + i, cells + i))
        cols.extend((cells + i, i, cells + i))
    rows.append(2 * cells + 1)
    cols.append(cells - 1)
    return csc_matrix((np.ones(len(rows)), (rows, cols)), shape=(2 * cells + 2, 2 * cells + 2))


def simulate_column(
    config: SimulationConfig,
    *,
    time_s: ArrayLike | None = None,
    options: SolverOptions | None = None,
    code_revision: str = "uncommitted",
) -> SimulationResult:
    """Solve a uniform aqueous column using upwind FV, dispersion and LDF.

    Constant positive flow/inlet, dry mass basis, one solute and fixed T only.
    HSDM dispatches to its radial solver; it is never replaced by LDF.
    """
    if not isinstance(config, SimulationConfig):
        raise ValueError("config must be a SimulationConfig")
    settings = SolverOptions() if options is None else options
    if not isinstance(settings, SolverOptions):
        raise ValueError("options must be SolverOptions")
    if settings.jacobian == "analytic" and (
        not isinstance(config.kinetics, LDF)
        or not isinstance(config.equilibrium, (Langmuir, Linear))
    ):
        raise ValueError("Analytic Jacobian supports only LDF with Langmuir or Linear")
    if settings.history == "streaming" and not isinstance(config.kinetics, LDF):
        raise ValueError("Streaming history supports LDF columns only")
    if not isinstance(config.kinetics, LDF):
        from .hsdm import simulate_hsdm_column

        return simulate_hsdm_column(
            config, time_s=time_s, options=options, code_revision=code_revision
        )
    times = sample_times(config.operation.duration_s, time_s)
    options_json, fingerprint, manifest = result_metadata(
        config.to_json(), times, settings, "column", code_revision
    )
    bed, op = config.bed, config.operation
    cells = settings.axial_cells
    dz = bed.length_m / cells
    area = finite_scalar(bed.volume_m3 / bed.length_m, "cross-sectional area")
    velocity = finite_scalar(op.flow_m3_s / area, "superficial velocity")
    epsilon, rho_b = bed.porosity, bed.bulk_density_kg_m3
    model = isotherm_from_parameters(config.equilibrium)
    rate = config.kinetics.rate_s_inv
    initial = np.concatenate(
        (
            np.full(cells, op.initial_concentration_kg_m3),
            np.full(cells, op.initial_loading_kg_kg),
            np.zeros(2),
        )
    )
    initial_mass = finite_scalar(
        bed.volume_m3
        * (epsilon * op.initial_concentration_kg_m3 + rho_b * op.initial_loading_kg_kg),
        "initial mass",
    )

    def rhs(_time: float, state: FloatArray) -> FloatArray:
        c, q = state[:cells], state[cells : 2 * cells]
        source = rate * (trial_loading(model, c) - q)
        flux = np.empty(cells + 1)
        flux[0] = velocity * op.inlet_concentration_kg_m3
        flux[1:cells] = velocity * c[:-1] - epsilon * op.axial_dispersion_m2_s * np.diff(c) / dz
        flux[cells] = velocity * c[-1]
        dc = -np.diff(flux) / (epsilon * dz) - (rho_b / epsilon) * source
        return np.concatenate(
            (dc, source, [op.flow_m3_s * op.inlet_concentration_kg_m3, op.flow_m3_s * c[-1]])
        )

    atol = np.concatenate(
        (
            np.full(cells, settings.atol_concentration_kg_m3),
            np.full(cells, settings.atol_loading_kg_kg),
            np.full(2, settings.atol_mass_kg),
        )
    )
    jac = LDFColumnJacobian(config, cells) if settings.jacobian == "analytic" else None

    def inventory(states: FloatArray) -> FloatArray:
        return np.asarray(
            area
            * dz
            * (
                epsilon * np.sum(states[:cells], axis=0)
                + rho_b * np.sum(states[cells : 2 * cells], axis=0)
            )
        )

    if settings.history == "streaming":
        physics = StreamingPhysics(cells=cells, area=area, dz=dz, epsilon=epsilon,
            rho_b=rho_b, initial_mass=initial_mass, options=settings, n_states=initial.size)
        streamed = integrate_streaming(rhs, initial, times, atol, settings,
            _jacobian_pattern(cells), jac=jac, on_state=physics.push_state)
        sampled = streamed.samples
        physics.push_block(sampled, [("sample", i, float(t)) for i, t in enumerate(times)])
        diagnostics = physics.finalize(streamed.nfev, streamed.njev, streamed.nlu,
                                       streamed.accepted_steps)
    else:
        solution = integrate(rhs, initial, times, atol, settings, _jacobian_pattern(cells), jac=jac)
        checked = solution.checkpoints
        diagnostics = check_physics(checked[:cells], checked[cells:2*cells], inventory(checked),
            checked[-2], checked[-1], initial_mass, settings, solution)
        sampled = solution.samples
    mass = inventory(sampled)
    return SimulationResult(
        reactor="column",
        time_s=times,
        concentration_kg_m3=sampled[:cells].T,
        loading_kg_kg=sampled[cells : 2 * cells].T,
        inventory_kg=mass,
        inlet_mass_kg=sampled[-2],
        outlet_mass_kg=sampled[-1],
        mass_residual_kg=mass - initial_mass - sampled[-2] + sampled[-1],
        z_m=np.asarray((np.arange(cells, dtype=np.float64) + 0.5) * dz),
        config_json=config.to_json(),
        options_json=options_json,
        numerical_sha256=fingerprint,
        manifest=manifest,
        diagnostics=diagnostics,
    )

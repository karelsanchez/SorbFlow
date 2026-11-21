"""Closed batch balance with a shared, conservative LDF mass source."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from .._arrays import FloatArray
from ..equilibrium import isotherm_from_parameters
from ..equilibrium.isotherms import trial_loading
from ..schemas import BatchConfig
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
    model = isotherm_from_parameters(config.equilibrium)
    ratio = finite_scalar(config.adsorbent_mass_kg / config.liquid_volume_m3, "mass/volume")
    initial = np.array([config.initial_concentration_kg_m3, config.initial_loading_kg_kg])
    initial_mass = finite_scalar(
        config.liquid_volume_m3 * initial[0] + config.adsorbent_mass_kg * initial[1], "initial_mass"
    )

    def rhs(_time: float, state: FloatArray) -> FloatArray:
        source = config.kinetics.rate_s_inv * (trial_loading(model, state[:1])[0] - state[1])
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

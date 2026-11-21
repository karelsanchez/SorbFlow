"""Quantitative independent references for the numerical verification report."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from run_ldf import configuration
from scipy.integrate import solve_ivp, trapezoid
from scipy.special import gammainc

from sorbflow import LDF, BatchConfig, Linear, Species
from sorbflow.kinetics.sphere import SphereGrid, diffusion_rhs
from sorbflow.simulate import batch, column
from sorbflow.solvers import SolverOptions


def main(path: Path) -> None:
    batch_config = BatchConfig(
        species=Species(name="analytic"),
        material="generic",
        liquid_volume_m3=0.001,
        adsorbent_mass_kg=0.002,
        duration_s=300,
        initial_concentration_kg_m3=0.01,
        initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=0.5),
        kinetics=LDF(rate_s_inv=0.02),
    )
    result = batch(
        batch_config,
        options=SolverOptions(rtol=1e-9, atol_concentration_kg_m3=1e-13, atol_loading_kg_kg=1e-14),
    )
    exact = 0.005 + 0.005 * np.exp(-0.04 * result.time_s)
    base = configuration()
    tau = base.bed.porosity * base.bed.volume_m3 / base.operation.flow_m3_s
    base = replace(
        base,
        equilibrium=Linear(distribution_m3_kg=0),
        operation=replace(base.operation, duration_s=3 * tau),
    )
    times = np.linspace(0, 3 * tau, 1201)
    tracer_metrics = []
    for n in (25, 50, 100, 200):
        run = column(
            base,
            time_s=times,
            options=SolverOptions(axial_cells=n, rtol=1e-9, atol_concentration_kg_m3=1e-13),
        )
        normalized = run.outlet_concentration_kg_m3 / 0.01
        fv_reference = gammainc(n, n * times / tau)
        tracer_metrics.append(
            dict(
                axial_cells=n,
                max_absolute_error_against_tanks=float(np.max(np.abs(normalized - fv_reference))),
                l1_front_error_normalized=float(
                    trapezoid(np.abs(normalized - (times >= tau)), times) / tau
                ),
                t50_relative_error=float(abs(np.interp(0.5, normalized, times) / tau - 1)),
                max_scaled_mass_residual=run.diagnostics.max_scaled_mass_residual,
            )
        )
    radial_metrics = []
    fo = np.array([0.01, 0.03, 0.1, 0.3, 1.0])
    terms = np.arange(1, 1001)[:, None]
    exact_particle = 1 - 6 / np.pi**2 * np.sum(
        np.exp(-(terms**2) * np.pi**2 * fo) / terms**2, axis=0
    )
    for n in (10, 20, 40, 80):
        grid = SphereGrid(1.0, n)

        def rhs(t, q, grid=grid):
            flux = np.array([(1 - q[-1]) / (1 - grid.centers_m[-1])])
            return diffusion_rhs(
                q[None], flux, grid=grid, diffusivity_m2_s=1, particle_density_kg_m3=1
            )[0]

        particle = solve_ivp(
            rhs, (0, 1), np.zeros(n), method="BDF", t_eval=fo, rtol=1e-10, atol=1e-12
        )
        if not particle.success:
            raise RuntimeError(particle.message)
        radial_metrics.append(
            dict(
                radial_cells=n,
                max_mean_loading_error=float(
                    np.max(np.abs(grid.mean_weights @ particle.y - exact_particle))
                ),
            )
        )
    data = {
        "status": "selected numerical references; not experimental validation",
        "batch_linear_max_absolute_c_error_kg_m3": float(
            np.max(np.abs(result.outlet_concentration_kg_m3 - exact))
        ),
        "batch_linear_max_scaled_mass_residual": result.diagnostics.max_scaled_mass_residual,
        "tracer": tracer_metrics,
        "spherical_diffusion": radial_metrics,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)

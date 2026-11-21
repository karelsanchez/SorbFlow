"""Synthetic API workflow: fit -> LDF/HSDM -> UQ -> hydraulics -> DXF/report.

Run: python examples/scientific_demo.py --output NEW_DIRECTORY
All model parameters and data are synthetic. No experimental validation is claimed.
Figures use optional matplotlib (also installed by the optimize extra).
"""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from run_ldf import configuration

from sorbflow import HSDM, Langmuir
from sorbflow.design import export_dxf, hydraulics
from sorbflow.equilibrium import isotherm_from_parameters
from sorbflow.fit import isotherm
from sorbflow.io import export_parquet, export_result
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions
from sorbflow.uncertainty import monte_carlo


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    config = configuration()
    concentrations = np.geomspace(0.0001, 1, 30)
    measured = isotherm_from_parameters(config.equilibrium).loading(concentrations)
    fit = isotherm(
        concentrations,
        measured,
        Langmuir(qmax_kg_kg=0.003, affinity_m3_kg=5),
        std_loading_kg_kg=np.full(30, 1e-5),
    )
    if not isinstance(fit.parameters, Langmuir):
        raise RuntimeError("Unexpected fitted parameter contract")
    config = replace(config, equilibrium=fit.parameters)
    ldf = column(config, options=SolverOptions(axial_cells=80))
    hsdm = column(
        replace(config, kinetics=HSDM(surface_diffusivity_m2_s=1e-12, film_coefficient_m_s=1e-5)),
        options=SolverOptions(axial_cells=40, radial_cells=16),
    )
    export_result(ldf, output / "ldf")
    export_result(hsdm, output / "hsdm")
    try:
        export_parquet(ldf, output / "ldf" / "timeseries.parquet")
        export_parquet(hsdm, output / "hsdm" / "timeseries.parquet")
    except ImportError:
        print("Parquet skipped: optional pyarrow is not installed")
    export_dxf(config.bed, output / "process_envelope.dxf")
    hydraulic = hydraulics(
        config.bed,
        flow_m3_s=config.operation.flow_m3_s,
        fluid_density_kg_m3=997,
        viscosity_pa_s=0.00089,
        pump_efficiency=0.6,
    )
    log_mean = np.log([fit.parameters.qmax_kg_kg, fit.parameters.affinity_m3_kg])
    covariance = fit.covariance_log_parameters
    if covariance is None:
        raise RuntimeError("Synthetic fit is not locally identifiable")

    def sampler(rng, n):
        return np.exp(rng.multivariate_normal(log_mean, covariance, size=n))

    def evaluate(values):
        scenario = replace(
            config,
            operation=replace(config.operation, duration_s=2200),
            equilibrium=Langmuir(qmax_kg_kg=values[0], affinity_m3_kg=values[1]),
        )
        result = column(scenario, time_s=[0, 2200], options=SolverOptions(axial_cells=30))
        return [result.outlet_concentration_kg_m3[-1], result.inventory_kg[-1]]

    uncertainty = monte_carlo(
        evaluate,
        sampler,
        n_samples=32,
        seed=42,
        model_id="synthetic-demo-local-lognormal-fit-covariance-v1",
    )
    report = {
        "data_status": "synthetic; no experimental validation",
        "fitted_equilibrium": asdict(fit.parameters),
        "fit_log_jacobian_condition": fit.jacobian_condition,
        "uq_assumption": (
            "Local lognormal approximation from a specified synthetic measurement sigma"
        ),
        "uq_seed": uncertainty.seed,
        "uq_n": len(uncertainty.inputs_si),
        "uq_inputs_si": uncertainty.inputs_si.tolist(),
        "uq_outputs_si": uncertainty.outputs_si.tolist(),
        "uq_output_names": ["outlet_concentration_at_2200s_kg_m3", "inventory_at_2200s_kg"],
        "uq_quantiles": uncertainty.quantiles.tolist(),
        "uq_probabilities": uncertainty.probabilities.tolist(),
        "uq_mean_standard_error": uncertainty.standard_error_mean.tolist(),
        "uq_samples_sha256": uncertainty.samples_sha256,
        "hydraulics": asdict(hydraulic),
        "ldf_diagnostics": asdict(ldf.diagnostics),
        "hsdm_diagnostics": asdict(hsdm.diagnostics),
    }
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Figure skipped: optional matplotlib is not installed")
    else:
        fig, ax = plt.subplots(figsize=(7, 4.2), layout="constrained")
        ax.plot(ldf.time_s / 60, ldf.outlet_concentration_kg_m3 / 0.01, label="LDF")
        ax.plot(hsdm.time_s / 60, hsdm.outlet_concentration_kg_m3 / 0.01, label="HSDM + film")
        ax.set(
            xlabel="Time (min)",
            ylabel="Outlet concentration / inlet concentration",
            title="SorbFlow — synthetic aqueous column (distinct kinetic assumptions)",
        )
        ax.grid(alpha=0.25)
        ax.legend()
        fig.savefig(output / "breakthrough.png", dpi=180)
        fig.savefig(output / "breakthrough.svg")
        plt.close(fig)
    print(f"Synthetic scientific workflow saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)

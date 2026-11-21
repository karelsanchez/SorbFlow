"""Preliminary robust column design with frozen synthetic uncertainty scenarios.

Run with the optimize extra installed:
python examples/robust_column_design.py --output NEW_DIRECTORY

This is a small demonstration budget, not a convergence certificate or validated
industrial design. All returned candidates are rechecked on a finer axial grid.
"""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from run_ldf import configuration

from sorbflow import Langmuir
from sorbflow.design import export_dxf, hydraulics
from sorbflow.optimize import Evaluation, nsga2
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions


def main(output: Path, population: int, generations: int) -> None:
    output.mkdir(parents=True, exist_ok=False)
    base = configuration()
    base = replace(base, operation=replace(base.operation, duration_s=1800))
    # Assumed scenario uncertainty, not an experimental posterior. Freeze across designs.
    scenarios = np.random.default_rng(123).lognormal(mean=0, sigma=0.1, size=(3, 2))
    effluent_limit = 0.001
    pressure_limit = 20000.0

    def evaluate(values, cells=20):
        bed = replace(base.bed, length_m=float(values[0]), diameter_m=float(values[1]))
        hydraulic = hydraulics(
            bed,
            flow_m3_s=base.operation.flow_m3_s,
            fluid_density_kg_m3=997,
            viscosity_pa_s=0.00089,
            pump_efficiency=0.6,
        )
        outlets = []
        for multiplier in scenarios:
            config = replace(
                base,
                bed=bed,
                equilibrium=Langmuir(
                    qmax_kg_kg=0.005 * multiplier[0], affinity_m3_kg=10 * multiplier[1]
                ),
            )
            result = column(config, time_s=[0, 1800], options=SolverOptions(axial_cells=cells))
            outlets.append(result.outlet_concentration_kg_m3[-1])
        return Evaluation(
            objectives=[hydraulic.dry_adsorbent_mass_kg, hydraulic.pump_power_w * 1800],
            constraints=[
                max(outlets) / effluent_limit - 1,
                hydraulic.pressure_drop_pa / pressure_limit - 1,
            ],
        )

    front = nsga2(
        evaluate,
        [0.05, 0.01],
        [0.2, 0.03],
        variable_units=("m", "m"),
        objective_units=("kg_dry_adsorbent", "J"),
        problem_id="synthetic-robust-column-LDF-v1",
        seed=42,
        n_constraints=2,
        population_size=population,
        generations=generations,
    )
    checked = []
    for index, candidate in enumerate(front.decisions_si):
        refined = evaluate(candidate, cells=80)
        accepted = bool(np.all(np.asarray(refined.constraints) <= 0))
        checked.append(
            {
                "length_m": float(candidate[0]),
                "diameter_m": float(candidate[1]),
                "fine_grid_objectives_si": refined.objectives,
                "fine_grid_constraints": refined.constraints,
                "fine_grid_feasible": accepted,
            }
        )
        if accepted:
            export_dxf(
                replace(base.bed, length_m=float(candidate[0]), diameter_m=float(candidate[1])),
                output / f"candidate_{index}.dxf",
            )
    data = {
        "status": "preliminary; synthetic scenarios; not experimentally validated",
        "base_config": json.loads(base.to_json()),
        "solver_coarse": asdict(SolverOptions(axial_cells=20)),
        "solver_refined": asdict(SolverOptions(axial_cells=80)),
        "scenario_seed": 123,
        "scenario_multipliers": scenarios.tolist(),
        "effluent_limit_kg_m3": effluent_limit,
        "pressure_limit_pa": pressure_limit,
        "pareto_specification": json.loads(front.specification_json),
        "evaluations": front.evaluations,
        "candidates": checked,
    }
    (output / "robust_design.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(
        f"Saved {len(checked)} preliminary candidates; "
        f"{sum(c['fine_grid_feasible'] for c in checked)} pass the fine-grid feasibility check"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--population", type=int, default=16)
    parser.add_argument("--generations", type=int, default=5)
    args = parser.parse_args()
    main(args.output, args.population, args.generations)

"""Generate a synthetic aqueous breakthrough curve with the independent solver.

Usage: python examples/run_ldf.py --output NEW_DIRECTORY
No experimental parameters, calibration or physical validation are claimed.
"""

import argparse

from pyfast import LDF, Bed, Langmuir, Operation, SimulationConfig, Species
from pyfast.io import export_result
from pyfast.simulate import column
from pyfast.solvers import SolverOptions


def configuration() -> SimulationConfig:
    return SimulationConfig(
        species=Species(name="synthetic-aqueous-solute"),
        bed=Bed(
            length_m=0.1,
            diameter_m=0.01,
            particle_diameter_m=0.0001,
            porosity=0.4,
            particle_density_kg_m3=1000,
            material="synthetic-adsorbent",
        ),
        operation=Operation(flow_m3_s=1e-7, inlet_concentration_kg_m3=0.01, duration_s=5000),
        equilibrium=Langmuir(qmax_kg_kg=0.005, affinity_m3_kg=10),
        kinetics=LDF(rate_s_inv=0.01),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = column(configuration(), options=SolverOptions(axial_cells=100))
    export_result(result, args.output)
    print(result.diagnostics)

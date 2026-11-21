"""Command-line interface for independent batch and column LDF simulations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from .io import export_result
from .reactors import simulate_batch, simulate_column
from .schemas import BatchConfig, SimulationConfig
from .solvers import SimulationError, SolverOptions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SorbFlow — aqueous LDF simulations in SI")
    parser.add_argument("reactor", choices=("batch", "column"))
    parser.add_argument("config", type=Path, help="Versioned JSON configuration")
    parser.add_argument("--output", required=True, type=Path, help="New output directory")
    parser.add_argument("--method", choices=("BDF", "Radau"), default="BDF")
    parser.add_argument("--cells", type=int, default=100)
    parser.add_argument("--radial-cells", type=int, default=20)
    parser.add_argument("--samples", type=int, default=201)
    parser.add_argument("--rtol", type=float, default=1e-7)
    parser.add_argument("--code-revision", default="uncommitted")
    args = parser.parse_args(argv)
    try:
        if args.samples < 2:
            raise ValueError("--samples must be >=2")
        if args.output.exists():
            raise FileExistsError(f"Output directory already exists: {args.output}")
        options = SolverOptions(
            method=args.method,
            axial_cells=args.cells,
            radial_cells=args.radial_cells,
            rtol=args.rtol,
        )
        payload = args.config.read_text(encoding="utf-8-sig")
        if args.reactor == "batch":
            batch_config = BatchConfig.from_json(payload)
            result = simulate_batch(
                batch_config,
                options=options,
                code_revision=args.code_revision,
                time_s=np.linspace(0, batch_config.duration_s, args.samples),
            )
        else:
            column_config = SimulationConfig.from_json(payload)
            result = simulate_column(
                column_config,
                options=options,
                code_revision=args.code_revision,
                time_s=np.linspace(0, column_config.operation.duration_s, args.samples),
            )
        export_result(result, args.output)
    except (OSError, ValueError, SimulationError, NotImplementedError) as exc:
        print(f"SorbFlow error: {exc}", file=sys.stderr)
        return 2
    print(f"Saved {result.reactor} simulation to {args.output}")
    print(f"Mass residual max: {result.diagnostics.max_abs_mass_residual_kg:.6g} kg")
    print("Numerical checks passed (mass balance and state constraints).")
    return 0

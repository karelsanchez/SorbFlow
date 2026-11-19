"""Portable result export without silently overwriting a previous simulation."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from ..solvers import SimulationResult


def export_result(result: SimulationResult, destination: str | Path) -> Path:
    """Write full JSON, outlet CSV and file hashes to a new directory.

    Existing directories are rejected, including empty ones, to preserve run identity.
    CSV includes SI units in column names; JSON contains all axial fields and inputs.
    """
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=False)
    (path / "result.json").write_text(result.to_json(), encoding="utf-8")
    with (path / "timeseries.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "time_s",
                "outlet_concentration_kg_m3",
                "inventory_kg",
                "inlet_mass_kg",
                "outlet_mass_kg",
                "mass_residual_kg",
            ]
        )
        writer.writerows(
            zip(
                result.time_s,
                result.outlet_concentration_kg_m3,
                result.inventory_kg,
                result.inlet_mass_kg,
                result.outlet_mass_kg,
                result.mass_residual_kg,
                strict=True,
            )
        )
    hashes = {
        name: hashlib.sha256((path / name).read_bytes()).hexdigest()
        for name in ("result.json", "timeseries.csv")
    }
    (path / "files.sha256.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    return path

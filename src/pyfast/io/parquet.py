"""Optional Parquet export of outlet series and global mass-balance evidence."""

from __future__ import annotations

import json
from dataclasses import asdict
from importlib import import_module
from pathlib import Path

from .._arrays import real_array
from ..solvers import SimulationResult


def export_parquet(result: SimulationResult, destination: str | Path) -> Path:
    """Write a time-series Parquet file with units and reproducibility metadata.

    Requires the optional ``parquet`` extra. This table contains the outlet (or
    mixed batch liquid) and global mass balance, not full axial/radial profiles.
    Use ``export_result`` for the complete JSON fields. All numeric columns are
    float64 in SI; per-field metadata identifies units. File metadata records the
    configuration, solver settings, diagnostics, run manifest and numerical hash.

    Existing files are never overwritten, including under a creation race. If an
    I/O failure occurs during writing, a partial new file may remain for inspection.
    """
    if not isinstance(result, SimulationResult):
        raise ValueError("result must be a SimulationResult")
    target = Path(destination)
    if target.exists():
        raise FileExistsError(f"Output file already exists: {target}")
    try:
        arrow = import_module("pyarrow")
        parquet = import_module("pyarrow.parquet")
    except ImportError as exc:
        raise ImportError("Install pyfast-adsorption[parquet] to export Parquet") from exc

    columns = {
        "time_s": (result.time_s, "s"),
        "outlet_concentration_kg_m3": (result.outlet_concentration_kg_m3, "kg/m^3"),
        "inventory_kg": (result.inventory_kg, "kg"),
        "inlet_mass_kg": (result.inlet_mass_kg, "kg"),
        "outlet_mass_kg": (result.outlet_mass_kg, "kg"),
        "mass_residual_kg": (result.mass_residual_kg, "kg"),
    }
    fields = []
    arrays = []
    for name, (values, unit) in columns.items():
        numeric = real_array(values, name)
        if numeric.ndim != 1 or numeric.shape != result.time_s.shape:
            raise ValueError(f"{name} must be a vector matching time_s")
        fields.append(
            arrow.field(
                name,
                arrow.float64(),
                nullable=False,
                metadata={b"unit": unit.encode("ascii")},
            )
        )
        arrays.append(arrow.array(numeric, type=arrow.float64(), from_pandas=False))

    metadata = {
        b"pyfast.export_schema_version": b"1",
        b"pyfast.export_scope": b"outlet_timeseries_and_global_mass_balance",
        b"pyfast.reactor": result.reactor.encode("ascii"),
        b"pyfast.experimental_validation": b"not_performed",
        b"pyfast.config_json": result.config_json.encode("utf-8"),
        b"pyfast.solver_options_json": result.options_json.encode("utf-8"),
        b"pyfast.numerical_sha256": result.numerical_sha256.encode("ascii"),
        b"pyfast.manifest_json": result.manifest.to_json().encode("utf-8"),
        b"pyfast.diagnostics_json": json.dumps(
            asdict(result.diagnostics), sort_keys=True, allow_nan=False
        ).encode("utf-8"),
    }
    schema = arrow.schema(fields, metadata=metadata)
    table = arrow.Table.from_arrays(arrays, schema=schema)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        parquet.write_table(table, stream, compression="snappy", version="2.6", store_schema=True)
    return target

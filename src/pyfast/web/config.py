"""Strict browser input boundary and deliberately bounded local-GUI defaults."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

from ..schemas import (
    HSDM,
    LDF,
    BatchConfig,
    Bed,
    Freundlich,
    Langmuir,
    Linear,
    Operation,
    SimulationConfig,
    Species,
)
from ..solvers import SolverOptions

MAX_REQUEST_BYTES = 65536
MAX_SAMPLES = 401
MAX_AXIAL_CELLS = 64
MAX_RADIAL_CELLS = 12
MAX_DURATION_S = 172800.0
MAX_JOBS = 50
SCIENTIFIC_STATUS = (
    "Prototipo científico con verificaciones numéricas seleccionadas; "
    "sin validación experimental ni certificación de diseño."
)


def strict_object(payload: str) -> dict[str, Any]:
    """Reject duplicate keys, non-objects and nonstandard NaN/Infinity literals."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key, value in pairs:
            if key in values:
                raise ValueError(f"Duplicate JSON key: {key}")
            values[key] = value
        return values

    def invalid_constant(value: str) -> None:
        raise ValueError(f"Nonfinite JSON literal: {value}")

    result = json.loads(payload, object_pairs_hook=unique, parse_constant=invalid_constant)
    if not isinstance(result, dict):
        raise ValueError("A JSON object is required")
    return result


def _range(value: float, name: str, low: float, high: float) -> None:
    if not low <= value <= high:
        raise ValueError(f"Local GUI limit: {name} must lie within [{low}, {high}] in SI")


@dataclass(frozen=True, slots=True)
class RequestSpec:
    reactor: Literal["batch", "column"]
    config_json: str
    config_sha256: str
    duration_s: float
    options: SolverOptions
    samples: int

    def input_json(self) -> str:
        return json.dumps(
            {
                "reactor": self.reactor,
                "config": json.loads(self.config_json),
                "solver_options": asdict(self.options),
                "samples": self.samples,
                "config_sha256": self.config_sha256,
            },
            sort_keys=True,
            allow_nan=False,
        )


def parse_request(data: dict[str, Any]) -> RequestSpec:
    """Use the package's existing strict schemas; GUI caps are not physical validation."""
    allowed = {"reactor", "config_json", "options", "samples"}
    if set(data) - allowed or not {"reactor", "config_json"} <= set(data):
        raise ValueError("Allowed request fields: reactor, config_json, options, samples")
    reactor, payload = data["reactor"], data["config_json"]
    if reactor not in ("batch", "column") or not isinstance(payload, str):
        raise ValueError("reactor must be batch/column and config_json must be JSON text")
    if len(payload.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise ValueError("Configuration exceeds local GUI size limit")
    # Validate the embedded JSON independently so its duplicate/nonfinite literals survive.
    strict_object(payload)
    config: BatchConfig | SimulationConfig
    if reactor == "batch":
        config = BatchConfig.from_json(payload)
        duration = config.duration_s
        c0, q0 = config.initial_concentration_kg_m3, config.initial_loading_kg_kg
        temperature = config.temperature_k
        _range(config.liquid_volume_m3, "liquid_volume_m3", 1e-9, 10)
        _range(config.adsorbent_mass_kg, "adsorbent_mass_kg", 1e-9, 1e5)
        _range(config.adsorbent_mass_kg / config.liquid_volume_m3, "mass/volume", 1e-9, 1e6)
        material = config.material
    else:
        config = SimulationConfig.from_json(payload)
        op, bed = config.operation, config.bed
        duration, temperature = op.duration_s, op.temperature_k
        c0, q0 = op.initial_concentration_kg_m3, op.initial_loading_kg_kg
        _range(op.inlet_concentration_kg_m3, "inlet_concentration_kg_m3", 0, 1000)
        _range(op.flow_m3_s, "flow_m3_s", 1e-12, 1e-2)
        _range(op.axial_dispersion_m2_s, "axial_dispersion_m2_s", 0, 1)
        _range(bed.length_m, "length_m", 1e-4, 10)
        _range(bed.diameter_m, "diameter_m", 1e-3, 2)
        _range(bed.particle_diameter_m, "particle_diameter_m", 1e-5, 0.1)
        _range(bed.porosity, "porosity", 0.05, 0.95)
        _range(bed.particle_density_kg_m3, "particle_density_kg_m3", 1, 1e4)
        material = bed.material
    if len(config.species.name) > 200 or len(material) > 200:
        raise ValueError("Species/material labels may contain at most 200 characters")
    _range(duration, "duration_s", 1e-6, MAX_DURATION_S)
    _range(temperature, "temperature_k", 250, 400)
    _range(c0, "initial_concentration_kg_m3", 0, 1000)
    _range(q0, "initial_loading_kg_kg", 0, 10)
    equilibrium = config.equilibrium
    if isinstance(equilibrium, Langmuir):
        _range(equilibrium.qmax_kg_kg, "qmax_kg_kg", 1e-12, 10)
        _range(equilibrium.affinity_m3_kg, "affinity_m3_kg", 1e-12, 1e9)
    elif isinstance(equilibrium, Freundlich):
        _range(equilibrium.q_ref_kg_kg, "q_ref_kg_kg", 1e-12, 10)
        _range(equilibrium.c_ref_kg_m3, "c_ref_kg_m3", 1e-12, 1000)
        _range(equilibrium.exponent, "exponent", 0.2, 3)
    elif isinstance(equilibrium, Linear):
        _range(equilibrium.distribution_m3_kg, "distribution_m3_kg", 0, 1e6)
    kinetics = config.kinetics
    if isinstance(kinetics, LDF):
        _range(kinetics.rate_s_inv, "rate_s_inv", 1e-8, 10)
    else:
        _range(kinetics.surface_diffusivity_m2_s, "surface_diffusivity_m2_s", 1e-16, 1e-8)
        _range(kinetics.film_coefficient_m_s, "film_coefficient_m_s", 1e-9, 1e-3)
    options_data = data.get("options", {})
    if not isinstance(options_data, dict) or set(options_data) - {
        "method",
        "axial_cells",
        "radial_cells",
        "rtol",
    }:
        raise ValueError("GUI options allow only method, axial_cells, radial_cells, rtol")
    defaults: dict[str, Any] = {"axial_cells": 40, "radial_cells": 8, "rtol": 1e-6}
    options = SolverOptions(**(defaults | options_data))
    if options.axial_cells > MAX_AXIAL_CELLS or options.radial_cells > MAX_RADIAL_CELLS:
        raise ValueError("Local GUI grid limit: axial<=64 and radial<=12")
    _range(options.rtol, "rtol", 1e-9, 1e-3)
    samples = data.get("samples", 201)
    if type(samples) is not int or not 2 <= samples <= MAX_SAMPLES:
        raise ValueError("samples must be an integer within [2,401]")
    return RequestSpec(reactor, config.to_json(), config.sha256, duration, options, samples)


def examples() -> list[dict[str, str]]:
    """Self-contained synthetic examples; no filesystem paths or experimental claims."""
    batch = BatchConfig(
        species=Species(name="Soluto sintético"),
        material="Adsorbente sintético",
        liquid_volume_m3=0.001,
        adsorbent_mass_kg=0.002,
        duration_s=300,
        initial_concentration_kg_m3=0.01,
        initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=0.5),
        kinetics=LDF(rate_s_inv=0.02),
    )
    column = SimulationConfig(
        species=Species(name="Soluto sintético"),
        bed=Bed(
            length_m=0.1,
            diameter_m=0.01,
            particle_diameter_m=0.0002,
            porosity=0.4,
            particle_density_kg_m3=1000,
            material="Adsorbente sintético",
        ),
        operation=Operation(flow_m3_s=1e-7, inlet_concentration_kg_m3=0.01, duration_s=1000),
        equilibrium=Langmuir(qmax_kg_kg=0.001, affinity_m3_kg=10),
        kinetics=LDF(rate_s_inv=0.02),
    )
    hsdm = SimulationConfig(
        species=column.species,
        bed=column.bed,
        operation=column.operation,
        equilibrium=column.equilibrium,
        kinetics=HSDM(surface_diffusivity_m2_s=1e-11, film_coefficient_m_s=1e-5),
    )
    return [
        {
            "id": "batch_linear",
            "label": "Batch LDF · referencia lineal",
            "reactor": "batch",
            "config_json": batch.to_json(),
        },
        {
            "id": "column_ldf",
            "label": "Columna LDF · Langmuir",
            "reactor": "column",
            "config_json": column.to_json(),
        },
        {
            "id": "column_hsdm",
            "label": "Columna HSDM · película externa",
            "reactor": "column",
            "config_json": hsdm.to_json(),
        },
    ]

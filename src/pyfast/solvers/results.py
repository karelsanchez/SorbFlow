"""Numerical results with explicit mass diagnostics and reproducibility metadata."""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from typing import Literal
from uuid import uuid4

import numpy as np

from .._arrays import FloatArray
from .._version import VERSION
from ..schemas import RunManifest
from .integration import IntegrationOutput, SimulationError
from .options import SolverOptions


@dataclass(frozen=True, slots=True, kw_only=True)
class SolverDiagnostics:
    """Mass and nonnegativity checks include internal accepted states."""

    nfev: int
    njev: int
    nlu: int
    accepted_steps: int
    max_abs_mass_residual_kg: float
    max_scaled_mass_residual: float
    min_concentration_kg_m3: float
    min_loading_kg_kg: float


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationResult:
    """Arrays use (time, axial cell); a batch has a single cell and no z coordinate.

    Read-only array snapshots prevent accidental in-place modification. Successful
    numerical checks do not imply independent experimental validation.
    """

    reactor: Literal["batch", "column"]
    time_s: FloatArray
    concentration_kg_m3: FloatArray
    loading_kg_kg: FloatArray
    inventory_kg: FloatArray
    inlet_mass_kg: FloatArray
    outlet_mass_kg: FloatArray
    mass_residual_kg: FloatArray
    z_m: FloatArray | None
    config_json: str
    options_json: str
    numerical_sha256: str
    manifest: RunManifest
    diagnostics: SolverDiagnostics
    radial_loading_kg_kg: FloatArray | None = None
    r_m: FloatArray | None = None

    def __post_init__(self) -> None:
        for name in (
            "time_s",
            "concentration_kg_m3",
            "loading_kg_kg",
            "inventory_kg",
            "inlet_mass_kg",
            "outlet_mass_kg",
            "mass_residual_kg",
            "z_m",
            "radial_loading_kg_kg",
            "r_m",
        ):
            value = getattr(self, name)
            if value is not None:
                copied = np.array(value, dtype=np.float64, copy=True)
                copied.setflags(write=False)
                object.__setattr__(self, name, copied)

    @property
    def outlet_concentration_kg_m3(self) -> FloatArray:
        """Last finite-volume cell, or the perfectly mixed liquid for a batch."""
        return self.concentration_kg_m3[:, -1]

    def to_json(self) -> str:
        """Serialize full fields plus units, inputs and numerical evidence."""
        data = {
            "result_schema_version": 1,
            "reactor": self.reactor,
            "experimental_validation": "not_performed",
            "units": {
                "time_s": "s",
                "z_m": "m",
                "concentration_kg_m3": "kg/m^3",
                "loading_kg_kg": "kg/kg_dry_adsorbent",
                "inventory_kg": "kg",
                "inlet_mass_kg": "kg",
                "outlet_mass_kg": "kg",
                "mass_residual_kg": "kg",
                "r_m": "m",
                "radial_loading_kg_kg": "kg/kg_dry_adsorbent",
            },
            "config": json.loads(self.config_json),
            "solver_options": json.loads(self.options_json),
            "numerical_sha256": self.numerical_sha256,
            "manifest": json.loads(self.manifest.to_json()),
            "diagnostics": asdict(self.diagnostics),
        }
        for name in (
            "time_s",
            "z_m",
            "concentration_kg_m3",
            "loading_kg_kg",
            "inventory_kg",
            "inlet_mass_kg",
            "outlet_mass_kg",
            "mass_residual_kg",
            "radial_loading_kg_kg",
            "r_m",
        ):
            value = getattr(self, name)
            data[name] = None if value is None else value.tolist()
        return json.dumps(data, sort_keys=True, allow_nan=False, separators=(",", ":"))


def check_physics(
    concentration: FloatArray,
    loading: FloatArray,
    inventory: FloatArray,
    inlet: FloatArray,
    outlet: FloatArray,
    initial_mass: float,
    options: SolverOptions,
    integrated: IntegrationOutput,
) -> SolverDiagnostics:
    """Check accepted+requested states; never clip away negative states or lost mass."""
    residual = inventory - initial_mass - inlet + outlet
    scale = np.maximum(np.maximum(initial_mass, inlet), options.mass_reference_kg)
    min_c, min_q = float(np.min(concentration)), float(np.min(loading))
    if min_c < -10 * options.atol_concentration_kg_m3:
        raise SimulationError(f"Negative liquid concentration: {min_c} kg/m^3")
    if min_q < -10 * options.atol_loading_kg_kg:
        raise SimulationError(f"Negative solid loading: {min_q} kg/kg")
    if (
        not np.all(np.isfinite(inventory))
        or np.any(np.abs(residual) > options.atol_mass_kg + options.mass_rtol * scale)
        or np.any(np.abs(residual) / scale > options.mass_rtol)
    ):
        raise SimulationError(
            "Global mass-conservation check failed: "
            f"max absolute residual={np.max(np.abs(residual)):.6g} kg; "
            f"max scaled residual={np.max(np.abs(residual) / scale):.6g}; "
            f"requested mass_rtol={options.mass_rtol:.6g}"
        )
    return SolverDiagnostics(
        nfev=integrated.nfev,
        njev=integrated.njev,
        nlu=integrated.nlu,
        accepted_steps=integrated.accepted_steps,
        max_abs_mass_residual_kg=float(np.max(np.abs(residual))),
        max_scaled_mass_residual=float(np.max(np.abs(residual) / scale)),
        min_concentration_kg_m3=min_c,
        min_loading_kg_kg=min_q,
    )


def result_metadata(
    config_json: str,
    times: FloatArray,
    options: SolverOptions,
    reactor: str,
    code_revision: str,
) -> tuple[str, str, RunManifest]:
    """Fingerprint physical problem, observation times and numerical method separately."""
    options_json = json.dumps(asdict(options), sort_keys=True, allow_nan=False)
    canonical = json.dumps(
        {
            "config": json.loads(config_json),
            "solver": asdict(options),
            "time_s": times.tolist(),
            "reactor": reactor,
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    manifest = RunManifest(
        run_id=str(uuid4()),
        created_utc=datetime.now(UTC).isoformat(),
        config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),
        code_revision=code_revision,
        python_version=platform.python_version(),
        seed=0,
        package_versions=tuple(f"{p}=={version(p)}" for p in ("numpy", "scipy", "pint"))
        + (f"pyfast-adsorption=={VERSION}",),
    )
    return options_json, fingerprint, manifest

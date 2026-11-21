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

    Read-only array snapshots prevent accidental in-place modification. Mass balance
    and state diagnostics accompany every result.
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
            "result_schema_version": 2,
            "reactor": self.reactor,
            "result_kind": "numerical_simulation",
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



class PhysicsViolation(SimulationError):
    """Physical-state failure with a location, retaining the dense-path message."""

    def __init__(self, message: str, location: dict[str, object] | None) -> None:
        super().__init__(message)
        self.location = location


class StreamingPhysics:
    """Bounded-memory checks over all accepted states followed by requested samples."""

    def __init__(self, *, cells: int, area: float, dz: float, epsilon: float,
                 rho_b: float, initial_mass: float, options: SolverOptions,
                 n_states: int, block: int = 64) -> None:
        if type(block) is not int or block < 1 or cells < 2 or n_states != 2*cells+2:
            raise ValueError("Invalid streaming buffer dimensions")
        self.cells, self.area, self.dz = cells, area, dz
        self.epsilon, self.rho_b, self.initial_mass = epsilon, rho_b, initial_mass
        self.options = options
        self.buffer = np.empty((n_states, block), order="F")
        self.meta: list[tuple[str, int, float]] = []
        self.min_c, self.min_q = np.inf, np.inf
        self.max_abs_res, self.max_scaled_res = 0., 0.
        self.locations: dict[str, dict[str, object]] = {}
        self.nonfinite: dict[str, object] | None = None
        self.mass_violation: dict[str, object] | None = None
        self.inventory_nonfinite = False
        self.columns = 0

    def inventory(self, states: FloatArray) -> FloatArray:
        block = np.asfortranarray(states)
        return np.asarray(self.area*self.dz*(self.epsilon*np.sum(block[:self.cells], axis=0)
            + self.rho_b*np.sum(block[self.cells:2*self.cells], axis=0)))

    def push_state(self, y: FloatArray, kind: str, index: int, t: float) -> None:
        if y.shape != (self.buffer.shape[0],):
            raise ValueError("Streaming state dimension mismatch")
        self.buffer[:, len(self.meta)] = y
        self.meta.append((kind, index, t))
        if len(self.meta) == self.buffer.shape[1]:
            self._flush()

    def _flush(self) -> None:
        if self.meta:
            self._process(self.buffer[:, :len(self.meta)], self.meta)
            self.meta = []

    def push_block(self, samples: FloatArray, metas: list[tuple[str, int, float]]) -> None:
        if (samples.ndim != 2 or samples.shape[0] != self.buffer.shape[0]
                or samples.shape[1] != len(metas)):
            raise ValueError("Streaming sample dimensions mismatch")
        self._flush()
        if metas:
            self._process(np.asfortranarray(samples), metas)

    def _process(self, states: FloatArray, metas: list[tuple[str, int, float]]) -> None:
        count = states.shape[1]
        self.columns += count

        def location(j: int) -> dict[str, object]:
            kind, index, time = metas[j]
            return {"kind": kind, "index": index, "time_s": time}

        finite = np.isfinite(states)
        if not np.all(finite):
            if self.nonfinite is None:
                j = int(np.flatnonzero(~finite.all(axis=0))[0])
                self.nonfinite = location(j)
            return
        c, q = states[:self.cells], states[self.cells:2*self.cells]
        for name, values, attr in (("concentration", c, "min_c"), ("loading", q, "min_q")):
            row, j = divmod(int(np.argmin(values)), count)
            value = float(values[row, j])
            if value < getattr(self, attr):
                setattr(self, attr, value)
                self.locations[name] = {**location(j), "cell": row, "value": value}
        inventory = self.inventory(states)
        inlet, outlet = states[-2], states[-1]
        residual = inventory-self.initial_mass-inlet+outlet
        scale = np.maximum(np.maximum(self.initial_mass, inlet), self.options.mass_reference_kg)
        abs_res = np.abs(residual)
        scaled = abs_res/scale
        self.inventory_nonfinite |= not bool(np.all(np.isfinite(inventory)))
        for values, attr, name in ((abs_res, "max_abs_res", "mass_absolute"),
                                   (scaled, "max_scaled_res", "mass_scaled")):
            j = int(np.argmax(values))
            if values[j] > getattr(self, attr):
                setattr(self, attr, float(values[j]))
                self.locations[name] = location(j)
        violation = ((abs_res > self.options.atol_mass_kg+self.options.mass_rtol*scale)
                     | (scaled > self.options.mass_rtol))
        if self.mass_violation is None and np.any(violation):
            self.mass_violation = location(int(np.flatnonzero(violation)[0]))

    def finalize(self, nfev: int, njev: int, nlu: int, steps: int) -> SolverDiagnostics:
        self._flush()
        if not self.columns:
            raise ValueError("No states were checked")
        o = self.options
        if self.nonfinite is not None:
            raise PhysicsViolation("Nonfinite integration state", self.nonfinite)
        if self.min_c < -10*o.atol_concentration_kg_m3:
            raise PhysicsViolation(f"Negative liquid concentration: {self.min_c} kg/m^3",
                                   self.locations.get("concentration"))
        if self.min_q < -10*o.atol_loading_kg_kg:
            raise PhysicsViolation(f"Negative solid loading: {self.min_q} kg/kg",
                                   self.locations.get("loading"))
        if self.inventory_nonfinite or self.mass_violation is not None:
            raise PhysicsViolation("Global mass-conservation check failed: "
                f"max absolute residual={self.max_abs_res:.6g} kg; "
                f"max scaled residual={self.max_scaled_res:.6g}; "
                f"requested mass_rtol={o.mass_rtol:.6g}", self.mass_violation)
        return SolverDiagnostics(nfev=nfev, njev=njev, nlu=nlu, accepted_steps=steps,
            max_abs_mass_residual_kg=self.max_abs_res,
            max_scaled_mass_residual=self.max_scaled_res,
            min_concentration_kg_m3=float(self.min_c), min_loading_kg_kg=float(self.min_q))


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
        + (f"sorbflow=={VERSION}",),
    )
    return options_json, fingerprint, manifest

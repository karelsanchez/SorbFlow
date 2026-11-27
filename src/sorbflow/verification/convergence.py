"""Mesh sequences and goal-oriented adaptive refinement of decision quantities.

The functions here only call the public simulation facade
(:func:`sorbflow.simulate.column`) with copies of :class:`SolverOptions` whose
``axial_cells`` (and, for HSDM, ``radial_cells``) follow a geometric sequence
``N0, r N0, r^2 N0, ...``. The representative cell size is ``h = L / N_axial``;
for HSDM both directions are refined by the same ratio, so the observed order is
that of the combined spatial error.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import version as _package_version
from typing import Literal
from uuid import uuid4

import numpy as np
from numpy.typing import ArrayLike

from .._arrays import FloatArray
from .._version import VERSION
from ..schemas import HSDM, RunManifest, SimulationConfig
from ..solvers import SimulationError, SolverOptions
from .quantities import DecisionQuantity, QuantityValue, default_quantities
from .richardson import RichardsonEstimate, richardson_estimate

__all__ = [
    "ConvergenceReport",
    "GridRun",
    "QuantityStatus",
    "QuantityReport",
    "Refine",
    "converge",
    "estimate_quantities",
    "mesh_sequence",
]

QuantityStatus = Literal["CONVERGED", "NOT_CONVERGED", "CENSORED"]
Refine = Literal["auto", "axial", "radial", "both"]

REPORT_SCHEMA = "sorbflow.verification.convergence/1"


def _canonical(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class GridRun:
    """One solve of the sequence.

    Attributes
    ----------
    axial_cells, radial_cells : int
        Grid of this solve (``radial_cells`` is ``None`` for LDF columns).
    h_m : float
        Representative axial cell size ``L / axial_cells`` (m).
    numerical_sha256 : str
        Fingerprint of the solve (problem, sample times, solver options).
    cpu_s : float
        Process CPU time of the solve (s); excluded from the report fingerprint.
    values : tuple of QuantityValue
        Decision quantities on this grid.
    """

    axial_cells: int
    radial_cells: int | None
    h_m: float
    numerical_sha256: str
    cpu_s: float
    values: tuple[QuantityValue, ...]

    def value(self, key: str) -> QuantityValue:
        """Quantity with ``key`` on this grid."""
        for item in self.values:
            if item.key == key:
                return item
        raise KeyError(key)

    def to_dict(self, *, include_timing: bool = True) -> dict[str, object]:
        """JSON-compatible mapping."""
        data: dict[str, object] = {
            "axial_cells": self.axial_cells, "radial_cells": self.radial_cells,
            "h_m": self.h_m, "numerical_sha256": self.numerical_sha256,
            "values": [v.to_dict() for v in self.values]}
        if include_timing:
            data["cpu_s"] = self.cpu_s
        return data


@dataclass(frozen=True, slots=True, kw_only=True)
class QuantityReport:
    """Error control outcome for one decision quantity.

    Attributes
    ----------
    key, units : str
        Quantity identifier and units.
    status : {"CONVERGED", "NOT_CONVERGED", "CENSORED"}
        ``CONVERGED``: ``error_bound <= tolerance``. ``CENSORED``: not observed
        within the horizon on the finest grid (``censoring``/``censored_bound``).
    value : float or None
        Finest-grid value.
    extrapolated : float or None
        Richardson-extrapolated value.
    error_bound : float or None
        Bound on ``|exact - value|`` (GCI or conservative fallback).
    tolerance : float
        ``max(abs_tol, rel_tol * |value|)`` in the quantity units.
    estimate : RichardsonEstimate or None
        Full estimate on the uncensored finest grids.
    censoring : {"none", "right", "left"}
        Censoring on the finest grid.
    censored_bound : float or None
        Censoring bound on the finest grid.
    flags : tuple of str
        Estimate flags plus ``coarse_grids_censored`` / ``mixed_censoring``.
    """

    key: str
    units: str
    status: QuantityStatus
    value: float | None
    extrapolated: float | None
    error_bound: float | None
    tolerance: float
    estimate: RichardsonEstimate | None
    censoring: Literal["none", "right", "left"]
    censored_bound: float | None
    finest_axial_cells: int
    flags: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """JSON-compatible mapping."""
        return {"key": self.key, "units": self.units, "status": self.status,
                "value": self.value, "extrapolated": self.extrapolated,
                "error_bound": self.error_bound, "tolerance": self.tolerance,
                "estimate": None if self.estimate is None else self.estimate.to_dict(),
                "censoring": self.censoring, "censored_bound": self.censored_bound,
                "finest_axial_cells": self.finest_axial_cells, "flags": list(self.flags)}


@dataclass(frozen=True, slots=True, kw_only=True)
class ConvergenceReport:
    """Frozen, JSON-serialisable record of a mesh study or adaptive refinement.

    ``fingerprint`` is the SHA-256 of the canonical JSON of everything that is
    reproducible (configuration hash, base options, sample-time hash, quantity
    definitions, tolerances, grids with their numerical fingerprints and values,
    estimates, stop reason). CPU times and the run manifest (identifier,
    timestamp) are excluded, mirroring ``SimulationResult.numerical_sha256``.
    """

    config_sha256: str
    options_json: str
    time_sha256: str
    quantity_definitions: tuple[str, ...]
    rel_tol: float
    abs_tol: tuple[tuple[str, float], ...]
    refinement_ratio: int
    refine: Literal["axial", "radial", "both"]
    formal_order: float
    grids: tuple[GridRun, ...]
    quantities: tuple[QuantityReport, ...]
    solves_used: int
    budget_solves: int
    max_cells: int
    stop_reason: str
    predicted_solves: tuple[tuple[int, int | None], ...]
    cpu_s_total: float
    sorbflow_version: str
    manifest: RunManifest

    def quantity(self, key: str) -> QuantityReport:
        """Report entry with ``key``."""
        for item in self.quantities:
            if item.key == key:
                return item
        raise KeyError(key)

    @property
    def all_resolved(self) -> bool:
        """True when every quantity is CONVERGED or CENSORED."""
        return all(q.status != "NOT_CONVERGED" for q in self.quantities)

    def _reproducible(self) -> dict[str, object]:
        return {
            "schema": REPORT_SCHEMA,
            "config_sha256": self.config_sha256,
            "solver_options": json.loads(self.options_json),
            "time_sha256": self.time_sha256,
            "quantity_definitions": [json.loads(d) for d in self.quantity_definitions],
            "rel_tol": self.rel_tol, "abs_tol": dict(self.abs_tol),
            "refinement_ratio": self.refinement_ratio, "refine": self.refine,
            "formal_order": self.formal_order,
            "grids": [g.to_dict(include_timing=False) for g in self.grids],
            "quantities": [q.to_dict() for q in self.quantities],
            "solves_used": self.solves_used, "budget_solves": self.budget_solves,
            "max_cells": self.max_cells, "stop_reason": self.stop_reason,
            "predicted_solves": [list(p) for p in self.predicted_solves],
            "sorbflow_version": self.sorbflow_version,
        }

    @property
    def fingerprint(self) -> str:
        """SHA-256 of the reproducible content (lowercase hex)."""
        return hashlib.sha256(_canonical(self._reproducible()).encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        """Canonical JSON with timings, manifest and fingerprint (no NaN/Infinity)."""
        data = self._reproducible()
        data["grids"] = [g.to_dict() for g in self.grids]
        data["cpu_s_total"] = self.cpu_s_total
        data["manifest"] = json.loads(self.manifest.to_json())
        data["fingerprint"] = self.fingerprint
        return _canonical(data)


def _resolve_refine(config: SimulationConfig, refine: Refine) -> Literal["axial", "radial", "both"]:
    hsdm = isinstance(config.kinetics, HSDM)
    if refine == "auto":
        return "both" if hsdm else "axial"
    if refine not in ("axial", "radial", "both"):
        raise ValueError("refine must be auto, axial, radial or both")
    if refine != "axial" and not hsdm:
        raise ValueError("Radial refinement applies to HSDM columns only")
    return refine


def _formal_order(options: SolverOptions, formal_order: float | None) -> float:
    if formal_order is not None:
        value = float(formal_order)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("formal_order must be positive")
        return value
    # Upwind axial advection is first order; the limited TVD scheme is second order
    # away from extrema. The radial shell FV of HSDM is second order (not limiting).
    return 2.0 if getattr(options, "axial_scheme", "upwind1") == "tvd" else 1.0


def _grid_options(base: SolverOptions, level: int, ratio: int,
                  refine: Literal["axial", "radial", "both"]) -> SolverOptions:
    factor = ratio**level
    axial = base.axial_cells * (factor if refine in ("axial", "both") else 1)
    radial = base.radial_cells * (factor if refine in ("radial", "both") else 1)
    return replace(base, axial_cells=axial, radial_cells=radial)


def _h(config: SimulationConfig, options: SolverOptions,
       refine: Literal["axial", "radial", "both"]) -> float:
    if refine == "radial":
        return config.bed.particle_diameter_m / 2 / options.radial_cells
    return config.bed.length_m / options.axial_cells


def _solve(config: SimulationConfig, options: SolverOptions, times: FloatArray,
           quantities: Sequence[DecisionQuantity],
           refine: Literal["axial", "radial", "both"], code_revision: str) -> GridRun:
    from ..simulate import column

    start = time.process_time()
    result = column(config, time_s=times, options=options, code_revision=code_revision)
    values = tuple(q.extract(result) for q in quantities)
    return GridRun(
        axial_cells=options.axial_cells,
        radial_cells=options.radial_cells if isinstance(config.kinetics, HSDM) else None,
        h_m=_h(config, options, refine), numerical_sha256=result.numerical_sha256,
        cpu_s=time.process_time() - start, values=values)


def _times(config: SimulationConfig, time_s: ArrayLike | None) -> FloatArray:
    if time_s is None:
        return np.linspace(0.0, config.operation.duration_s, 2001)
    return np.asarray(time_s, dtype=np.float64)


def _check_quantities(config: SimulationConfig,
                      quantities: Sequence[DecisionQuantity] | None
                      ) -> tuple[DecisionQuantity, ...]:
    chosen = default_quantities() if quantities is None else tuple(quantities)
    if not chosen:
        raise ValueError("At least one decision quantity is required")
    keys = [q.key for q in chosen]
    if len(set(keys)) != len(keys):
        raise ValueError("Decision quantity keys must be unique")
    for q in chosen:
        q.validate(config)
    return chosen


def _tolerance(key: str, value: float | None, rel_tol: float,
               abs_tol: Mapping[str, float]) -> float:
    scale = 0.0 if value is None else abs(value)
    return max(abs_tol.get(key, 0.0), rel_tol * scale)


def _quantity_report(key: str, units: str, grids: Sequence[GridRun], *, formal_order: float,
                     p_band: tuple[float, float] | None, rel_tol: float,
                     abs_tol: Mapping[str, float]) -> QuantityReport:
    ordered = sorted(grids, key=lambda g: g.h_m)
    series = [g.value(key) for g in ordered]
    finest = series[0]
    flags: list[str] = []
    if finest.censored:
        if any(not s.censored for s in series):
            flags.append("mixed_censoring")
        return QuantityReport(
            key=key, units=units, status="CENSORED", value=None, extrapolated=None,
            error_bound=None, tolerance=_tolerance(key, None, rel_tol, abs_tol), estimate=None,
            censoring=finest.censoring, censored_bound=finest.bound,
            finest_axial_cells=ordered[0].axial_cells, flags=tuple(flags))
    usable: list[tuple[float, float]] = []
    for grid, item in zip(ordered, series, strict=True):
        if item.censored:
            flags.append("coarse_grids_censored")
            break
        assert item.value is not None
        usable.append((grid.h_m, item.value))
    estimate = richardson_estimate([v for _, v in usable], [h for h, _ in usable],
                                   formal_order=formal_order, p_band=p_band)
    tol = _tolerance(key, finest.value, rel_tol, abs_tol)
    converged = estimate.error_bound is not None and estimate.error_bound <= tol
    return QuantityReport(
        key=key, units=units, status="CONVERGED" if converged else "NOT_CONVERGED",
        value=finest.value, extrapolated=estimate.extrapolated,
        error_bound=estimate.error_bound, tolerance=tol, estimate=estimate,
        censoring="none", censored_bound=None, finest_axial_cells=ordered[0].axial_cells,
        flags=tuple(flags) + estimate.flags)


def estimate_quantities(grids: Sequence[GridRun], quantities: Sequence[DecisionQuantity], *,
                        formal_order: float = 1.0, p_band: tuple[float, float] | None = None,
                        rel_tol: float = 1e-2, abs_tol: Mapping[str, float] | None = None
                        ) -> tuple[QuantityReport, ...]:
    """Error estimates of every quantity from already computed grids (pure).

    Parameters
    ----------
    grids : sequence of GridRun
        Solves of one geometric sequence (any order).
    quantities : sequence of DecisionQuantity
        Quantities present in every grid.
    formal_order : float
        Formal order of the discretization.
    p_band : (float, float), optional
        Plausible band of observed orders (see ``richardson_estimate``).
    rel_tol : float
        Relative tolerance on each quantity.
    abs_tol : mapping of key to float, optional
        Absolute tolerances in each quantity's units.

    Returns
    -------
    tuple of QuantityReport
    """
    if not grids:
        raise ValueError("At least one grid is required")
    absolute = dict(abs_tol or {})
    return tuple(_quantity_report(q.key, q.units, grids, formal_order=formal_order,
                                  p_band=p_band, rel_tol=rel_tol, abs_tol=absolute)
                 for q in quantities)


def mesh_sequence(config: SimulationConfig, quantities: Sequence[DecisionQuantity] | None = None,
                  *, levels: int = 3, refinement_ratio: int = 2,
                  options: SolverOptions | None = None, time_s: ArrayLike | None = None,
                  refine: Refine = "auto", code_revision: str = "uncommitted"
                  ) -> tuple[GridRun, ...]:
    """Solve a fixed geometric sequence ``N0 r^k`` (k = 0..levels-1).

    Parameters
    ----------
    config : SimulationConfig
        Fixed-bed problem (LDF or HSDM).
    quantities : sequence of DecisionQuantity, optional
        Defaults to ``t_0.05``, ``t_0.1``, ``t_0.5``.
    levels : int
        Number of grids (>= 1).
    refinement_ratio : int
        Integer ratio ``r >= 2`` between successive grids.
    options : SolverOptions, optional
        Base options; ``axial_cells``/``radial_cells`` define the coarsest grid.
    time_s : array_like, optional
        Common output times (default 2001 uniform samples over the horizon).
    refine : {"auto", "axial", "radial", "both"}
        ``auto`` refines axially for LDF and both directions for HSDM.
    code_revision : str
        Forwarded to every solve.

    Returns
    -------
    tuple of GridRun
        Coarsest first.
    """
    if type(levels) is not int or levels < 1:
        raise ValueError("levels must be a positive integer")
    if type(refinement_ratio) is not int or refinement_ratio < 2:
        raise ValueError("refinement_ratio must be an integer >= 2")
    base = SolverOptions() if options is None else options
    chosen = _check_quantities(config, quantities)
    mode = _resolve_refine(config, refine)
    times = _times(config, time_s)
    return tuple(_solve(config, _grid_options(base, k, refinement_ratio, mode), times, chosen,
                        mode, code_revision) for k in range(levels))


def _predict(reports: Sequence[QuantityReport], ratio: int, solves: int) -> int | None:
    """Solves needed until every unconverged bound falls below its tolerance.

    Assumes ``U ~ h^p_used``: each refinement divides the bound by ``r^p``.
    ``None`` when an unconverged quantity has no usable order or zero tolerance.
    """
    extra = 0
    for report in reports:
        if report.status != "NOT_CONVERGED":
            continue
        estimate = report.estimate
        if (estimate is None or estimate.error_bound is None or report.tolerance <= 0):
            return None
        p = estimate.p_used if estimate.p_used is not None else None
        if p is None or not estimate.asymptotic:
            return None
        needed = math.log(estimate.error_bound / report.tolerance) / (p * math.log(ratio))
        extra = max(extra, max(1, math.ceil(needed - 1e-9)))
    return solves + extra


def converge(config: SimulationConfig, quantities: Sequence[DecisionQuantity] | None = None,
             *, rel_tol: float = 1e-2, abs_tol: float | Mapping[str, float] = 0.0,
             max_cells: int = 3200, budget_solves: int = 6,
             options: SolverOptions | None = None, time_s: ArrayLike | None = None,
             refinement_ratio: int = 2, refine: Refine = "auto",
             formal_order: float | None = None, p_band: tuple[float, float] | None = None,
             min_grids: int = 3, max_radial_cells: int | None = None,
             code_revision: str = "uncommitted") -> ConvergenceReport:
    """Refine geometrically until every decision quantity meets its tolerance.

    Starting from ``options`` (coarsest grid), the grid is refined by
    ``refinement_ratio`` per solve. After ``min_grids`` solves the error of every
    quantity is estimated from the three finest grids; refinement stops when every
    quantity is CONVERGED (``error_bound <= max(abs_tol, rel_tol |value|)``) or
    CENSORED, when ``budget_solves`` would be exceeded, or when the next grid would
    exceed ``max_cells`` axial (or ``max_radial_cells`` radial) cells.

    Parameters
    ----------
    config : SimulationConfig
        Fixed-bed problem (LDF or HSDM).
    quantities : sequence of DecisionQuantity, optional
        Defaults to ``t_0.05``, ``t_0.1``, ``t_0.5`` (s).
    rel_tol : float
        Relative tolerance (dimensionless).
    abs_tol : float or mapping of key to float
        Absolute tolerance in each quantity's own units; a float applies to all.
    max_cells : int
        Largest admissible ``axial_cells``.
    budget_solves : int
        Maximum number of simulations.
    options : SolverOptions, optional
        Base numerical options (time tolerances should be tight, e.g.
        ``rtol=1e-8``, so that time-integration error stays below the target).
    time_s : array_like, optional
        Common output times (default 2001 uniform samples).
    refinement_ratio : int
        Integer ratio between grids (default 2).
    refine : {"auto", "axial", "radial", "both"}
        Refined directions.
    formal_order : float, optional
        Formal order (default 1 for ``upwind1``, 2 for ``tvd``).
    p_band : (float, float), optional
        Plausible observed-order band.
    min_grids : int
        Grids before the first estimate (2 uses the two-grid GCI, Fs = 3).
    max_radial_cells : int, optional
        Largest admissible ``radial_cells`` (HSDM).
    code_revision : str
        Forwarded to every solve.

    Returns
    -------
    ConvergenceReport
    """
    if not math.isfinite(rel_tol) or rel_tol < 0:
        raise ValueError("rel_tol must be finite and nonnegative")
    chosen = _check_quantities(config, quantities)
    if isinstance(abs_tol, Mapping):
        absolute = {str(k): float(v) for k, v in abs_tol.items()}
    else:
        absolute = {q.key: float(abs_tol) for q in chosen}
    if any(not math.isfinite(v) or v < 0 for v in absolute.values()):
        raise ValueError("abs_tol must be finite and nonnegative")
    unknown = set(absolute) - {q.key for q in chosen}
    if unknown:
        raise ValueError(f"abs_tol keys are not requested quantities: {sorted(unknown)}")
    if type(budget_solves) is not int or budget_solves < 1:
        raise ValueError("budget_solves must be a positive integer")
    if type(min_grids) is not int or min_grids not in (2, 3):
        raise ValueError("min_grids must be 2 or 3")
    if type(refinement_ratio) is not int or refinement_ratio < 2:
        raise ValueError("refinement_ratio must be an integer >= 2")
    base = SolverOptions() if options is None else options
    if not isinstance(base, SolverOptions):
        raise ValueError("options must be SolverOptions")
    if type(max_cells) is not int or max_cells < base.axial_cells:
        raise ValueError("max_cells must be an integer >= the base axial_cells")
    mode = _resolve_refine(config, refine)
    order = _formal_order(base, formal_order)
    times = _times(config, time_s)
    grids: list[GridRun] = []
    predictions: list[tuple[int, int | None]] = []
    reports: tuple[QuantityReport, ...] = ()
    stop = "budget_exhausted"
    level = 0
    while True:
        if len(grids) >= budget_solves:
            stop = "budget_exhausted"
            break
        candidate = _grid_options(base, level, refinement_ratio, mode)
        if candidate.axial_cells > max_cells or (
                max_radial_cells is not None and candidate.radial_cells > max_radial_cells):
            stop = "max_cells"
            break
        try:
            grids.append(_solve(config, candidate, times, chosen, mode, code_revision))
        except SimulationError as exc:
            stop = f"solver_failure: {exc}"
            break
        level += 1
        if len(grids) < min_grids:
            continue
        reports = estimate_quantities(grids, chosen, formal_order=order, p_band=p_band,
                                      rel_tol=rel_tol, abs_tol=absolute)
        predictions.append((len(grids), _predict(reports, refinement_ratio, len(grids))))
        if all(r.status != "NOT_CONVERGED" for r in reports):
            stop = "converged"
            break
    if grids and len(grids) < min_grids:
        reports = estimate_quantities(grids, chosen, formal_order=order, p_band=p_band,
                                      rel_tol=rel_tol, abs_tol=absolute)
    if not grids:
        raise ValueError(f"No grid could be solved ({stop})")
    return ConvergenceReport(
        config_sha256=config.sha256,
        options_json=json.dumps(asdict(base), sort_keys=True, allow_nan=False),
        time_sha256=hashlib.sha256(_canonical(times.tolist()).encode()).hexdigest(),
        quantity_definitions=tuple(_canonical(q.describe()) for q in chosen),
        rel_tol=float(rel_tol), abs_tol=tuple(sorted(absolute.items())),
        refinement_ratio=refinement_ratio, refine=mode, formal_order=order,
        grids=tuple(grids), quantities=reports, solves_used=len(grids),
        budget_solves=budget_solves, max_cells=max_cells, stop_reason=stop,
        predicted_solves=tuple(predictions), cpu_s_total=sum(g.cpu_s for g in grids),
        sorbflow_version=VERSION,
        manifest=RunManifest(
            run_id=str(uuid4()), created_utc=datetime.now(UTC).isoformat(),
            config_sha256=config.sha256, code_revision=code_revision,
            python_version=platform.python_version(), seed=0,
            package_versions=tuple(f"{p}=={_package_version(p)}"
                                   for p in ("numpy", "scipy", "pint"))
            + (f"sorbflow=={VERSION}",),
            input_sha256=tuple(sorted({g.numerical_sha256 for g in grids}))))

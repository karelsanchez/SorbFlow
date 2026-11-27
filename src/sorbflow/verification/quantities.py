"""Decision quantities extracted from a fixed-bed :class:`SimulationResult`.

Every extractor is a pure function of the sampled result. Interpolation between
the requested output times is explicit and identical on every grid of a mesh
sequence, so that differences between grids measure the spatial discretization
and not a change of post-processing.

Interpolation contract
----------------------
``"pchip"`` (default)
    The sampled effluent ratio ``C_eff(t)/C_in`` and the cumulative inlet/outlet
    masses are represented by the monotone piecewise-cubic Hermite interpolant
    (Fritsch-Carlson, :class:`scipy.interpolate.PchipInterpolator`). It reproduces
    the samples exactly, never overshoots between them and is third-order
    accurate on smooth monotone data.
``"linear"``
    Piecewise-linear interpolation of the same samples (second-order).

A crossing time ``t_x`` is the *first* time at which the interpolated ratio
reaches ``x``: the first sample index ``k`` with ``ratio[k] >= x`` is located,
and the root of ``interpolant(t) - x`` is bracketed in ``[t[k-1], t[k]]``.

Censoring
---------
A crossing that does not occur within the simulated horizon is *right
censored*: the value is ``None`` and ``bound`` holds the quantity evaluated at
the horizon (``t_x > duration_s``). A ratio that already reaches ``x`` at the
first sample is *left censored* (``bound`` is the value at ``t = 0``).
Censored values are never replaced by NaN or by the horizon itself.

The effluent concentration is the concentration carried by the outlet face:
the last cell average for the first-order upwind scheme (and HSDM columns) and
the limited reconstruction at ``z = L`` for ``axial_scheme="tvd"``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

from .._arrays import FloatArray
from ..schemas import SimulationConfig
from ..solvers.results import SimulationResult

Interpolation = Literal["pchip", "linear"]
Censoring = Literal["none", "right", "left"]

__all__ = [
    "BedVolumesAt",
    "BreakthroughTime",
    "Censoring",
    "DecisionQuantity",
    "EffluentAt",
    "ExceedanceTime",
    "Interpolation",
    "QuantityValue",
    "UsefulCapacity",
    "default_quantities",
    "extract",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class QuantityValue:
    """One decision quantity evaluated on one grid.

    Attributes
    ----------
    key : str
        Stable identifier of the quantity (see ``DecisionQuantity.key``).
    units : str
        Units of ``value`` and ``bound``.
    value : float or None
        The quantity, or ``None`` when censored.
    censoring : {"none", "right", "left"}
        ``"right"``: event not reached within the horizon (true value > bound);
        ``"left"``: event already reached at the first sample (true value <= bound).
    bound : float or None
        Censoring bound in ``units``; ``None`` when not censored.
    """

    key: str
    units: str
    value: float | None
    censoring: Censoring = "none"
    bound: float | None = None

    def __post_init__(self) -> None:
        if self.censoring not in ("none", "right", "left"):
            raise ValueError("censoring must be none, right or left")
        if self.censoring == "none":
            if self.value is None or not math.isfinite(self.value) or self.bound is not None:
                raise ValueError("An uncensored value must be finite and carry no bound")
        elif self.value is not None or self.bound is None or not math.isfinite(self.bound):
            raise ValueError("A censored value must be None with a finite bound")

    @property
    def censored(self) -> bool:
        """True when the event was not observed within the sampled horizon."""
        return self.censoring != "none"

    def to_dict(self) -> dict[str, object]:
        """JSON-compatible mapping (no NaN or Infinity)."""
        return {"key": self.key, "units": self.units, "value": self.value,
                "censoring": self.censoring, "bound": self.bound}


class DecisionQuantity(Protocol):
    """Contract of a decision quantity: a stable key, units and a pure extractor."""

    @property
    def key(self) -> str:
        """Stable identifier, used as mapping key in reports."""
        ...

    @property
    def units(self) -> str:
        """Units of the extracted value."""
        ...

    def validate(self, config: SimulationConfig) -> None:
        """Raise ``ValueError`` when the quantity is undefined for ``config``."""
        ...

    def extract(self, result: SimulationResult) -> QuantityValue:
        """Evaluate the quantity on one simulation result."""
        ...

    def describe(self) -> dict[str, object]:
        """JSON-compatible definition (participates in report fingerprints)."""
        ...


def _effluent_kg_m3(result: SimulationResult) -> FloatArray:
    if result.reactor != "column":
        raise ValueError("Decision quantities require a fixed-bed column result")
    scheme = json.loads(result.options_json).get("axial_scheme", "upwind1")
    if scheme != "upwind1":
        from ..reactors import column as _column

        reconstruct = getattr(_column, "effluent_concentration", None)
        if reconstruct is None:  # pragma: no cover - guarded against API drift
            raise ValueError(f"No effluent reconstruction available for scheme {scheme!r}")
        return np.asarray(reconstruct(result), dtype=np.float64)
    return np.array(result.outlet_concentration_kg_m3, dtype=np.float64)


def _config(result: SimulationResult) -> SimulationConfig:
    return SimulationConfig.from_json(result.config_json)


def _interpolant(t: FloatArray, y: FloatArray, method: Interpolation) -> PchipInterpolator | None:
    if method == "pchip":
        return PchipInterpolator(t, y, extrapolate=False)
    if method == "linear":
        return None
    raise ValueError("interpolation must be 'pchip' or 'linear'")


def _evaluate(t: FloatArray, y: FloatArray, at_s: float, method: Interpolation) -> float:
    spline = _interpolant(t, y, method)
    if spline is None:
        return float(np.interp(at_s, t, y))
    return float(spline(at_s))


def _first_crossing(t: FloatArray, y: FloatArray, level: float,
                    method: Interpolation) -> tuple[float | None, Censoring]:
    """First time at which the interpolant of ``y`` reaches ``level``."""
    above = np.flatnonzero(y >= level)
    if above.size == 0:
        return None, "right"
    k = int(above[0])
    if k == 0:
        return None, "left"
    t0, t1, y0, y1 = float(t[k - 1]), float(t[k]), float(y[k - 1]), float(y[k])
    if method == "linear":
        return t0 + (level - y0) * (t1 - t0) / (y1 - y0), "none"
    # PCHIP is local: four samples around the bracket determine the cubic segment.
    lo, hi = max(k - 2, 0), min(k + 2, t.size)
    spline = PchipInterpolator(t[lo:hi], y[lo:hi], extrapolate=False)
    if float(spline(t1)) - level == 0.0:
        return t1, "none"
    root = brentq(lambda s: float(spline(s)) - level, t0, t1, xtol=1e-12 * max(t1, 1.0),
                  rtol=8.9e-16, maxiter=200)
    return float(root), "none"


def _ratio_crossing(result: SimulationResult, level: float,
                    method: Interpolation) -> tuple[float | None, Censoring]:
    inlet = _config(result).operation.inlet_concentration_kg_m3
    if inlet <= 0:
        raise ValueError("Breakthrough quantities require a positive inlet concentration")
    ratio = _effluent_kg_m3(result) / inlet
    return _first_crossing(np.asarray(result.time_s), ratio, level, method)


def _check_fraction(x: float, name: str) -> float:
    value = float(x)
    if not math.isfinite(value) or not 0 < value < 1:
        raise ValueError(f"{name} must lie strictly between zero and one")
    return value


def _fmt(value: float) -> str:
    return format(value, ".6g")


def _suffix(method: Interpolation) -> str:
    # Keys of the default (PCHIP) definition carry no suffix; others are distinct.
    return "" if method == "pchip" else f"_{method}"


@dataclass(frozen=True, slots=True, kw_only=True)
class BreakthroughTime:
    """Breakthrough time ``t_x`` (s): first time with ``C_eff/C_in >= fraction``."""

    fraction: float = 0.1
    interpolation: Interpolation = "pchip"

    def __post_init__(self) -> None:
        object.__setattr__(self, "fraction", _check_fraction(self.fraction, "fraction"))
        _interpolant(np.array([0.0, 1.0]), np.array([0.0, 1.0]), self.interpolation)

    @property
    def key(self) -> str:
        """For example ``t_0.1_s`` (``t_0.1_s_linear`` with linear interpolation)."""
        return f"t_{_fmt(self.fraction)}_s{_suffix(self.interpolation)}"

    @property
    def units(self) -> str:
        """Seconds."""
        return "s"

    def validate(self, config: SimulationConfig) -> None:
        """Require a positive inlet concentration."""
        if config.operation.inlet_concentration_kg_m3 <= 0:
            raise ValueError("Breakthrough quantities require a positive inlet concentration")

    def extract(self, result: SimulationResult) -> QuantityValue:
        """Return ``t_x``, right censored at ``duration_s`` when not reached."""
        time, censoring = _ratio_crossing(result, self.fraction, self.interpolation)
        if censoring == "none":
            return QuantityValue(key=self.key, units=self.units, value=time)
        bound = float(result.time_s[-1] if censoring == "right" else result.time_s[0])
        return QuantityValue(key=self.key, units=self.units, value=None,
                             censoring=censoring, bound=bound)

    def describe(self) -> dict[str, object]:
        """Definition used in report fingerprints."""
        return {"kind": "breakthrough_time", "fraction": self.fraction,
                "interpolation": self.interpolation, "units": self.units}


@dataclass(frozen=True, slots=True, kw_only=True)
class BedVolumesAt:
    """Bed volumes treated until ``t_x``: ``BV_x = Q t_x / V_bed`` (dimensionless)."""

    fraction: float = 0.1
    interpolation: Interpolation = "pchip"

    def __post_init__(self) -> None:
        object.__setattr__(self, "fraction", _check_fraction(self.fraction, "fraction"))
        _interpolant(np.array([0.0, 1.0]), np.array([0.0, 1.0]), self.interpolation)

    @property
    def key(self) -> str:
        """For example ``bv_0.1``."""
        return f"bv_{_fmt(self.fraction)}{_suffix(self.interpolation)}"

    @property
    def units(self) -> str:
        """Bed volumes (m^3 treated per m^3 of total bed volume)."""
        return "BV"

    def validate(self, config: SimulationConfig) -> None:
        """Require a positive inlet concentration."""
        BreakthroughTime(fraction=self.fraction).validate(config)

    def extract(self, result: SimulationResult) -> QuantityValue:
        """Return ``BV_x``; censoring follows ``t_x``."""
        config = _config(result)
        scale = config.operation.flow_m3_s / config.bed.volume_m3
        time = BreakthroughTime(fraction=self.fraction,
                                interpolation=self.interpolation).extract(result)
        if time.value is not None:
            return QuantityValue(key=self.key, units=self.units, value=scale * time.value)
        assert time.bound is not None
        return QuantityValue(key=self.key, units=self.units, value=None,
                             censoring=time.censoring, bound=scale * time.bound)

    def describe(self) -> dict[str, object]:
        """Definition used in report fingerprints."""
        return {"kind": "bed_volumes", "fraction": self.fraction,
                "interpolation": self.interpolation, "units": self.units}


@dataclass(frozen=True, slots=True, kw_only=True)
class UsefulCapacity:
    """Useful capacity until ``t_x`` (kg solute per kg dry adsorbent).

    ``(M_in(t_x) - M_out(t_x)) / (rho_b V_bed)``: solute removed from the treated
    water (retained by solid and bed liquid, net of the initial bed content) per
    dry adsorbent mass. Cumulative masses are the integrated boundary fluxes of
    the solver, interpolated with the same rule as ``t_x``. When ``t_x`` is right
    censored the capacity at the horizon is a lower bound.
    """

    fraction: float = 0.1
    interpolation: Interpolation = "pchip"

    def __post_init__(self) -> None:
        object.__setattr__(self, "fraction", _check_fraction(self.fraction, "fraction"))
        _interpolant(np.array([0.0, 1.0]), np.array([0.0, 1.0]), self.interpolation)

    @property
    def key(self) -> str:
        """For example ``capacity_0.1_kg_kg``."""
        return f"capacity_{_fmt(self.fraction)}_kg_kg{_suffix(self.interpolation)}"

    @property
    def units(self) -> str:
        """kg solute per kg dry adsorbent."""
        return "kg/kg"

    def validate(self, config: SimulationConfig) -> None:
        """Require a positive inlet concentration."""
        BreakthroughTime(fraction=self.fraction).validate(config)

    def extract(self, result: SimulationResult) -> QuantityValue:
        """Return the capacity at ``t_x`` (or a censoring bound)."""
        config = _config(result)
        adsorbent_kg = config.bed.bulk_density_kg_m3 * config.bed.volume_m3
        t = np.asarray(result.time_s)
        removed = np.asarray(result.inlet_mass_kg) - np.asarray(result.outlet_mass_kg)
        time = BreakthroughTime(fraction=self.fraction,
                                interpolation=self.interpolation).extract(result)
        at = time.value if time.value is not None else time.bound
        assert at is not None
        value = _evaluate(t, removed, at, self.interpolation) / adsorbent_kg
        if time.value is not None:
            return QuantityValue(key=self.key, units=self.units, value=value)
        return QuantityValue(key=self.key, units=self.units, value=None,
                             censoring=time.censoring, bound=value)

    def describe(self) -> dict[str, object]:
        """Definition used in report fingerprints."""
        return {"kind": "useful_capacity", "fraction": self.fraction,
                "interpolation": self.interpolation, "units": self.units}


@dataclass(frozen=True, slots=True, kw_only=True)
class EffluentAt:
    """Effluent concentration ``C_eff(t_service)`` (kg/m^3) at a declared service time."""

    service_time_s: float
    interpolation: Interpolation = "pchip"

    def __post_init__(self) -> None:
        value = float(self.service_time_s)
        if not math.isfinite(value) or value < 0:
            raise ValueError("service_time_s must be finite and nonnegative")
        object.__setattr__(self, "service_time_s", value)
        _interpolant(np.array([0.0, 1.0]), np.array([0.0, 1.0]), self.interpolation)

    @property
    def key(self) -> str:
        """For example ``c_out_at_3600s_kg_m3``."""
        return f"c_out_at_{_fmt(self.service_time_s)}s_kg_m3{_suffix(self.interpolation)}"

    @property
    def units(self) -> str:
        """kg/m^3."""
        return "kg/m^3"

    def validate(self, config: SimulationConfig) -> None:
        """Require the service time inside the simulated horizon."""
        if self.service_time_s > config.operation.duration_s:
            raise ValueError("service_time_s exceeds the simulated duration_s")

    def extract(self, result: SimulationResult) -> QuantityValue:
        """Interpolate the effluent concentration at the service time (never censored)."""
        t = np.asarray(result.time_s)
        if not t[0] <= self.service_time_s <= t[-1]:
            raise ValueError("service_time_s lies outside the sampled horizon")
        value = _evaluate(t, _effluent_kg_m3(result), self.service_time_s, self.interpolation)
        return QuantityValue(key=self.key, units=self.units, value=value)

    def describe(self) -> dict[str, object]:
        """Definition used in report fingerprints."""
        return {"kind": "effluent_at", "service_time_s": self.service_time_s,
                "interpolation": self.interpolation, "units": self.units}


@dataclass(frozen=True, slots=True, kw_only=True)
class ExceedanceTime:
    """First time (s) at which the effluent reaches a declared limit (kg/m^3).

    Right censored at the horizon when the limit is never reached.
    """

    limit_kg_m3: float
    interpolation: Interpolation = "pchip"

    def __post_init__(self) -> None:
        value = float(self.limit_kg_m3)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("limit_kg_m3 must be finite and positive")
        object.__setattr__(self, "limit_kg_m3", value)
        _interpolant(np.array([0.0, 1.0]), np.array([0.0, 1.0]), self.interpolation)

    @property
    def key(self) -> str:
        """For example ``t_exceed_1e-05kg_m3_s``."""
        return f"t_exceed_{_fmt(self.limit_kg_m3)}kg_m3_s{_suffix(self.interpolation)}"

    @property
    def units(self) -> str:
        """Seconds."""
        return "s"

    def validate(self, config: SimulationConfig) -> None:
        """Accept any positive limit (a limit above C_in is censored on every grid)."""

    def extract(self, result: SimulationResult) -> QuantityValue:
        """Return the exceedance time or its censoring bound."""
        t = np.asarray(result.time_s)
        time, censoring = _first_crossing(t, _effluent_kg_m3(result), self.limit_kg_m3,
                                          self.interpolation)
        if censoring == "none":
            return QuantityValue(key=self.key, units=self.units, value=time)
        bound = float(t[-1] if censoring == "right" else t[0])
        return QuantityValue(key=self.key, units=self.units, value=None,
                             censoring=censoring, bound=bound)

    def describe(self) -> dict[str, object]:
        """Definition used in report fingerprints."""
        return {"kind": "exceedance_time", "limit_kg_m3": self.limit_kg_m3,
                "interpolation": self.interpolation, "units": self.units}


def default_quantities() -> tuple[DecisionQuantity, ...]:
    """Breakthrough times ``t_0.05``, ``t_0.1`` and ``t_0.5`` (s)."""
    return tuple(BreakthroughTime(fraction=x) for x in (0.05, 0.1, 0.5))


def extract(result: SimulationResult,
            quantities: tuple[DecisionQuantity, ...] | list[DecisionQuantity]
            ) -> tuple[QuantityValue, ...]:
    """Evaluate several decision quantities on one result.

    Parameters
    ----------
    result : SimulationResult
        A fixed-bed column result (LDF or HSDM).
    quantities : sequence of DecisionQuantity
        Quantities with distinct keys.

    Returns
    -------
    tuple of QuantityValue
        In the order of ``quantities``.
    """
    keys = [q.key for q in quantities]
    if len(set(keys)) != len(keys):
        raise ValueError("Decision quantity keys must be unique")
    return tuple(q.extract(result) for q in quantities)

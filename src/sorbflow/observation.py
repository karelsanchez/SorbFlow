"""Experimental SI observation operators; no interpolation or fitted transport.

An upstream bed-output shift is valid only for a compatible time-invariant bed
with initial equilibrium/history. This module cannot establish that physics.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from .units import finite_scalar

ScalarSignal = Callable[[float], float]


def _positive(value: float, name: str) -> float:
    result = finite_scalar(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _delay(value: float) -> float:
    result = finite_scalar(value, "delay_s")
    if result < 0:
        raise ValueError("delay_s must be nonnegative")
    return result


@dataclass(frozen=True, slots=True)
class LiquidSegment:
    """Separate upstream segment; only ideal plug delay and identity implemented."""

    volume_m3: float
    position: Literal["upstream"] = "upstream"
    model: Literal["plug", "none"] = "plug"

    def __post_init__(self) -> None:
        volume = finite_scalar(self.volume_m3, "volume_m3")
        if volume < 0 or self.position != "upstream" or self.model not in ("plug", "none"):
            raise ValueError("Require nonnegative volume, upstream position and plug/none model")
        object.__setattr__(self, "volume_m3", volume)

    def residence_time(self, flow_m3_s: float) -> float:
        """V/Q for the plug model; identity deliberately applies no segment."""
        flow = _positive(flow_m3_s, "flow_m3_s")
        return (finite_scalar(self.volume_m3 / flow, "residence_time")
                if self.model == "plug" else 0.)


@dataclass(frozen=True, slots=True)
class CollectionWindow:
    """Collection bounds and independently declared integrated liquid volume."""

    start_s: float
    end_s: float
    volume_m3: float

    def __post_init__(self) -> None:
        start = finite_scalar(self.start_s, "start_s")
        end = finite_scalar(self.end_s, "end_s")
        volume = _positive(self.volume_m3, "volume_m3")
        if end <= start:
            raise ValueError("Collection window must have positive duration")
        object.__setattr__(self, "start_s", start)
        object.__setattr__(self, "end_s", end)
        object.__setattr__(self, "volume_m3", volume)

    @property
    def flags(self) -> tuple[str, ...]:
        return ("WINDOW_STARTS_BEFORE_T0",) if self.start_s < 0 else ()


def collection_window(
    time_s: float, volume_m3: float, flow_m3_s: float,
    rule: Literal["mid", "start", "end"] = "mid",
) -> CollectionWindow:
    """Constant-Q window; instantaneous observations are deliberately separate."""
    time = finite_scalar(time_s, "time_s")
    duration = finite_scalar(_positive(volume_m3, "volume_m3") /
                             _positive(flow_m3_s, "flow_m3_s"), "duration_s")
    if rule not in ("mid", "start", "end"):
        raise ValueError("rule must be mid, start or end; instant is a separate operator")
    left = time - {"start": 0., "mid": .5, "end": 1.}[rule] * duration
    return CollectionWindow(left, left + duration, volume_m3)


@dataclass(frozen=True, slots=True)
class SampledSignal:
    """Exact sample lookup; missing solver endpoints are errors, never interpolated."""

    times_s: Sequence[float]
    values: Sequence[float]

    def __post_init__(self) -> None:
        try:
            times = tuple(finite_scalar(v, "times_s") for v in self.times_s)
            values = tuple(finite_scalar(v, "values") for v in self.values)
        except TypeError as exc:
            raise ValueError("Sample arrays must be one-dimensional sequences") from exc
        if not times or len(times) != len(values):
            raise ValueError("Nonempty matching sample arrays required")
        if any(b <= a for a, b in zip(times, times[1:], strict=False)):
            raise ValueError("Sample times must strictly increase")
        object.__setattr__(self, "times_s", times)
        object.__setattr__(self, "values", values)

    def __call__(self, time_s: float) -> float:
        time = finite_scalar(time_s, "time_s")
        for sampled_time, value in zip(self.times_s, self.values, strict=True):
            if time == sampled_time:
                return value
        raise ValueError(f"Missing exact sample endpoint: {time}; request it from the solver")


def _shifted_value(
    signal: ScalarSignal, time_s: float, delay_s: float, initially_at_rest: bool,
    history: ScalarSignal | None,
) -> float:
    if type(initially_at_rest) is not bool:
        raise ValueError("initially_at_rest must be an explicit boolean")
    if not callable(signal) or (history is not None and not callable(history)):
        raise ValueError("signal and optional history must be callable")
    time = finite_scalar(time_s, "time_s")
    delay = _delay(delay_s)
    shifted = finite_scalar(time - delay, "shifted_time_s")
    if shifted < 0:
        if history is not None:
            return finite_scalar(history(shifted), "history value")
        if initially_at_rest:
            return 0.
        raise ValueError("Negative time requires explicit history or initially_at_rest")
    return finite_scalar(signal(shifted), "signal value")


def plug_delay(
    signal: ScalarSignal, time_s: float, delay_s: float, *,
    initially_at_rest: bool = False, history: ScalarSignal | None = None,
) -> float:
    """Delay a prescribed signal; history covers negative times.

    A nonzero history is allowed. Using this as an upstream bed-output substitution
    additionally requires time invariance and a compatible initial equilibrium;
    those conditions cannot be inferred from this callable.
    """
    return _shifted_value(signal, time_s, delay_s, initially_at_rest, history)


def fraction_average(
    cumulative_mass: ScalarSignal, window: CollectionWindow, *, delay_s: float = 0.,
    initially_at_rest: bool = False, mass_history: ScalarSignal | None = None,
) -> float:
    """(M(b-delay)-M(a-delay))/V; endpoint numerical error is retained.

    M is cumulative solute mass in kg. An additive mass origin cancels. V is actual
    collected volume, not automatically a container capacity. Nonzero delay assumes
    constant Q when shifting bed cumulative mass. For variable Q, use delay_s=0
    with M already integrating the correctly delayed concentration against Q(t),
    and supply the integrated volume. Negative history is explicit; windows are
    never clipped or renormalized. The caller must establish physical validity of
    any upstream-bed substitution (time invariance and compatible initial state).
    initially_at_rest supplies zero prehistory, requiring a consistent zero origin
    of M; otherwise supply mass_history with the same additive origin as M.
    """
    if not isinstance(window, CollectionWindow):
        raise ValueError("window must be CollectionWindow")
    if not callable(cumulative_mass):
        raise ValueError("cumulative_mass must be callable")
    left = _shifted_value(cumulative_mass, window.start_s, delay_s,
                          initially_at_rest, mass_history)
    right = _shifted_value(cumulative_mass, window.end_s, delay_s,
                           initially_at_rest, mass_history)
    return finite_scalar((right - left) / window.volume_m3, "fraction concentration")

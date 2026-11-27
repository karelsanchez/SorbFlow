"""Observed order, Richardson extrapolation and Roache's Grid Convergence Index.

Notation (grid 1 is the finest): ``h1 < h2 < h3``, ``r21 = h2/h1``,
``r32 = h3/h2``, ``e21 = phi2 - phi1``, ``e32 = phi3 - phi2``.

Three or more grids (the three finest are used)
    ``s = sign(e32/e21)``; the observed order solves (Celik et al. 2008)
    ``p = [ln|e32/e21| + ln((r21^p - s)/(r32^p - s))] / ln r21``
    (closed form ``p = ln(e32/e21)/ln r`` for a constant ratio ``r``).
    ``phi_ext = phi1 + (phi1 - phi2)/(r21^p - 1)`` and
    ``GCI = Fs |phi1 - phi2| / (r21^p - 1)`` with ``Fs = 1.25``.
Two grids
    ``p`` is the declared formal order and ``Fs = 3``.
Non-asymptotic sequences
    Oscillatory (``s < 0``), divergent or implausible (``p`` outside
    ``p_band``) sequences are flagged and receive the conservative bound
    ``U = Fs_fallback * max(|e21|, |e32| / r32^p_ref)`` with ``Fs_fallback = 3``
    and ``p_ref`` the formal order (1 when undeclared); ``phi_ext`` is then
    the finest value ``phi1`` (no extrapolation is trusted).

The band ``phi1 +- U`` is the error band of the finest-grid value in the sense of
Roache (1994, 1998); it contains ``phi_ext`` because ``Fs >= 1``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

__all__ = ["ConvergenceType", "RichardsonEstimate", "observed_order", "richardson_estimate"]

ConvergenceType = Literal["monotone", "oscillatory", "divergent", "grid_independent",
                          "two_grid", "single_grid"]

FS_THREE_GRIDS = 1.25
FS_TWO_GRIDS = 3.0
FS_FALLBACK = 3.0


@dataclass(frozen=True, slots=True, kw_only=True)
class RichardsonEstimate:
    """Discretization error estimate of one scalar from a grid sequence.

    Attributes
    ----------
    h : tuple of float
        Representative cell sizes, finest first (any consistent unit).
    values : tuple of float
        Quantity on each grid, finest first.
    p_observed : float or None
        Observed order from the three finest grids (``None`` with < 3 grids or
        when undefined).
    p_used : float or None
        Order used in the extrapolation and GCI.
    extrapolated : float
        Richardson value (``values[0]`` when extrapolation is not trusted).
    error_bound : float or None
        GCI (or conservative fallback) bound on ``|phi_exact - values[0]|``,
        same units as ``values``; ``None`` with a single grid.
    safety_factor : float or None
        Factor ``Fs`` actually applied.
    convergence : ConvergenceType
        Classification of the finest triplet.
    asymptotic : bool
        True when the GCI with observed (three grids) or formal (two grids)
        order was applied rather than the fallback.
    flags : tuple of str
        Diagnostics: ``oscillatory``, ``divergent``, ``order_below_band``,
        ``order_above_band``, ``order_drift``, ``order_iteration_failed``,
        ``grid_independent``, ``two_grids``, ``single_grid``.
    """

    h: tuple[float, ...]
    values: tuple[float, ...]
    p_observed: float | None
    p_used: float | None
    extrapolated: float
    error_bound: float | None
    safety_factor: float | None
    convergence: ConvergenceType
    asymptotic: bool
    flags: tuple[str, ...]

    @property
    def finest(self) -> float:
        """Value on the finest grid."""
        return self.values[0]

    def to_dict(self) -> dict[str, object]:
        """JSON-compatible mapping."""
        return {"h": list(self.h), "values": list(self.values), "p_observed": self.p_observed,
                "p_used": self.p_used, "extrapolated": self.extrapolated,
                "error_bound": self.error_bound, "safety_factor": self.safety_factor,
                "convergence": self.convergence, "asymptotic": self.asymptotic,
                "flags": list(self.flags)}


def observed_order(values: Sequence[float], h: Sequence[float], *,
                   max_iterations: int = 100) -> float | None:
    """Observed order of a monotone triplet (finest first); ``None`` if undefined.

    Parameters
    ----------
    values : sequence of 3 float
        ``phi1, phi2, phi3`` on grids ``h1 < h2 < h3``.
    h : sequence of 3 float
        Cell sizes.
    max_iterations : int
        Fixed-point iterations for a nonconstant refinement ratio.

    Returns
    -------
    float or None
        Signed order (negative for a divergent monotone sequence); ``None`` when
        ``e21`` or ``e32`` vanishes, the sequence is oscillatory, or the
        fixed-point iteration fails.
    """
    if len(values) != 3 or len(h) != 3:
        raise ValueError("observed_order needs exactly three grids")
    phi1, phi2, phi3 = (float(v) for v in values)
    h1, h2, h3 = (float(v) for v in h)
    e21, e32 = phi2 - phi1, phi3 - phi2
    if e21 == 0 or e32 == 0 or e32 / e21 < 0:
        return None
    r21, r32 = h2 / h1, h3 / h2
    log_ratio = math.log(e32 / e21)
    p = log_ratio / math.log(r21)
    if math.isclose(r21, r32, rel_tol=1e-12):
        return p
    for _ in range(max_iterations):
        try:
            q = math.log((r21**p - 1) / (r32**p - 1))
        except (ValueError, ZeroDivisionError, OverflowError):
            return None
        new = (log_ratio + q) / math.log(r21)
        if abs(new - p) <= 1e-12 * max(1.0, abs(p)):
            return new
        p = new
    return None


def _validated(values: Sequence[float], h: Sequence[float]
               ) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if len(values) != len(h) or not values:
        raise ValueError("values and h must be nonempty and of equal length")
    pairs = sorted(zip((float(x) for x in h), (float(v) for v in values), strict=True))
    hs = tuple(p[0] for p in pairs)
    vs = tuple(p[1] for p in pairs)
    if not all(math.isfinite(x) and x > 0 for x in hs) or not all(map(math.isfinite, vs)):
        raise ValueError("h must be positive and values finite")
    if any(b <= a * (1 + 1e-12) for a, b in zip(hs, hs[1:], strict=False)):
        raise ValueError("Grid sizes must be distinct")
    return hs, vs


def richardson_estimate(values: Sequence[float], h: Sequence[float], *,
                        formal_order: float | None = None,
                        p_band: tuple[float, float] | None = None) -> RichardsonEstimate:
    """Estimate the discretization error of the finest-grid value.

    Parameters
    ----------
    values : sequence of float
        Quantity on each grid (any order; paired with ``h``).
    h : sequence of float
        Representative cell sizes (e.g. ``L / axial_cells``).
    formal_order : float, optional
        Formal order of the scheme. Required for two grids; with three or more
        grids the GCI uses ``min(p_observed, formal_order)`` (more conservative
        when the observed order exceeds the formal one).
    p_band : (float, float), optional
        Plausible observed orders. Default ``(0.5, formal_order + 1)`` or
        ``(0.5, 3.0)`` when no formal order is declared. Outside the band the
        conservative fallback applies.

    Returns
    -------
    RichardsonEstimate
    """
    hs, vs = _validated(values, h)
    if formal_order is not None and not (math.isfinite(formal_order) and formal_order > 0):
        raise ValueError("formal_order must be positive")
    low, high = p_band if p_band is not None else (
        0.5, (formal_order + 1.0) if formal_order is not None else 3.0)
    if not 0 < low < high:
        raise ValueError("p_band must satisfy 0 < low < high")
    p_ref = formal_order if formal_order is not None else 1.0
    if len(vs) == 1:
        return RichardsonEstimate(h=hs, values=vs, p_observed=None, p_used=None,
                                  extrapolated=vs[0], error_bound=None, safety_factor=None,
                                  convergence="single_grid", asymptotic=False,
                                  flags=("single_grid",))
    phi1, phi2 = vs[0], vs[1]
    r21 = hs[1] / hs[0]
    e21 = phi2 - phi1
    if len(vs) == 2:
        if formal_order is None:
            raise ValueError("Two-grid estimates require a declared formal_order")
        denom = r21**formal_order - 1
        return RichardsonEstimate(
            h=hs, values=vs, p_observed=None, p_used=formal_order,
            extrapolated=phi1 - e21 / denom, error_bound=FS_TWO_GRIDS * abs(e21) / denom,
            safety_factor=FS_TWO_GRIDS, convergence="two_grid", asymptotic=True,
            flags=("two_grids",))
    phi3 = vs[2]
    r32 = hs[2] / hs[1]
    e32 = phi3 - phi2
    flags: list[str] = []
    if e21 == 0 and e32 == 0:
        return RichardsonEstimate(h=hs, values=vs, p_observed=None, p_used=None,
                                  extrapolated=phi1, error_bound=0.0, safety_factor=None,
                                  convergence="grid_independent", asymptotic=True,
                                  flags=("grid_independent",))
    convergence: ConvergenceType
    if e21 * e32 < 0:
        convergence = "oscillatory"
        flags.append("oscillatory")
    elif abs(e21) >= abs(e32):
        convergence = "divergent"
        flags.append("divergent")
    else:
        convergence = "monotone"
    p_obs = observed_order(vs[:3], hs[:3]) if convergence == "monotone" else None
    if convergence == "monotone" and p_obs is None:
        flags.append("order_iteration_failed")
    if p_obs is not None and p_obs < low:
        flags.append("order_below_band")
    if p_obs is not None and p_obs > high:
        flags.append("order_above_band")
    if len(vs) >= 4 and p_obs is not None:
        p_next = observed_order(vs[1:4], hs[1:4])
        if p_next is None or abs(p_next - p_obs) > 0.25 * max(p_obs, 1.0):
            flags.append("order_drift")
    trusted = (p_obs is not None and low <= p_obs <= high)
    if trusted:
        assert p_obs is not None
        p_used = min(p_obs, formal_order) if formal_order is not None else p_obs
        denom = r21**p_used - 1
        return RichardsonEstimate(
            h=hs, values=vs, p_observed=p_obs, p_used=p_used,
            extrapolated=phi1 - e21 / denom, error_bound=FS_THREE_GRIDS * abs(e21) / denom,
            safety_factor=FS_THREE_GRIDS, convergence=convergence, asymptotic=True,
            flags=tuple(flags))
    bound = FS_FALLBACK * max(abs(e21), abs(e32) / r32**p_ref)
    return RichardsonEstimate(
        h=hs, values=vs, p_observed=p_obs, p_used=None, extrapolated=phi1,
        error_bound=bound, safety_factor=FS_FALLBACK, convergence=convergence,
        asymptotic=False, flags=tuple(flags))

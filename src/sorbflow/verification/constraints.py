"""Classification of design constraints under estimated discretization error.

A constraint ``phi >= threshold`` (or ``phi <= threshold``) is judged on the
error band ``[phi_h - U, phi_h + U]`` of the finest-grid value ``phi_h`` with
bound ``U`` (GCI or conservative fallback); the Richardson value lies inside
this band. The outcome is

* ``SATISFIED`` when the whole band satisfies the constraint,
* ``VIOLATED`` when the whole band violates it,
* ``UNDETERMINED`` otherwise, with a refinement recommendation: the axial grid
  at which the predicted bound ``U (h'/h)^p`` falls below the margin
  ``|phi_h - threshold|``.

Censored quantities are classified from their censoring bound when that is
logically decisive (e.g. ``t_10 > duration >= required time``); otherwise the
recommendation is to extend the simulated horizon.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from .convergence import ConvergenceReport, QuantityReport

__all__ = ["Constraint", "ConstraintAssessment", "ConstraintStatus", "classify",
           "classify_report"]

ConstraintStatus = Literal["SATISFIED", "VIOLATED", "UNDETERMINED"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Constraint:
    """Design constraint on one decision quantity.

    Attributes
    ----------
    quantity_key : str
        Key of the decision quantity (e.g. ``"t_0.1_s"``).
    sense : {">=", "<="}
        ``">="`` requires ``phi >= threshold``; ``"<="`` requires ``phi <= threshold``.
    threshold : float
        Threshold in the quantity units.
    label : str
        Free description, for reports.
    """

    quantity_key: str
    sense: Literal[">=", "<="]
    threshold: float
    label: str = ""

    def __post_init__(self) -> None:
        if self.sense not in (">=", "<="):
            raise ValueError("sense must be '>=' or '<='")
        value = float(self.threshold)
        if not math.isfinite(value):
            raise ValueError("threshold must be finite")
        object.__setattr__(self, "threshold", value)


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstraintAssessment:
    """Outcome of :func:`classify`.

    Attributes
    ----------
    status : {"SATISFIED", "VIOLATED", "UNDETERMINED"}
    interval_low, interval_high : float or None
        Error band used for the decision (``None`` when censored).
    margin : float or None
        Signed distance of the finest value to the threshold, positive on the
        feasible side.
    recommended_axial_cells : int or None
        Axial grid predicted to resolve an UNDETERMINED decision.
    recommendation : str
        Human-readable next step (empty when decided).
    """

    constraint: Constraint
    status: ConstraintStatus
    value: float | None
    error_bound: float | None
    interval_low: float | None
    interval_high: float | None
    margin: float | None
    recommended_axial_cells: int | None
    recommendation: str

    def to_dict(self) -> dict[str, object]:
        """JSON-compatible mapping."""
        return {"quantity_key": self.constraint.quantity_key, "sense": self.constraint.sense,
                "threshold": self.constraint.threshold, "label": self.constraint.label,
                "status": self.status, "value": self.value, "error_bound": self.error_bound,
                "interval_low": self.interval_low, "interval_high": self.interval_high,
                "margin": self.margin, "recommended_axial_cells": self.recommended_axial_cells,
                "recommendation": self.recommendation}


def _censored(report: QuantityReport, constraint: Constraint) -> ConstraintAssessment:
    bound = report.censored_bound
    assert bound is not None
    status: ConstraintStatus = "UNDETERMINED"
    lower_bounded = report.censoring == "right"  # exact > bound
    if lower_bounded and constraint.sense == ">=" and bound >= constraint.threshold:
        status = "SATISFIED"
    elif lower_bounded and constraint.sense == "<=" and bound >= constraint.threshold:
        status = "VIOLATED"
    elif not lower_bounded and constraint.sense == "<=" and bound <= constraint.threshold:
        status = "SATISFIED"
    elif not lower_bounded and constraint.sense == ">=" and bound < constraint.threshold:
        status = "VIOLATED"
    note = "" if status != "UNDETERMINED" else (
        "Quantity censored by the simulated horizon; extend duration_s beyond the threshold"
        if lower_bounded else "Quantity censored at the first sample; refine the time grid")
    return ConstraintAssessment(
        constraint=constraint, status=status, value=None, error_bound=None,
        interval_low=None, interval_high=None, margin=None, recommended_axial_cells=None,
        recommendation=note)


def classify(report: QuantityReport, constraint: Constraint, *,
             refinement_ratio: int = 2) -> ConstraintAssessment:
    """Classify a design constraint against an error-controlled quantity.

    Parameters
    ----------
    report : QuantityReport
        Entry of a :class:`ConvergenceReport` (``report.quantity(key)``).
    constraint : Constraint
        Constraint on the same quantity.
    refinement_ratio : int
        Ratio of the geometric sequence, used to round the recommendation up to a
        reachable grid ``N_fine r^k``.

    Returns
    -------
    ConstraintAssessment
    """
    if report.key != constraint.quantity_key:
        raise ValueError("Constraint and report refer to different quantities")
    if report.status == "CENSORED":
        return _censored(report, constraint)
    value = report.value
    assert value is not None
    bound = report.error_bound
    sign = 1.0 if constraint.sense == ">=" else -1.0
    margin = sign * (value - constraint.threshold)
    if bound is None:
        return ConstraintAssessment(
            constraint=constraint, status="UNDETERMINED", value=value, error_bound=None,
            interval_low=None, interval_high=None, margin=margin,
            recommended_axial_cells=report.finest_axial_cells * refinement_ratio**2,
            recommendation="No error estimate: solve at least three grids of a sequence")
    low, high = value - bound, value + bound
    if constraint.sense == ">=":
        status: ConstraintStatus = ("SATISFIED" if low >= constraint.threshold else
                                    "VIOLATED" if high < constraint.threshold else
                                    "UNDETERMINED")
    else:
        status = ("SATISFIED" if high <= constraint.threshold else
                  "VIOLATED" if low > constraint.threshold else "UNDETERMINED")
    cells: int | None = None
    note = ""
    if status == "UNDETERMINED":
        estimate = report.estimate
        p = None if estimate is None else estimate.p_used
        if margin == 0:
            note = ("Finest value equals the threshold; refinement cannot decide, "
                    "revise the design margin")
        elif p is None or estimate is None or not estimate.asymptotic:
            note = ("Non-asymptotic grid sequence; refine further and re-estimate "
                    "before deciding")
            cells = report.finest_axial_cells * refinement_ratio
        else:
            # U(h') = U (h'/h)^p < |margin|  =>  N' > N (U/|margin|)^(1/p).
            needed = report.finest_axial_cells * (bound / abs(margin)) ** (1.0 / p)
            k = max(1, math.ceil(math.log(needed / report.finest_axial_cells)
                                 / math.log(refinement_ratio) - 1e-9))
            cells = report.finest_axial_cells * refinement_ratio**k
            note = (f"Error band straddles the threshold; refine to about {cells} axial "
                    "cells (prediction assumes the observed order persists)")
    return ConstraintAssessment(
        constraint=constraint, status=status, value=value, error_bound=bound,
        interval_low=low, interval_high=high, margin=margin,
        recommended_axial_cells=cells, recommendation=note)


def classify_report(report: ConvergenceReport, constraints: Sequence[Constraint]
                    ) -> tuple[ConstraintAssessment, ...]:
    """Classify several constraints against one convergence report."""
    return tuple(classify(report.quantity(c.quantity_key), c,
                          refinement_ratio=report.refinement_ratio) for c in constraints)

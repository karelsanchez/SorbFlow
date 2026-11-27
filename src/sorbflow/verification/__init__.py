"""Decision-oriented numerical error control for fixed-bed simulations.

Discretization error is estimated for the quantities used in design
(breakthrough times, bed volumes, useful capacity, effluent at a service time)
rather than for whole curves: geometric mesh sequences, observed order,
Richardson extrapolation and Roache's Grid Convergence Index, adaptive
refinement to a tolerance, and classification of design constraints as
SATISFIED / VIOLATED / UNDETERMINED. See ``docs/decision_error_control.md``.
"""

from .constraints import (
    Constraint,
    ConstraintAssessment,
    ConstraintStatus,
    classify,
    classify_report,
)
from .convergence import (
    ConvergenceReport,
    GridRun,
    QuantityReport,
    QuantityStatus,
    converge,
    estimate_quantities,
    mesh_sequence,
)
from .quantities import (
    BedVolumesAt,
    BreakthroughTime,
    DecisionQuantity,
    EffluentAt,
    ExceedanceTime,
    QuantityValue,
    UsefulCapacity,
    default_quantities,
    extract,
)
from .richardson import RichardsonEstimate, observed_order, richardson_estimate

__all__ = [
    "BedVolumesAt",
    "BreakthroughTime",
    "Constraint",
    "ConstraintAssessment",
    "ConstraintStatus",
    "ConvergenceReport",
    "DecisionQuantity",
    "EffluentAt",
    "ExceedanceTime",
    "GridRun",
    "QuantityReport",
    "QuantityStatus",
    "QuantityValue",
    "RichardsonEstimate",
    "UsefulCapacity",
    "classify",
    "classify_report",
    "converge",
    "default_quantities",
    "estimate_quantities",
    "extract",
    "mesh_sequence",
    "observed_order",
    "richardson_estimate",
]

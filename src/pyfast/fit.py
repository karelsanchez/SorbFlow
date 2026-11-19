"""Inverse-workflow facade, with local diagnostics and explicit physical units."""

from .calibration.least_squares import FitError, FitResult
from .calibration.least_squares import fit_batch_rate as batch_rate
from .calibration.least_squares import fit_isotherm as isotherm

__all__ = ["FitError", "FitResult", "batch_rate", "isotherm"]

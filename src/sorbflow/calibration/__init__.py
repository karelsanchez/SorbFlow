"""Least-squares fitting with local SVD identifiability diagnostics."""

from .least_squares import FitError, FitResult, fit_batch_rate, fit_isotherm

__all__ = ["FitError", "FitResult", "fit_batch_rate", "fit_isotherm"]

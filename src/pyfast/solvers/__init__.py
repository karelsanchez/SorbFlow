"""Numerical options, failures and result contracts."""

from .integration import SimulationError
from .options import SolverOptions
from .results import SimulationResult, SolverDiagnostics

__all__ = ["SimulationError", "SolverOptions", "SimulationResult", "SolverDiagnostics"]

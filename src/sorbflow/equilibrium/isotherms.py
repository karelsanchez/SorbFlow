"""Independent, vectorized mass-based equilibrium in SI units."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import ArrayLike
from scipy.special import expit

from .._arrays import FloatArray, nonnegative_array
from ..schemas import Freundlich, Langmuir, Linear


class Isotherm(Protocol):
    """Extensible concentration -> loading contract at a fixed calibration T.

    Concentration: kg solute/m3 liquid. Loading: kg solute/kg dry adsorbent.
    Derivative: m3/kg dry adsorbent. Output preserves the input shape.
    """

    def loading(self, concentration_kg_m3: ArrayLike) -> FloatArray: ...

    def derivative(self, concentration_kg_m3: ArrayLike) -> FloatArray: ...


def _checked(value: ArrayLike) -> FloatArray:
    result = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(result)):
        raise ValueError("Isotherm result exceeds finite floating-point range")
    return result


@dataclass(frozen=True, slots=True)
class LangmuirIsotherm:
    """Saturating equilibrium, evaluated in log form to avoid b*c overflow."""

    parameters: Langmuir

    def loading(self, concentration_kg_m3: ArrayLike) -> FloatArray:
        c = nonnegative_array(concentration_kg_m3, "concentration_kg_m3")
        return _checked(self._loading_unchecked(c))

    def derivative(self, concentration_kg_m3: ArrayLike) -> FloatArray:
        c = nonnegative_array(concentration_kg_m3, "concentration_kg_m3")
        return _checked(self._derivative_unchecked(c))

    def _loading_unchecked(self, c: FloatArray) -> FloatArray:
        """Hot-loop kernel: ``c`` must already be a finite nonnegative float array."""
        with np.errstate(divide="ignore"):
            log_bc = np.log(self.parameters.affinity_m3_kg) + np.log(c)
        return np.asarray(self.parameters.qmax_kg_kg * expit(log_bc))

    def _derivative_unchecked(self, c: FloatArray) -> FloatArray:
        """Hot-loop kernel: ``c`` must already be a finite nonnegative float array."""
        p = self.parameters
        with np.errstate(divide="ignore", over="ignore"):
            log_bc = np.log(p.affinity_m3_kg) + np.log(c)
            value = np.exp(
                np.log(p.qmax_kg_kg) + np.log(p.affinity_m3_kg) - 2 * np.logaddexp(0, log_bc)
            )
        return np.asarray(value)


@dataclass(frozen=True, slots=True)
class FreundlichIsotherm:
    """Normalized power law. A singular derivative at zero is an explicit error."""

    parameters: Freundlich

    def loading(self, concentration_kg_m3: ArrayLike) -> FloatArray:
        c = nonnegative_array(concentration_kg_m3, "concentration_kg_m3")
        return _checked(self._loading_unchecked(c))

    def derivative(self, concentration_kg_m3: ArrayLike) -> FloatArray:
        c = nonnegative_array(concentration_kg_m3, "concentration_kg_m3")
        if self.parameters.exponent < 1 and np.any(c == 0):
            raise ValueError("Freundlich derivative is singular at zero when exponent < 1")
        return _checked(self._derivative_unchecked(c))

    def _loading_unchecked(self, c: FloatArray) -> FloatArray:
        """Hot-loop kernel: ``c`` must already be a finite nonnegative float array."""
        p = self.parameters
        with np.errstate(divide="ignore", over="ignore", under="ignore"):
            value = np.exp(np.log(p.q_ref_kg_kg) + p.exponent * (np.log(c) - np.log(p.c_ref_kg_m3)))
        return np.asarray(value)

    def _derivative_unchecked(self, c: FloatArray) -> FloatArray:
        """Hot-loop kernel; returns +inf at ``c == 0`` when the exponent is below one."""
        p = self.parameters
        if p.exponent == 1:
            return np.full_like(c, p.q_ref_kg_kg / p.c_ref_kg_m3)
        with np.errstate(divide="ignore", over="ignore", under="ignore"):
            value = np.exp(
                np.log(p.exponent)
                + np.log(p.q_ref_kg_kg)
                - np.log(p.c_ref_kg_m3)
                + (p.exponent - 1) * (np.log(c) - np.log(p.c_ref_kg_m3))
            )
        return np.asarray(value)


@dataclass(frozen=True, slots=True)
class LinearIsotherm:
    """Henry-type mass-based equilibrium, also providing an exact tracer limit."""

    parameters: Linear

    def loading(self, concentration_kg_m3: ArrayLike) -> FloatArray:
        c = nonnegative_array(concentration_kg_m3, "concentration_kg_m3")
        return _checked(self._loading_unchecked(c))

    def derivative(self, concentration_kg_m3: ArrayLike) -> FloatArray:
        c = nonnegative_array(concentration_kg_m3, "concentration_kg_m3")
        return self._derivative_unchecked(c)

    def _loading_unchecked(self, c: FloatArray) -> FloatArray:
        """Hot-loop kernel: ``c`` must already be a finite nonnegative float array."""
        with np.errstate(over="ignore"):
            return np.asarray(self.parameters.distribution_m3_kg * c)

    def _derivative_unchecked(self, c: FloatArray) -> FloatArray:
        """Hot-loop kernel: ``c`` must already be a finite nonnegative float array."""
        return np.full_like(c, self.parameters.distribution_m3_kg)


def isotherm_from_parameters(parameters: Langmuir | Freundlich | Linear) -> Isotherm:
    """Resolve explicit parameter types; no contaminant or material is hardcoded."""
    if isinstance(parameters, Langmuir):
        return LangmuirIsotherm(parameters)
    if isinstance(parameters, Freundlich):
        return FreundlichIsotherm(parameters)
    if isinstance(parameters, Linear):
        return LinearIsotherm(parameters)
    raise ValueError("Unsupported equilibrium parameter type")


def trial_loading(model: Isotherm, concentration: FloatArray) -> FloatArray:
    """Odd extension for implicit trial states only; physical outputs are checked."""
    return np.asarray(np.sign(concentration) * model.loading(np.abs(concentration)))


_BUILTIN = (LangmuirIsotherm, FreundlichIsotherm, LinearIsotherm)


def _loading_kernel(model: Isotherm, concentration: FloatArray) -> FloatArray:
    """Internal hot-loop loading for finite nonnegative float arrays.

    Built-in isotherms skip the public input validation and the finiteness reduction;
    any other protocol implementation is routed through its public ``loading``.
    Callers must check the finiteness of the values they finally accept.
    """
    if isinstance(model, _BUILTIN):
        return model._loading_unchecked(concentration)
    return np.asarray(model.loading(concentration), dtype=np.float64)


def _trial_loading_unchecked(model: Isotherm, concentration: FloatArray) -> FloatArray:
    """Odd extension of :func:`_loading_kernel`; same values as ``trial_loading``."""
    return np.asarray(np.sign(concentration) * _loading_kernel(model, np.abs(concentration)))

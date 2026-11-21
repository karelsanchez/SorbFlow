"""Scalar unit boundary: explicit physical units in, finite SI magnitudes out."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any

import pint

_REGISTRY: pint.UnitRegistry[Any] = pint.UnitRegistry()


class UnitError(ValueError):
    """A value has missing, unknown or incompatible physical units."""


def finite_scalar(value: object, name: str) -> float:
    """Reject booleans, non-real values, arrays and non-finite magnitudes."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def quantity(value: float, unit: str) -> pint.Quantity[Any]:
    """Create a finite scalar quantity, including offset units such as degC.

    This is the public quantity factory. No mutable registry is exposed.
    """
    magnitude = finite_scalar(value, "value")
    if not isinstance(unit, str) or not unit.strip():
        raise UnitError("unit must be an explicit nonempty unit string")
    try:
        return _REGISTRY.Quantity(magnitude, unit)
    except (pint.UndefinedUnitError, ValueError, TypeError) as exc:
        raise UnitError(f"Invalid unit: {unit}") from exc


def to_si(value: pint.Quantity[Any], target_unit: str) -> float:
    """Convert a scalar quantity to a caller-declared SI unit.

    The function does not infer chemical species, dry/wet basis, ppm or molar mass.
    """
    if not isinstance(value, pint.Quantity):
        raise UnitError("A quantity with explicit units is required")
    try:
        converted = value.to(target_unit)
    except (pint.DimensionalityError, pint.UndefinedUnitError) as exc:
        raise UnitError(f"Expected units compatible with {target_unit}") from exc
    return finite_scalar(converted.magnitude, "magnitude")

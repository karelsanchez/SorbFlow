"""Shared finite real array checks; no physical units are inferred here."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def _contains_boolean(value: object) -> bool:
    # Inspect containers before NumPy can turn mixed bool/float inputs into floats.
    if isinstance(value, (bool, np.bool_)):
        return True
    if isinstance(value, np.ndarray):
        return bool(value.dtype.kind == "b")
    if isinstance(value, (list, tuple)):
        return any(_contains_boolean(item) for item in value)
    return False


def real_array(value: ArrayLike, name: str) -> FloatArray:
    """Copy numeric input, preserving shape, rejecting booleans/complex/NaN."""
    if _contains_boolean(value):
        raise ValueError(f"{name} must contain real numbers, not booleans")
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise ValueError(f"{name} must contain real numbers")
    result = np.array(raw, dtype=np.float64, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


def nonnegative_array(value: ArrayLike, name: str) -> FloatArray:
    """Require nonnegative physical values, including scalar (zero-D) input."""
    result = real_array(value, name)
    if np.any(result < 0):
        raise ValueError(f"{name} must be nonnegative")
    return result

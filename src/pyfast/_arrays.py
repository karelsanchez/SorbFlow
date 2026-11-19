"""Shared finite real array checks; no physical units are inferred here."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def real_array(value: ArrayLike, name: str) -> FloatArray:
    """Copy numeric input, preserving shape, rejecting booleans/complex/NaN."""
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

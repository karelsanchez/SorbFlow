"""Experimental signed observations for a fixed, diagonal Gaussian error model."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..units import finite_scalar


@dataclass(frozen=True, slots=True, kw_only=True)
class SignedGaussianMeasurements:
    """Finite measurements in SI; signed values are distinct from physical states.

    The model is y = c + sigma*z with known, positive, fixed diagonal sigma.
    Values are retained without clipping, censoring or resampling. Construction
    does not establish normality or independence of the experimental errors.
    """

    experiment_id: str
    species_name: str
    time_s: tuple[float, ...]
    concentration_kg_m3: tuple[float, ...]
    source_sha256: str
    std_kg_m3: tuple[float, ...]

    def __post_init__(self) -> None:
        for name in ("experiment_id", "species_name"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be nonempty text")
        if (not isinstance(self.source_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", self.source_sha256) is None):
            raise ValueError("source_sha256 must be a lowercase SHA-256 hex digest")
        for name in ("time_s", "concentration_kg_m3", "std_kg_m3"):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)):
                raise ValueError(f"{name} must be a sequence")
            normalized = tuple(finite_scalar(value, name) for value in values)
            if name == "time_s" and any(value < 0 for value in normalized):
                raise ValueError("Measurement times must be nonnegative")
            if name == "std_kg_m3" and any(value <= 0 for value in normalized):
                raise ValueError("Known standard deviations must be positive")
            object.__setattr__(self, name, normalized)
        if (not self.time_s or len(self.time_s) != len(self.concentration_kg_m3)
                or len(self.time_s) != len(self.std_kg_m3)):
            raise ValueError("Nonempty matching time, measurement and sigma arrays are required")
        if any(b <= a for a, b in zip(self.time_s, self.time_s[1:], strict=False)):
            raise ValueError("Measurement times must strictly increase")

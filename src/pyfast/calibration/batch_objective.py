"""Known-sigma multi-experiment objective using the existing linear batch solver."""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from threading import Lock

import numpy as np
from numpy.typing import ArrayLike

from .._arrays import FloatArray
from ..reactors.batch import simulate_batch
from ..schemas import LDF, BatchConfig, Linear, Observations
from ..solvers import SolverOptions
from ..units import finite_scalar
from .measurements import SignedGaussianMeasurements


@dataclass(frozen=True, slots=True)
class BatchExperiment:
    """One declared experiment with known measurement sigma and SI quantities."""

    config: BatchConfig
    observations: Observations | SignedGaussianMeasurements

    def __post_init__(self) -> None:
        if (not isinstance(self.config, BatchConfig)
                or not isinstance(self.observations, (Observations, SignedGaussianMeasurements))):
            raise ValueError("BatchExperiment requires BatchConfig and supported measurements")
        if (not isinstance(self.config.equilibrium, Linear)
                or not isinstance(self.config.kinetics, LDF)):
            raise ValueError("This objective supports only linear equilibrium and LDF")
        if self.observations.species_name != self.config.species.name:
            raise ValueError("Observation and model species differ")
        if self.observations.std_kg_m3 is None:
            raise ValueError("Known positive measurement standard deviations are required")
        if self.observations.time_s[-1] > self.config.duration_s:
            raise ValueError("Observation times exceed the configured experiment duration")


class LinearBatchObjective:
    """Whitened residual for shared positive K and k across declared independent batches.

    Known c0/q0, mass, volume and fixed common temperature are assumed. This
    callback does not fit nuisance quantities or validate experiment independence.
    """

    parameter_names = ("distribution_m3_kg", "rate_s_inv")
    parameter_units = ("m^3/kg", "1/s")

    def __init__(
        self, experiments: Sequence[BatchExperiment], *, options: SolverOptions | None = None,
        code_revision: str = "uncommitted",
    ) -> None:
        items = tuple(experiments)
        if not items or not all(isinstance(item, BatchExperiment) for item in items):
            raise ValueError("At least one BatchExperiment is required")
        reference = items[0].config
        identities = [item.observations.experiment_id for item in items]
        if len(set(identities)) != len(identities):
            raise ValueError("Experiment IDs must be unique")
        for item in items:
            config = item.config
            if (config.material != reference.material or config.species != reference.species
                    or config.temperature_k != reference.temperature_k):
                raise ValueError("Shared parameters require common material/species/temperature")
        settings = SolverOptions(rtol=1e-9, atol_concentration_kg_m3=1e-13,
                                 atol_loading_kg_kg=1e-14) if options is None else options
        if not isinstance(settings, SolverOptions):
            raise ValueError("options must be SolverOptions")
        if not isinstance(code_revision, str) or (code_revision != "uncommitted"
                and re.fullmatch(r"[0-9a-f]{7,40}", code_revision) is None):
            raise ValueError("code_revision must be a Git hash or uncommitted")
        self._experiments = items
        self._options = settings
        self._code_revision = code_revision
        self._physical_solves = 0
        self._lock = Lock()

    @property
    def experiments(self) -> tuple[BatchExperiment, ...]:
        return self._experiments

    @property
    def physical_solves(self) -> int:
        with self._lock:
            return self._physical_solves

    @property
    def input_hashes(self) -> tuple[tuple[str, str, str], ...]:
        """(experiment ID, original configuration SHA, declared observation source SHA)."""
        return tuple((item.observations.experiment_id, item.config.sha256,
                      item.observations.source_sha256) for item in self._experiments)

    def __call__(self, parameters: ArrayLike) -> FloatArray:
        raw = np.asarray(parameters, dtype=object)
        if raw.ndim != 1 or raw.shape != (2,):
            raise ValueError("Expected [K_m3_kg, k_LDF_s_inv]")
        values = tuple(finite_scalar(value, "parameter") for value in raw)
        if any(value <= 0 for value in values):
            raise ValueError("K and k_LDF must be strictly positive")
        distribution, rate = values
        residuals = []
        for item in self._experiments:
            config = replace(item.config, equilibrium=Linear(distribution_m3_kg=distribution),
                             kinetics=LDF(rate_s_inv=rate))
            observed_times = np.asarray(item.observations.time_s)
            times = np.unique(np.concatenate(([0.0], observed_times, [config.duration_s])))
            with self._lock:
                self._physical_solves += 1
            result = simulate_batch(config, time_s=times, options=self._options,
                                    code_revision=self._code_revision)
            measured = np.asarray(item.observations.concentration_kg_m3)
            sigma = np.asarray(item.observations.std_kg_m3)
            positions = np.searchsorted(times, observed_times)
            residuals.append((result.outlet_concentration_kg_m3[positions] - measured) / sigma)
        return np.concatenate(residuals)

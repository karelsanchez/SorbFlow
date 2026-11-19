"""Reproducible Monte Carlo and finite-difference sensitivity, independent of solvers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from .._arrays import FloatArray, real_array


@dataclass(frozen=True, slots=True, kw_only=True)
class MonteCarloResult:
    """Actual samples and sampling uncertainty; not posterior credibility by itself."""

    inputs_si: FloatArray
    outputs_si: FloatArray
    mean: FloatArray
    standard_deviation: FloatArray
    standard_error_mean: FloatArray
    probabilities: FloatArray
    quantiles: FloatArray
    seed: int
    model_id: str
    samples_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "inputs_si",
            "outputs_si",
            "mean",
            "standard_deviation",
            "standard_error_mean",
            "probabilities",
            "quantiles",
        ):
            array = np.array(getattr(self, name), dtype=np.float64, copy=True)
            array.setflags(write=False)
            object.__setattr__(self, name, array)


def monte_carlo(
    evaluate: Callable[[FloatArray], ArrayLike],
    sampler: Callable[[np.random.Generator, int], ArrayLike],
    *,
    n_samples: int,
    seed: int,
    model_id: str,
    probabilities: ArrayLike = (0.025, 0.5, 0.975),
) -> MonteCarloResult:
    """Propagate sampled parameters in SI without silently rejecting failed cases.

    Sampler returns (n_samples, n_parameters), and may encode correlations or
    non-normal distributions. Each evaluate result is a scalar or a fixed vector.
    Preserve the evaluator/sampler source and model_id separately for reproduction.
    """
    if type(n_samples) is not int or n_samples < 2:
        raise ValueError("n_samples must be an integer >=2")
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("seed must be an unsigned 64-bit integer")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model_id must identify the configured model and sampler")
    p = real_array(probabilities, "probabilities")
    if p.ndim != 1 or not p.size or np.any(p < 0) or np.any(p > 1) or np.any(np.diff(p) <= 0):
        raise ValueError("probabilities must strictly increase within [0,1]")
    inputs = real_array(sampler(np.random.default_rng(seed), n_samples), "samples")
    if inputs.ndim != 2 or inputs.shape[0] != n_samples or inputs.shape[1] == 0:
        raise ValueError("Sampler must return (n_samples, n_parameters)")
    rows: list[FloatArray] = []
    for i, sample in enumerate(inputs):
        try:
            output = np.atleast_1d(real_array(evaluate(sample.copy()), "model output"))
            if output.ndim != 1 or output.size == 0 or (rows and output.shape != rows[0].shape):
                raise ValueError("Model output shape must remain a nonempty vector")
        except Exception as exc:
            raise RuntimeError(
                f"Monte Carlo failed at sample {i}; no samples were discarded"
            ) from exc
        rows.append(output)
    outputs = np.stack(rows)
    std = np.std(outputs, axis=0, ddof=1)
    header = json.dumps(
        {"inputs": inputs.shape, "outputs": outputs.shape, "model_id": model_id}, sort_keys=True
    ).encode()
    digest = hashlib.sha256(
        header + inputs.astype("<f8").tobytes() + outputs.astype("<f8").tobytes()
    ).hexdigest()
    return MonteCarloResult(
        inputs_si=inputs,
        outputs_si=outputs,
        mean=np.mean(outputs, axis=0),
        standard_deviation=std,
        standard_error_mean=std / np.sqrt(n_samples),
        probabilities=p,
        quantiles=np.quantile(outputs, p, axis=0),
        seed=seed,
        model_id=model_id,
        samples_sha256=digest,
    )


def local_sensitivity(
    evaluate: Callable[[FloatArray], ArrayLike],
    point_si: ArrayLike,
    steps_si: ArrayLike,
) -> FloatArray:
    """Central numerical Jacobian (outputs, parameters), with caller-chosen SI steps.

    No clipping or one-sided substitution is applied at physical boundaries.
    Repeat with smaller steps to assess truncation and numerical error.
    """
    point, steps = real_array(point_si, "point_si"), real_array(steps_si, "steps_si")
    if point.ndim != 1 or not point.size or point.shape != steps.shape or np.any(steps <= 0):
        raise ValueError("Matched nonempty point and positive step vectors are required")
    columns: list[FloatArray] = []
    for i, step in enumerate(steps):
        plus, minus = point.copy(), point.copy()
        plus[i] += step
        minus[i] -= step
        a = np.atleast_1d(real_array(evaluate(plus), "model output"))
        b = np.atleast_1d(real_array(evaluate(minus), "model output"))
        if a.ndim != 1 or a.shape != b.shape or (columns and a.shape != columns[0].shape):
            raise ValueError("Model output shape changed during differentiation")
        columns.append((a - b) / (2 * step))
    return np.column_stack(columns)

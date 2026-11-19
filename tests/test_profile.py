"""Analytic method tests, not the confirmatory E02 coverage study."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from pyfast.calibration.profile import ProfileParameter, profile_gaussian_known_sigma


def parameters():
    return (ProfileParameter("x", "m^3/kg", 0.1, 10), ProfileParameter("y", "1/s", 0.1, 10))


def quadratic(theta):
    x, y = theta
    return [(x + y - 5) / 0.1, (y - 2) / 0.2]


def test_analytic_quadratic_reoptimizes_nuisance_and_retains_starts():
    result = profile_gaussian_known_sigma(
        quadratic, parameters(), [[1, 1], [5, 4]], parameter="x", grid=[2, 2.8, 3, 3.2, 4],
    )
    assert result.status == "COMPLETE"
    assert result.baseline_parameters == pytest.approx((3, 2), abs=1e-7)
    assert result.baseline_chi2 == pytest.approx(0, abs=1e-14)
    assert result.cutoff == pytest.approx(3.841458820694124)
    assert len(result.baseline_trials) == 2
    for point in result.points:
        assert len(point.trials) == 2
        assert all(trial.success for trial in point.trials)
        assert point.parameters[1] == pytest.approx(4.4 - 0.8 * point.value)
        assert point.delta_chi2 == pytest.approx(20 * (point.value - 3) ** 2, abs=1e-8)
    assert result.accepted_grid == (2.8, 3, 3.2)
    assert result.edge_status == ("REJECTED", "REJECTED")
    assert result.callback_calls == sum(t.callback_calls for t in result.baseline_trials) + sum(
        t.callback_calls for p in result.points for t in p.trials
    )
    with pytest.raises(FrozenInstanceError):
        result.status = "anything"


def test_ridge_product_does_not_invent_closed_interval():
    specs = (ProfileParameter("x", "1", 1, 6), ProfileParameter("y", "1", 1, 6))
    result = profile_gaussian_known_sigma(
        lambda theta: [(theta[0] * theta[1] - 6) / 0.1],
        specs, [[2, 3], [3, 2]], parameter="x", grid=[1, 2, 3, 6],
    )
    assert result.status == "COMPLETE"
    assert result.accepted_grid == (1, 2, 3, 6)
    assert result.edge_status == ("BOUND_LIMITED", "BOUND_LIMITED")
    assert all(p.delta_chi2 == pytest.approx(0, abs=1e-7) for p in result.points)
    assert not hasattr(result, "confidence_interval")


def test_accepted_grid_truncation_and_nuisance_bounds():
    result = profile_gaussian_known_sigma(
        lambda theta: [theta[1] + 1], parameters(), [[1, 1]],
        parameter="x", grid=[1, 2],
    )
    assert result.edge_status == ("GRID_TRUNCATED", "GRID_TRUNCATED")
    assert all(point.bound_limited for point in result.points)
    assert all("y" in point.trials[0].bound_parameters for point in result.points)


def test_singleton_grid_edges_are_directional():
    result = profile_gaussian_known_sigma(
        lambda theta: [theta[0] - 1], [ProfileParameter("x", "1", 1, 5)], [[2]],
        parameter="x", grid=[1],
    )
    assert result.edge_status == ("BOUND_LIMITED", "GRID_TRUNCATED")


def test_better_profile_marks_inconsistent_baseline_and_never_clips_negative_delta():
    result = profile_gaussian_known_sigma(
        lambda theta: [(theta[0] - 1) ** 2 * (4 - theta[0]) + 1],
        [ProfileParameter("x", "1", 0.1, 6)], [[1]], parameter="x", grid=[1, 4.1],
    )
    assert result.baseline_chi2 == pytest.approx(1)
    assert result.baseline_inconsistent
    assert result.status == "BASELINE_INCONSISTENT"
    assert result.points[1].delta_chi2 < -0.9
    assert all(point.accepted is None for point in result.points)
    assert result.accepted_grid == ()
    assert result.edge_status == ("UNAVAILABLE", "UNAVAILABLE")


def test_real_callback_count_includes_jacobian_and_hard_budget():
    seen = []

    def residual(theta):
        seen.append(tuple(theta))
        assert not theta.flags.writeable
        return quadratic(theta)

    complete = profile_gaussian_known_sigma(
        residual, parameters(), [[1, 1]], parameter="x", grid=[3],
    )
    assert complete.callback_calls == len(seen)
    assert complete.callback_calls > 5  # Finite differences invoke the callback too.
    seen.clear()
    result = profile_gaussian_known_sigma(
        residual, parameters(), [[1, 1], [5, 4]], parameter="x", grid=[2, 3],
        max_callback_calls=3,
    )
    assert result.callback_calls == len(seen) == 3
    assert result.budget_exhausted
    assert result.status == "BUDGET_EXHAUSTED"
    assert result.baseline_trials[0].callback_calls == 3
    assert result.baseline_trials[1].callback_calls == 0
    assert all(t.status == "BUDGET_EXHAUSTED" for t in result.baseline_trials)


def test_partial_profile_preserves_failures_and_valid_points():
    def residual(theta):
        if theta[0] < 0.5:
            raise RuntimeError("outside supported model")
        return [theta[0] - 2]

    result = profile_gaussian_known_sigma(
        residual, [ProfileParameter("x", "1", 0.1, 5)], [[0.2], [3]],
        parameter="x", grid=[0.2, 2, 4],
    )
    assert result.status == "INCOMPLETE"
    assert not result.baseline_trials[0].success
    assert "outside supported model" in result.baseline_trials[0].message
    assert result.baseline_trials[1].success
    assert result.points[0].chi2 is None
    assert all(t.status == "ERROR" for t in result.points[0].trials)
    assert result.accepted_grid == (2,)
    assert result.edge_status == ("UNAVAILABLE", "REJECTED")


def test_budget_exhausted_after_baseline_keeps_partial_grid():
    args = dict(
        weighted_residual=lambda theta: [theta[0] - 2],
        parameters=[ProfileParameter("x", "1", 0.1, 5)], starts=[[2]],
        parameter="x", grid=[1, 2, 3],
    )
    complete = profile_gaussian_known_sigma(**args)
    baseline_calls = sum(t.callback_calls for t in complete.baseline_trials)
    partial = profile_gaussian_known_sigma(**args, max_callback_calls=baseline_calls + 1)
    assert partial.baseline_chi2 == pytest.approx(0)
    assert partial.status == "BUDGET_EXHAUSTED"
    assert partial.accepted_grid == (1,)
    assert partial.points[1].accepted is None
    assert partial.points[1].trials[0].callback_calls == 0
    assert partial.edge_status == ("GRID_TRUNCATED", "UNAVAILABLE")


@pytest.mark.parametrize("bad", [[], [[1]], [np.nan], [np.inf], [1j], [True], [1e308]])
def test_invalid_residuals_are_retained_as_failures(bad):
    result = profile_gaussian_known_sigma(
        lambda theta: bad, [ProfileParameter("x", "1", 0.1, 5)], [[1]],
        parameter="x", grid=[1, 2],
    )
    assert result.status == "BASELINE_FAILED"
    assert result.callback_calls == 1
    assert result.baseline_trials[0].status == "ERROR"
    assert all(p.accepted is None and not p.trials for p in result.points)


def test_residual_length_changes_are_not_silently_accepted():
    calls = 0

    def residual(theta):
        nonlocal calls
        calls += 1
        return [1] if calls == 1 else [1, 2]

    result = profile_gaussian_known_sigma(
        residual, [ProfileParameter("x", "1", 0.1, 5)], [[1]], parameter="x", grid=[1],
    )
    assert result.status == "BASELINE_FAILED"
    assert "length changed" in result.baseline_trials[0].message


def test_optimizer_nonconvergence_is_not_an_optimum():
    result = profile_gaussian_known_sigma(
        quadratic, parameters(), [[1, 1]], parameter="x", grid=[3], max_nfev=1,
    )
    assert result.status == "BASELINE_FAILED"
    assert result.baseline_trials[0].status == "OPTIMIZER_FAILED"
    assert result.baseline_trials[0].chi2 is not None
    assert result.baseline_chi2 is None


@pytest.mark.parametrize("kwargs", [
    {"starts": [1, 1]}, {"starts": []}, {"starts": [[0, 1]]},
    {"starts": [[11, 1]]}, {"starts": [[1, np.nan]]}, {"starts": [[True, False]]},
    {"grid": []}, {"grid": [[1]]}, {"grid": [2, 1]}, {"grid": [1, 1]},
    {"grid": [0]}, {"grid": [11]}, {"grid": [np.inf]},
    {"parameter": "absent"}, {"confidence": 1}, {"confidence": 0},
    {"confidence": True}, {"baseline_tolerance": -1}, {"baseline_tolerance": np.nan},
    {"max_nfev": 0}, {"max_nfev": True},
    {"max_callback_calls": 0}, {"max_callback_calls": 1.5},
    {"parameters": []}, {"parameters": ["not a parameter"]},
    {"parameters": [ProfileParameter("x", "1", 0.1, 10)] * 2},
    {"weighted_residual": None},
])
def test_invalid_inputs_rejected_before_callback(kwargs):
    def forbidden(theta):
        raise AssertionError("Configuration validation must precede callbacks")

    arguments = dict(weighted_residual=forbidden, parameters=parameters(), starts=[[1, 1]],
                     parameter="x", grid=[1, 2])
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        profile_gaussian_known_sigma(**arguments)


@pytest.mark.parametrize("name,unit,lower,upper", [
    ("", "1", 1, 2), ("x", "", 1, 2), ("x", "nonsense_unit", 1, 2),
    ("x", "1", 0, 2), ("x", "1", 2, 1), ("x", "1", 1, 1),
    ("x", "1", np.nan, 2), ("x", "1", 1, np.inf), ("x", "1", True, 2),
])
def test_invalid_parameter_metadata(name, unit, lower, upper):
    with pytest.raises(ValueError):
        ProfileParameter(name, unit, lower, upper)

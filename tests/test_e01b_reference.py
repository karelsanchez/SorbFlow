"""Independent eigenfunction checks without executing the full E01-B FV matrix."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad

FOLDER = Path(__file__).resolve().parents[1] / "benchmarks/e01b"
SPEC = importlib.util.spec_from_file_location("reference", FOLDER / "reference.py")
assert SPEC is not None and SPEC.loader is not None
reference = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reference
SPEC.loader.exec_module(reference)
RUN_SPEC = importlib.util.spec_from_file_location("e01b_run", FOLDER / "run.py")
assert RUN_SPEC is not None and RUN_SPEC.loader is not None
run = importlib.util.module_from_spec(RUN_SPEC)
RUN_SPEC.loader.exec_module(run)


@pytest.mark.parametrize("pe", [2.0, 10.0])
def test_positive_roots_both_robin_conditions_and_projection(pe):
    ref = reference.ADEReference(pe, 16)
    roots, h = ref.roots, ref.h
    assert np.all(roots > np.arange(16) * np.pi)
    assert np.all(roots < (np.arange(16) + 1) * np.pi)
    left_f, left_df = np.ones(16), np.full(16, h)
    np.testing.assert_allclose(left_df - h * left_f, 0.0, atol=1e-14)
    right_f = np.cos(roots) + h / roots * np.sin(roots)
    right_df = -roots * np.sin(roots) + h * np.cos(roots)
    np.testing.assert_allclose(right_df + h * right_f, 0.0, atol=2e-12)
    checks = ref.checks([0.1, 0.5, 1.0, 3.0])
    assert checks["projection_quad_scaled"] < 1e-12
    assert checks["reference_mass_identity"] < 1e-12


def test_modes_are_orthogonal():
    ref = reference.ADEReference(10.0, 8)
    roots = ref.roots
    for i, j in ((0, 1), (1, 3), (3, 7)):

        def f(k, x):
            return np.cos(k * x) + ref.h / k * np.sin(k * x)

        value = quad(lambda x, i=i, j=j: f(roots[i], x) * f(roots[j], x), 0, 1, epsabs=1e-12)[0]
        assert abs(value) < 1e-12


@pytest.mark.parametrize("pe", [2.0, 10.0])
def test_continuous_pde_with_independent_finite_differences(pe):
    ref = reference.ADEReference(pe, 64)
    step = 1e-4
    for x, theta in ((0.2, 0.4), (0.7, 0.8)):
        center = ref.points([x], [theta])[0, 0]
        left, right = ref.points([x - step, x + step], [theta])[0]
        before, after = ref.points([x], [theta - step, theta + step])[:, 0]
        dt = (after - before) / (2 * step)
        dx = (right - left) / (2 * step)
        dxx = (right - 2 * center + left) / step**2
        assert dt == pytest.approx(dxx / pe - dx, abs=3e-7)


@pytest.mark.parametrize("pe", [2.0, 10.0])
def test_cell_average_matches_independent_quadrature_and_partition(pe):
    ref = reference.ADEReference(pe, 32)
    times = np.array([0.1, 0.5, 1.0])
    edges = np.array([0.0, 0.03, 0.2, 0.8, 1.0])
    means = ref.averages(edges, times)
    for t_index, t in enumerate(times):
        for i, (left, right) in enumerate(zip(edges, edges[1:], strict=False)):
            integrated = quad(lambda x, t=t: ref.points([x], [t])[0, 0], left, right, epsabs=1e-11)[
                0
            ] / (right - left)
            assert means[t_index, i] == pytest.approx(integrated, abs=2e-12)
    np.testing.assert_allclose(
        means @ np.diff(edges), ref.averages([0, 1], times)[:, 0], atol=2e-13
    )


def test_truncation_equilibrium_and_bounds():
    x, times = np.linspace(0, 1, 11), np.array([0.1, 0.5, 1.0, 3.0])
    for pe in (2.0, 10.0):
        fine = reference.ADEReference(pe, 128)
        values = fine.points(x, times)
        np.testing.assert_allclose(
            values, reference.ADEReference(pe, 64).points(x, times), atol=1e-13
        )
        assert values.min() >= -1e-12 and values.max() <= 1 + 1e-12
        np.testing.assert_allclose(fine.points(x, [30]), 1.0, atol=1e-12)


@pytest.mark.parametrize(
    "pe,modes", [(True, 64), (0.0, 64), (np.inf, 64), (51.0, 64), (2.0, True), (2.0, 1)]
)
def test_reference_rejects_invalid_parameters(pe, modes):
    with pytest.raises(ValueError):
        reference.ADEReference(pe, modes)


def test_reference_rejects_invalid_observation_domain():
    ref = reference.ADEReference(2.0)
    for x, t in (([0, 1], [0]), ([1.1], [0.1]), ([0], [np.nan])):
        with pytest.raises(ValueError):
            ref.points(x, t)
    with pytest.raises(ValueError):
        ref.averages([0, 0.5, 0.5, 1], [0.1])


def test_protocol_and_corruption():
    p = json.loads((FOLDER / "protocol.json").read_text())
    run.validate(p)
    for key, value in (
        ("peclet", [2.0, 2.0]),
        ("reference_modes", [8, 16]),
        ("full_e01_complete", True),
        ("sample_theta_start", 0.0),
    ):
        broken = dict(p)
        broken[key] = value
        with pytest.raises(ValueError):
            run.validate(broken)


def test_failed_case_is_kept_and_does_not_stop_later_case():
    p = json.loads((FOLDER / "protocol.json").read_text())
    study = run.Study(p)

    def bad(case):
        raise RuntimeError("reference unavailable")

    study.execute("bad", bad)
    study.execute("fail", lambda case: study.check(case, "known", 2.0, 1.0))
    study.execute("pass", lambda case: study.check(case, "known", 0.0, 1.0))
    assert [x["status"] for x in study.cases] == ["INCONCLUSIVE", "FAIL", "PASS"]

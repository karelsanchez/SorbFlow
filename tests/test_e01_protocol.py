"""Small reference/protocol checks; the full preregistered matrix is a separate run."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from scipy.special import gammainc

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("e01_run", ROOT / "benchmarks/e01/run.py")
assert SPEC is not None and SPEC.loader is not None
e01 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e01)


@pytest.fixture
def protocol():
    return json.loads((ROOT / "benchmarks/e01/protocol.json").read_text())


def test_frozen_protocol_is_consistent(protocol):
    e01.validate_protocol(protocol)


@pytest.mark.parametrize(
    "change",
    [
        "unknown",
        "boolean_number",
        "duplicate_mesh",
        "dirty_tracer",
        "equilibrium",
        "series",
        "scope",
    ],
)
def test_inconsistent_protocol_rejected(protocol, change):
    p = deepcopy(protocol)
    if change == "unknown":
        p["batch"]["criteria"]["typo_threshold"] = 1
    elif change == "boolean_number":
        p["batch"]["rate_s_inv"] = True
    elif change == "duplicate_mesh":
        p["sphere"]["radial_cells"][-1] = 40
    elif change == "dirty_tracer":
        p["tracer"]["distribution_m3_kg"] = 0.1
    elif change == "equilibrium":
        p["batch"]["initial_states"][2]["loading_kg_kg"] = 0.006
    elif change == "series":
        p["sphere"]["series_terms"] = 1
    elif change == "scope":
        p["experimental_validation"] = True
    with pytest.raises(ValueError):
        e01.validate_protocol(p)


def test_batch_exact_preserves_mass_and_initial_state(protocol):
    b = protocol["batch"]
    for state in b["initial_states"]:
        times = np.array([0.0, 10.0, 300.0])
        c, q = e01.batch_exact(b, state, times)
        assert c[0] == pytest.approx(state["concentration_kg_m3"])
        assert q[0] == pytest.approx(state["loading_kg_kg"])
        mass = b["liquid_volume_m3"] * c + b["adsorbent_mass_kg"] * q
        np.testing.assert_allclose(mass, mass[0], rtol=1e-14, atol=1e-20)
        if state["state_id"] in ("equilibrium", "empty"):
            np.testing.assert_allclose(c, c[0], rtol=1e-14, atol=1e-18)


def test_rms_and_tanks_reference_normalization():
    assert e01.scaled_rms(np.array([0.0, 4.0]), np.zeros(2), 2) == pytest.approx(np.sqrt(2))
    times = np.array([0.0, 1.0, 4.0])
    np.testing.assert_allclose(gammainc(1, times), 1 - np.exp(-times), atol=1e-15)


def test_independent_affine_matrix_has_correct_total_mass_derivative(protocol):
    p = protocol["matrix_ldf"]
    matrix, _ = e01.affine_matrix(p)
    bed, n = p["bed"], p["axial_cells"]
    cellvolume = np.pi * bed["diameter_m"] ** 2 / 4 * bed["length_m"] / n
    weights = np.r_[
        np.full(n, bed["porosity"] * cellvolume),
        np.full(n, (1 - bed["porosity"]) * bed["particle_density_kg_m3"] * cellvolume),
        0.0,
    ]
    expected = np.zeros(2 * n + 1)
    expected[n - 1] = -p["flow_m3_s"]
    expected[-1] = p["flow_m3_s"] * p["inlet_concentration_kg_m3"]
    np.testing.assert_allclose(weights @ matrix, expected, atol=1e-20, rtol=1e-13)


def test_failure_is_recorded_and_later_case_runs(protocol):
    study = e01.Study(protocol)

    def broken(case):
        raise RuntimeError("deliberate test failure")

    study.execute("failed", broken)
    study.execute("criterion_failed", lambda case: study.check(case, "known", 2.0, 1.0))
    study.execute("passed", lambda case: study.check(case, "known", 1.0, 1.0))
    assert [x["status"] for x in study.cases] == ["ERROR", "FAIL", "PASS"]
    assert study.cases[0]["error"] == "deliberate test failure"


def test_existing_output_and_source_output_are_refused(protocol, tmp_path):
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol))
    for output in (tmp_path, ROOT / "benchmarks/e01/never_created"):
        with pytest.raises(SystemExit) as exc:
            e01.main(["--protocol", str(path), "--output", str(output)])
        assert exc.value.code == 2

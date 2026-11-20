"""Execution-kit data identities and immutable-artifact safety."""
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location(
    "e02_execution_kit", Path(__file__).resolve().parents[1] / "examples/e02_execution_kit.py")
assert SPEC is not None and SPEC.loader is not None
KIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(KIT)


def test_generator_isolated_identity_and_no_modification_of_noise():
    table = {"time_sets": {"short": {"value_s": [0, 2, 10]}}}
    scenario = dict(id="one", scenario_index=1, times="short",
                    truth={"K_m3_kg": .5, "k_s_inv": .02})
    first = KIT.dataset(scenario, table)
    KIT.dataset(dict(scenario, id="other", scenario_index=2), table)
    assert KIT.encoded(first) == KIT.encoded(KIT.dataset(scenario, table))
    for batch in first["batches"]:
        for y, c, z in zip(batch["y"], batch["truth"], batch["z"], strict=True):
            assert y == c + first["sigma_kg_m3"] * z
    assert first["batches"][0]["z"] != first["batches"][1]["z"]


def test_immutable_file_rejects_changed_content(tmp_path):
    target = tmp_path / "data.json"
    KIT.immutable(target, {"value": -1})
    KIT.immutable(target, {"value": -1})
    with pytest.raises(ValueError, match="mismatch"):
        KIT.immutable(target, {"value": 1})
    assert json.loads(target.read_bytes()) == {"value": -1}


def test_atomic_file_is_parseable_and_replaces_previous_state(tmp_path):
    target = tmp_path / "record.json"
    KIT.atomic(target, {"status": "RUNNING"})
    KIT.atomic(target, {"status": "FINALIZED"})
    assert json.loads(target.read_bytes()) == {"status": "FINALIZED"}
    assert not target.with_suffix(".json.tmp").exists()


@pytest.fixture
def prepared_run(tmp_path, monkeypatch):
    table = dict(time_sets={"short": {"value_s": [0., 1.], "duration_s": 1.}},
                 bounds_sets={"box": {"K_m3_kg": [.1, 2.], "k_s_inv": [.005, .08]}},
                 scenarios=[dict(id=f"S{i}", scenario_index=i, times="short", bounds="box",
                                 truth={"K_m3_kg": .5, "k_s_inv": .02}) for i in range(7)])
    table_path = tmp_path / "table.json"
    table_path.write_bytes(KIT.encoded(table))
    output = tmp_path / "run"
    calls = []

    class Objective:
        def __init__(self, experiments):
            self.physical_solves = 0

        def __call__(self, theta):
            self.physical_solves += 2
            return np.zeros(4)

    @dataclass
    class Profile:
        status: str = "COMPLETE"

    def profile(callback, specs, starts, **kwargs):
        calls.append(kwargs["max_callback_calls"])
        callback(np.array([.5, .02]))
        return Profile()

    monkeypatch.setattr(KIT, "LinearBatchObjective", Objective)
    monkeypatch.setattr(KIT, "profile_gaussian_known_sigma", profile)
    KIT.run(table_path, output)
    assert calls == [250] * 14
    return table_path, output


def test_resume_completed_records_never_calls_optimizer_or_solver(prepared_run, monkeypatch):
    table, output = prepared_run
    before = {p.name: p.read_bytes() for p in output.glob("*_record.json")}

    def forbidden(*args, **kwargs):
        raise AssertionError("Completed records must not invoke numerical work")

    monkeypatch.setattr(KIT, "LinearBatchObjective", forbidden)
    monkeypatch.setattr(KIT, "profile_gaussian_known_sigma", forbidden)
    KIT.run(table, output)
    assert before == {p.name: p.read_bytes() for p in output.glob("*_record.json")}


def test_resume_rejects_changed_dataset_before_optimizer(prepared_run, monkeypatch):
    table, output = prepared_run
    data_path = output / "S0_data.json"
    data = json.loads(data_path.read_bytes())
    data["batches"][0]["y"][0] = -123.
    data_path.write_bytes(KIT.encoded(data))

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed immutable data must fail before numerical work")

    monkeypatch.setattr(KIT, "profile_gaussian_known_sigma", forbidden)
    with pytest.raises(ValueError, match="Immutable artifact mismatch"):
        KIT.run(table, output)
    assert json.loads(data_path.read_bytes())["batches"][0]["y"][0] == -123.


def test_resume_exhausted_interruption_does_not_reset_budget(prepared_run, monkeypatch):
    table, output = prepared_run
    record_path = output / "S0_record.json"
    record = json.loads(record_path.read_bytes())
    record["status"] = "RUNNING"
    progress = record["profiles"]["K"]
    progress.update(status="RUNNING", callback_calls=250, physical_solves=500)
    KIT.atomic(record_path, record)

    def forbidden(*args, **kwargs):
        raise AssertionError("No remaining budget means no new objective or optimizer")

    monkeypatch.setattr(KIT, "LinearBatchObjective", forbidden)
    monkeypatch.setattr(KIT, "profile_gaussian_known_sigma", forbidden)
    KIT.run(table, output)
    finished = json.loads(record_path.read_bytes())
    assert finished["status"] == "FINALIZED"
    resumed = finished["profiles"]["K"]
    assert resumed["status"] == "BUDGET_EXHAUSTED_AFTER_INTERRUPTION"
    assert resumed["callback_calls"] == 250
    assert resumed["physical_solves"] == 500
    assert resumed["interruptions"] == 1

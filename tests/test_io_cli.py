import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from sorbflow import LDF, BatchConfig, Linear, Species
from sorbflow.cli import main
from sorbflow.io import export_result
from sorbflow.simulate import batch
from sorbflow.solvers import SimulationError, SolverOptions
from sorbflow.solvers.integration import IntegrationOutput
from sorbflow.solvers.results import check_physics
from sorbflow.validate import mass_balance


@pytest.fixture
def problem():
    return BatchConfig(
        species=Species(name="independent-species"),
        material="independent-material",
        liquid_volume_m3=0.001,
        adsorbent_mass_kg=0.002,
        duration_s=20,
        initial_concentration_kg_m3=0.01,
        initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=0.5),
        kinetics=LDF(rate_s_inv=0.02),
    )


def test_export_complete_json_csv_and_hashes_without_overwrite(problem, tmp_path):
    result = batch(problem, time_s=[0, 10, 20])
    path = export_result(result, tmp_path / "run")
    doc = json.loads((path / "result.json").read_text())
    assert doc["config"]["species"]["name"] == "independent-species"
    assert np.shape(doc["concentration_kg_m3"]) == (3, 1)
    assert doc["numerical_sha256"] == result.numerical_sha256
    assert "outlet_concentration_kg_m3" in (path / "timeseries.csv").read_text()
    hashes = json.loads((path / "files.sha256.json").read_text())
    assert all(
        hashlib.sha256((path / name).read_bytes()).hexdigest() == h for name, h in hashes.items()
    )
    with pytest.raises(FileExistsError):
        export_result(result, path)


def test_cli_batch_success_and_failures(problem, tmp_path, capsys):
    config = tmp_path / "batch.json"
    config.write_text(problem.to_json())
    assert main(["batch", str(config), "--output", str(tmp_path / "out"), "--samples", "3"]) == 0
    assert "experimental validation" in capsys.readouterr().out
    assert main(["batch", str(config), "--output", str(tmp_path / "out")]) == 2
    assert "already exists" in capsys.readouterr().err
    assert main(["batch", str(config), "--output", str(tmp_path / "new"), "--samples", "1"]) == 2
    config.write_text('{"bad": 1}')
    assert main(["batch", str(config), "--output", str(tmp_path / "bad")]) == 2
    assert not (tmp_path / "bad").exists()


def test_cli_column(config, tmp_path):
    config = replace(config, equilibrium=Linear(distribution_m3_kg=0))
    path = tmp_path / "column.json"
    path.write_text(config.to_json())
    assert (
        main(
            [
                "column",
                str(path),
                "--output",
                str(tmp_path / "col"),
                "--cells",
                "10",
                "--samples",
                "3",
            ]
        )
        == 0
    )
    doc = json.loads((tmp_path / "col" / "result.json").read_text())
    assert np.shape(doc["concentration_kg_m3"]) == (3, 10)


@pytest.mark.parametrize("failure", ["negative-liquid", "negative-solid", "mass"])
def test_physical_failure_is_rejected_and_not_repaired(failure):
    c = np.array([-1.0 if failure == "negative-liquid" else 0])
    q = np.array([-1.0 if failure == "negative-solid" else 0])
    mass = np.array([1.0 if failure == "mass" else 0])
    zero = np.zeros(1)
    integrated = IntegrationOutput(zero[None], zero[None], 0, 0, 0, 0)
    with pytest.raises(SimulationError):
        check_physics(c, q, mass, zero, zero, 0, SolverOptions(), integrated)


def test_independent_mass_report_detects_corruption(problem):
    result = batch(problem)
    corrupt = replace(result, inventory_kg=result.inventory_kg + np.linspace(0, 1, 201))
    assert not mass_balance(corrupt).passed


@pytest.mark.parametrize("mode", ["incomplete", "nonfinite"])
def test_integrator_status_and_finiteness(problem, monkeypatch, mode):
    def broken(*args, **kwargs):
        if mode == "incomplete":
            return SimpleNamespace(success=False, sol=None, message="forced incomplete")
        return SimpleNamespace(
            success=True, sol=lambda t: np.full((2, len(t)), np.nan), y=np.zeros((2, 2))
        )

    monkeypatch.setattr("sorbflow.solvers.integration.solve_ivp", broken)
    with pytest.raises(SimulationError):
        batch(problem)

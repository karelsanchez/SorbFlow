"""Bounded seven-dataset integration check; no coverage or validation claim.

Run with --table SCENARIO_TABLE.json --output NEW_DIRECTORY. Re-running with
identical inputs resumes terminal records and remaining budgets, not SciPy state.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from pyfast import LDF, BatchConfig, Linear, Species
from pyfast.calibration.batch_objective import BatchExperiment, LinearBatchObjective
from pyfast.calibration.measurements import SignedGaussianMeasurements
from pyfast.calibration.profile import ProfileParameter, profile_gaussian_known_sigma

ROOT_SEED = 20261120
CAP = 250


def encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded(value))
    temporary.replace(path)


def immutable(path: Path, value: Any) -> None:
    raw = encoded(value)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f"Immutable artifact mismatch: {path}")
    else:
        path.write_bytes(raw)


def analytic(K: float, k: float, beta: float, times: np.ndarray) -> np.ndarray:
    ceq = .01 / (1 + beta * K)
    return ceq + (.01 - ceq) * np.exp(-k * (1 + beta * K) * times)


def dataset(scenario: dict[str, Any], table: dict[str, Any]) -> dict[str, Any]:
    times = np.array(table["time_sets"][scenario["times"]]["value_s"], dtype=float)
    K, k = scenario["truth"]["K_m3_kg"], scenario["truth"]["k_s_inv"]
    batches = []
    for stream, mass in enumerate((.002, .004)):
        key = (scenario["scenario_index"], 0, stream)
        rng = np.random.default_rng(np.random.SeedSequence(ROOT_SEED, spawn_key=key))
        z = rng.standard_normal(len(times))
        truth = analytic(K, k, mass / .001, times)
        batches.append(dict(mass_kg=mass, time_s=times.tolist(), truth=truth.tolist(),
                            z=z.tolist(), y=(truth + 1e-4 * z).tolist(), spawn_key=key))
    return dict(scenario=scenario["id"], seed=ROOT_SEED, replicate=0,
                sigma_kg_m3=1e-4, truth_parameters=[K, k], batches=batches)


def run(table_path: Path, output: Path) -> None:
    if any(p.casefold() in {"src", ".git", ".venv", "datasets_benchmark_pyfast"}
           for p in output.resolve().parts):
        raise ValueError("Output must be outside protected folders")
    table_raw = table_path.read_bytes()
    table = json.loads(table_raw)
    scenarios = table["scenarios"]
    if len(scenarios) != 7 or len({s["id"] for s in scenarios}) != 7:
        raise ValueError("Exactly seven uniquely named scenarios are required")
    root = Path(__file__).resolve().parents[1]
    files = {p.relative_to(root).as_posix(): sha(p.read_bytes())
             for p in sorted((root / "src/pyfast").rglob("*.py"))}
    specification = dict(study="seven_dataset_integration_not_coverage_or_pilot",
        table_sha256=sha(table_raw), source_sha256=files,
        runner_sha256=sha(Path(__file__).read_bytes()), seed=ROOT_SEED,
        max_callbacks_per_profile=CAP, max_nfev=60, total_callback_cap=3500,
        total_physical_solve_cap=7000, baseline_tolerance=1e-6,
        tolerance_status="provisional_not_inferentially_validated",
        starts_rule="two log-interior diagonal points at fractions 1/3 and 2/3",
        python=sys.version, platform=platform.platform(),
        versions={p: importlib.metadata.version(p) for p in ("numpy", "scipy", "pint")})
    output.mkdir(parents=True, exist_ok=True)
    if not (output / "specification.json").exists() and any(output.iterdir()):
        raise ValueError("New output directory must be empty")
    immutable(output / "specification.json", specification)
    # All noisy data are materialized before the first numerical solve.
    for scenario in scenarios:
        immutable(output / f"{scenario['id']}_data.json", dataset(scenario, table))
    for scenario in scenarios:
        identity = scenario["id"]
        data_path = output / f"{identity}_data.json"
        data = json.loads(data_path.read_bytes())
        record_path = output / f"{identity}_record.json"
        record = (json.loads(record_path.read_bytes()) if record_path.exists() else
                  dict(scenario=identity, specification_sha256=sha(encoded(specification)),
                       data_sha256=sha(data_path.read_bytes()), status="RUNNING", profiles={}))
        if (record["specification_sha256"] != sha(encoded(specification))
                or record["data_sha256"] != sha(data_path.read_bytes())):
            raise ValueError("Record provenance mismatch")
        if record["status"] == "FINALIZED":
            continue
        bounds = table["bounds_sets"][scenario["bounds"]]
        specs = [ProfileParameter("K", "m^3/kg", *bounds["K_m3_kg"]),
                 ProfileParameter("k", "1/s", *bounds["k_s_inv"])]
        lo, hi = np.log([s.lower for s in specs]), np.log([s.upper for s in specs])
        starts = np.exp([lo + (hi - lo) / 3, lo + 2 * (hi - lo) / 3])
        experiments = []
        for index, batch in enumerate(data["batches"]):
            config = BatchConfig(species=Species(name="synthetic-solute"), material="generic",
                liquid_volume_m3=.001, adsorbent_mass_kg=batch["mass_kg"],
                duration_s=table["time_sets"][scenario["times"]]["duration_s"],
                initial_concentration_kg_m3=.01, initial_loading_kg_kg=0,
                equilibrium=Linear(distribution_m3_kg=data["truth_parameters"][0]),
                kinetics=LDF(rate_s_inv=data["truth_parameters"][1]))
            obs = SignedGaussianMeasurements(experiment_id=f"{identity}-{index}",
                species_name="synthetic-solute", time_s=tuple(batch["time_s"]),
                concentration_kg_m3=tuple(batch["y"]),
                std_kg_m3=(1e-4,) * len(batch["y"]), source_sha256=sha(data_path.read_bytes()))
            experiments.append(BatchExperiment(config, obs))
        for index, spec in enumerate(specs):
            progress = record["profiles"].setdefault(spec.name,
                dict(status="RUNNING", callback_calls=0, physical_solves=0, interruptions=0))
            if progress["status"] != "RUNNING":
                continue
            if progress["callback_calls"]:
                progress["interruptions"] += 1
            remaining = CAP - progress["callback_calls"]
            atomic(record_path, record)
            if remaining <= 0:
                progress["status"] = "BUDGET_EXHAUSTED_AFTER_INTERRUPTION"
                atomic(record_path, record)
                continue
            objective = LinearBatchObjective(experiments)
            def callback(theta, progress=progress, record_path=record_path,
                         record=record, objective=objective, data=data):
                progress["callback_calls"] += 1
                # Reserve both solves before entering the solver. Interrupted callbacks
                # consume reservations, so recovery cannot exceed the physical cap.
                progress["physical_solves"] += 2
                atomic(record_path, record)
                residual = objective(theta)
                exact = np.concatenate([
                    (analytic(theta[0], theta[1], b["mass_kg"] / .001,
                              np.array(b["time_s"])) - b["y"]) / 1e-4
                    for b in data["batches"]])
                error = float(np.max(np.abs(residual - exact)))
                progress["predictor_error_max_in_sigma_on_evaluations"] = max(
                    progress.get("predictor_error_max_in_sigma_on_evaluations", 0), error)
                return residual

            started = time.perf_counter()
            try:
                profile = profile_gaussian_known_sigma(callback, specs, starts,
                    parameter=spec.name, grid=[data["truth_parameters"][index]],
                    max_callback_calls=remaining, max_nfev=60)
                progress.update(status=profile.status, profile=asdict(profile))
            except Exception as exc:
                progress.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
            progress.update(elapsed_seconds=time.perf_counter() - started,
                actual_solves_this_attempt=objective.physical_solves,
                physical_solves_semantics="conservative reservations including interrupted calls")
            atomic(record_path, record)
        record["status"] = "FINALIZED"
        atomic(record_path, record)
        print(identity, {k: v["status"] for k, v in record["profiles"].items()}, flush=True)
    records = [json.loads((output / f"{s['id']}_record.json").read_bytes()) for s in scenarios]
    callbacks = sum(p["callback_calls"] for r in records for p in r["profiles"].values())
    solves = sum(p["physical_solves"] for r in records for p in r["profiles"].values())
    assert callbacks <= 3500 and solves <= 7000
    atomic(output / "summary.json", dict(study=specification["study"], terminal_records=7,
        callback_calls=callbacks, physical_solve_reservations=solves,
        statistical_coverage_estimated=False, scientific_validation=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.table, args.output)

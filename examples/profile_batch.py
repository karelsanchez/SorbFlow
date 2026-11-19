"""One synthetic engineering demo, not the E02 identifiability/coverage study."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from pyfast import LDF, BatchConfig, Linear, Observations, Species
from pyfast.calibration.batch_objective import BatchExperiment, LinearBatchObjective
from pyfast.calibration.profile import ProfileParameter, profile_gaussian_known_sigma
from pyfast.solvers import SolverOptions


def main(output: Path) -> None:
    if any(part.casefold() in {"datasets_benchmark_pyfast", ".git", ".venv", "src"}
           for part in output.absolute().parts):
        raise ValueError("Choose a new run directory outside source/data/protected folders")
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              text=True, check=False)
    base_revision = revision.stdout.strip() if revision.returncode == 0 else None
    state = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True,
                           text=True, check=False)
    dirty = state.returncode != 0 or bool(state.stdout.strip())
    code_revision = base_revision if base_revision is not None and not dirty else "uncommitted"
    source_hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted((root / "src/pyfast").rglob("*.py"))}
    demo_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    source_hashes["examples/profile_batch.py"] = demo_sha
    seed, sigma = 20261119, 1e-4
    rng = np.random.default_rng(seed)
    times = np.array([0, 10, 30, 60, 120, 300], dtype=float)
    experiments = []
    for index, mass in enumerate((0.002, 0.004)):
        config = BatchConfig(species=Species(name="synthetic-solute"), material="generic",
                             liquid_volume_m3=0.001, adsorbent_mass_kg=mass, duration_s=300,
                             initial_concentration_kg_m3=0.01, initial_loading_kg_kg=0,
                             equilibrium=Linear(distribution_m3_kg=0.5),
                             kinetics=LDF(rate_s_inv=0.02))
        beta = mass / config.liquid_volume_m3
        ceq = 0.01 / (1 + beta * 0.5)
        truth = ceq + (0.01 - ceq) * np.exp(-0.02 * (1 + beta * 0.5) * times)
        observed = truth + rng.normal(0, sigma, times.size)
        if np.any(observed < 0):
            raise ValueError("Signed noisy data require another observation schema; never clip")
        data = {"kind": "synthetic_analytic_linear_batch", "seed": seed,
                "experiment_id": f"synthetic-{index}", "time_s": times.tolist(),
                "concentration_kg_m3": observed.tolist(), "sigma_kg_m3": sigma,
                "config_json": config.to_json(), "truth_parameters": [0.5, 0.02]}
        raw = (json.dumps(data, sort_keys=True, indent=2) + "\n").encode()
        (output / f"data_{index}.json").write_bytes(raw)
        observations = Observations(experiment_id=f"synthetic-{index}",
                                    species_name="synthetic-solute", time_s=tuple(times),
                                    concentration_kg_m3=tuple(observed),
                                    std_kg_m3=(sigma,) * times.size,
                                    source_sha256=hashlib.sha256(raw).hexdigest())
        experiments.append(BatchExperiment(config, observations))
    parameters = (ProfileParameter("distribution_m3_kg", "m^3/kg", 0.1, 2),
                  ProfileParameter("rate_s_inv", "1/s", 0.005, 0.08))
    starts, grid = [[0.25, 0.01], [1.0, 0.04]], [0.4, 0.5, 0.6]
    options = SolverOptions(rtol=1e-9, atol_concentration_kg_m3=1e-13,
                            atol_loading_kg_kg=1e-14)
    specification = {"study": "engineering_demo_not_E02_confirmation", "seed": seed,
                     "parameters": [asdict(parameter) for parameter in parameters],
                     "starts": starts, "grid": grid, "known_sigma_kg_m3": sigma,
                     "max_callback_calls": 1200, "confidence": 0.95,
                     "truth_generator": "closed-form linear batch, independent of numerical solver",
                     "python": sys.version, "code_revision": code_revision,
                     "git_base_revision": base_revision, "worktree_dirty": dirty,
                     "source_sha256": source_hashes, "solver_options": asdict(options),
                     "packages": {name: importlib.metadata.version(name)
                                  for name in ("numpy", "scipy", "pint", "pyfast-adsorption")}}
    (output / "specification.json").write_text(json.dumps(specification, indent=2) + "\n")
    objective = LinearBatchObjective(experiments, options=options, code_revision=code_revision)
    profile = profile_gaussian_known_sigma(objective, parameters, starts,
                                          parameter="distribution_m3_kg", grid=grid,
                                          max_callback_calls=1200)
    assert objective.physical_solves == 2 * profile.callback_calls
    report = {"study": specification["study"], "profile": asdict(profile),
              "physical_solves": objective.physical_solves,
              "input_hashes": objective.input_hashes,
              "experimental_validation": False, "coverage_study_completed": False,
              "continuous_confidence_interval_estimated": False}
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": profile.status, "callback_calls": profile.callback_calls,
                      "physical_solves": objective.physical_solves,
                      "baseline_parameters": profile.baseline_parameters,
                      "accepted_grid": profile.accepted_grid}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args().output)

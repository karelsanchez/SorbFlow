"""Execute the frozen, scoped E01-A references; never experimental validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp, trapezoid
from scipy.linalg import expm
from scipy.special import gammainc

import pyfast
from pyfast import LDF, BatchConfig, Bed, Linear, Operation, SimulationConfig, Species
from pyfast.kinetics.sphere import SphereGrid, diffusion_rhs
from pyfast.simulate import batch, column
from pyfast.solvers import SolverOptions

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "e60dba9"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_protocol(p: dict) -> None:
    """Reject incomplete/unknown fields and physically inconsistent reference cases.

    The shipped protocol defines the schema; numeric values may be changed only in
    a separately frozen protocol, whose exact bytes are retained by every run.
    """
    template = json.loads(Path(__file__).with_name("protocol.json").read_text())

    def shape(value, reference, path):
        if isinstance(reference, dict):
            if not isinstance(value, dict) or value.keys() != reference.keys():
                raise ValueError(f"Unknown/missing fields at {path}")
            for key in reference:
                shape(value[key], reference[key], f"{path}.{key}")
        elif isinstance(reference, list):
            if not isinstance(value, list) or not value:
                raise ValueError(f"Nonempty list required: {path}")
            for item in value:
                shape(item, reference[0], path)
        elif isinstance(reference, bool):
            if type(value) is not bool or value != reference:
                raise ValueError(f"Scope flags cannot be promoted: {path}")
        elif isinstance(reference, (int, float)):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Finite nonnegative number required: {path}")
            if isinstance(reference, int) and type(value) is not int:
                raise ValueError(f"Integer required: {path}")
            if reference > 0 and value == 0 and ".initial_states." not in path:
                raise ValueError(f"Positive number required: {path}")
        elif not isinstance(value, str) or not value:
            raise ValueError(f"Text required: {path}")

    shape(p, template, "protocol")
    if p["protocol_id"] != "E01-A" or p["schema_version"] != 1:
        raise ValueError("Unsupported protocol")
    if p["methods"] != ["BDF", "Radau"]:
        raise ValueError("Both BDF and Radau required in this order")
    b, t, s = p["batch"], p["tracer"], p["sphere"]
    states = {x["state_id"]: x for x in b["initial_states"]}
    if len(b["initial_states"]) != 4 or set(states) != {
        "adsorption",
        "desorption",
        "equilibrium",
        "empty",
    }:
        raise ValueError("Four distinct batch reference states required")
    for label, state in states.items():
        c, q = state["concentration_kg_m3"], state["loading_kg_kg"]
        target = b["distribution_m3_kg"] * c
        valid = {
            "adsorption": q < target,
            "desorption": q > target,
            "equilibrium": math.isclose(q, target, rel_tol=1e-14),
            "empty": c == q == 0,
        }[label]
        if not valid:
            raise ValueError(f"Inconsistent batch state: {label}")
    for key in ("rtol", "atol_concentration_kg_m3", "atol_loading_kg_kg"):
        values = [x[key] for x in b["tolerances"]]
        if len(values) < 3 or any(a <= z for a, z in zip(values, values[1:], strict=False)):
            raise ValueError("Batch tolerances must strictly decrease, >=3 levels")
    for obj, key, minimum in ((t, "axial_cells", 3), (s, "radial_cells", 4)):
        values = obj[key]
        if (
            len(values) < minimum
            or any(type(x) is not int or x < 2 for x in values)
            or any(a >= z for a, z in zip(values, values[1:], strict=False))
        ):
            raise ValueError(f"Invalid increasing mesh: {key}")
    if any(
        t[k] != 0
        for k in (
            "axial_dispersion_m2_s",
            "distribution_m3_kg",
            "initial_concentration_kg_m3",
            "initial_loading_kg_kg",
        )
    ):
        raise ValueError("Tanks reference requires clean zero-dispersion nonadsorbing tracer")
    if s["initial_loading_kg_kg"] != 0 or any(
        a >= z for a, z in zip(s["fourier_times"], s["fourier_times"][1:], strict=False)
    ):
        raise ValueError("Sphere requires zero initial loading and increasing Fourier times")
    for obj in (t, p["matrix_ldf"]):
        if not 0 < obj["bed"]["porosity"] < 1 or obj["sample_count"] < 3:
            raise ValueError("Invalid bed/sample count")
    if b["sample_count"] < 3 or t["horizon_residence_times"] <= 1:
        raise ValueError("Insufficient observation horizon")
    if p["matrix_ldf"]["axial_cells"] < 2:
        raise ValueError("Matrix reference requires >=2 axial cells")
    log_bound = (
        math.log(6 / math.pi**2 / s["series_terms"])
        - math.pi**2 * s["series_terms"] ** 2 * s["fourier_times"][0]
    )
    if log_bound > math.log(s["criteria"]["series_tail_absolute_fraction_max"]):
        raise ValueError("Sphere series truncation cannot meet declared bound")


def batch_exact(b, state, times):
    v, m, k = b["liquid_volume_m3"], b["adsorbent_mass_kg"], b["distribution_m3_kg"]
    c0, q0 = state["concentration_kg_m3"], state["loading_kg_kg"]
    ceq = (v * c0 + m * q0) / (v + m * k)
    c = ceq + (c0 - ceq) * np.exp(-b["rate_s_inv"] * (1 + m * k / v) * times)
    return c, (v * c0 + m * q0 - v * c) / m


def scaled_rms(actual, reference, scale):
    return float(np.sqrt(np.mean(((actual - reference) / scale) ** 2)))


def affine_matrix(p):
    n, bed = p["axial_cells"], p["bed"]
    area = math.pi * bed["diameter_m"] ** 2 / 4
    eps, dz = bed["porosity"], bed["length_m"] / n
    rho_b = (1 - eps) * bed["particle_density_kg_m3"]
    a = p["flow_m3_s"] / (area * eps * dz)
    d = p["axial_dispersion_m2_s"] / dz**2
    k, rate = p["distribution_m3_kg"], p["rate_s_inv"]
    matrix = np.zeros((2 * n + 1, 2 * n + 1))
    for i in range(n):
        matrix[i, i] = -a - d * (int(i > 0) + int(i < n - 1)) - rho_b / eps * rate * k
        if i > 0:
            matrix[i, i - 1] = a + d
        if i < n - 1:
            matrix[i, i + 1] = d
        matrix[i, n + i] = rho_b / eps * rate
        matrix[n + i, i], matrix[n + i, n + i] = rate * k, -rate
    matrix[0, -1] = a * p["inlet_concentration_kg_m3"]
    initial = np.r_[
        np.full(n, p["initial_concentration_kg_m3"]), np.full(n, p["initial_loading_kg_kg"]), 1.0
    ]
    return matrix, initial


def sources():
    core = ROOT / "src" / "pyfast"
    paths = sorted(core.glob("*.py"))
    for directory in ("equilibrium", "kinetics", "reactors", "solvers"):
        paths.extend(sorted((core / directory).rglob("*.py")))
    paths.extend(sorted(Path(__file__).parent.glob("*.py")))
    hashes = {str(x.relative_to(ROOT)).replace("\\", "/"): sha(x.read_bytes()) for x in paths}
    return {"files": hashes, "combined_sha256": sha(json.dumps(hashes, sort_keys=True).encode())}


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


class Study:
    def __init__(self, p):
        self.p, self.cases, self.metrics, self.traces = p, [], [], []
        self.cache = {}

    def check(self, case, name, value, limit, relation="<="):
        passed = math.isfinite(value) and (value <= limit if relation == "<=" else value >= limit)
        self.metrics.append(
            dict(
                case_id=case,
                name=name,
                value=float(value),
                relation=relation,
                limit=float(limit),
                passed=passed,
            )
        )

    def trace(self, case, times, actual, reference, variable):
        for t, a, r in zip(times, actual, reference, strict=False):
            self.traces.append(
                dict(
                    case_id=case,
                    time_s=float(t),
                    variable=variable,
                    actual=float(a),
                    reference=float(r),
                )
            )

    def execute(self, case, fn):
        start, index = time.perf_counter(), len(self.metrics)
        record = dict(case_id=case)
        try:
            extra = fn(case)
            record.update(extra or {})
            record["status"] = "PASS" if all(x["passed"] for x in self.metrics[index:]) else "FAIL"
        except Exception as exc:
            record.update(status="ERROR", error_type=type(exc).__name__, error=str(exc))
        record["elapsed_s"] = time.perf_counter() - start
        self.cases.append(record)
        print(f"{case}: {record['status']} ({record['elapsed_s']:.3f}s)", flush=True)

    def options(self, method, tol, **kwargs):
        return SolverOptions(
            method=method,
            **tol,
            mass_rtol=self.p["common"]["mass_scaled_max"],
            mass_reference_kg=self.p["common"]["mass_reference_kg"],
            **kwargs,
        )

    def diagnostics(self, case, result, tol):
        d, p = result.diagnostics, self.p["common"]
        self.check(case, "mass_absolute_kg", d.max_abs_mass_residual_kg, p["mass_absolute_max_kg"])
        self.check(case, "mass_scaled", d.max_scaled_mass_residual, p["mass_scaled_max"])
        self.check(
            case,
            "min_c_kg_m3",
            d.min_concentration_kg_m3,
            -p["negative_atol_multiplier"] * tol["atol_concentration_kg_m3"],
            ">=",
        )
        self.check(
            case,
            "min_q_kg_kg",
            d.min_loading_kg_kg,
            -p["negative_atol_multiplier"] * tol["atol_loading_kg_kg"],
            ">=",
        )
        return {"solver_diagnostics": asdict(d), "numerical_sha256": result.numerical_sha256}

    def run_batch(self, case, method, level, state):
        b = self.p["batch"]
        tol = b["tolerances"][level]
        config = BatchConfig(
            species=Species(name="E01-A-linear"),
            material="generic",
            liquid_volume_m3=b["liquid_volume_m3"],
            adsorbent_mass_kg=b["adsorbent_mass_kg"],
            duration_s=b["duration_s"],
            initial_concentration_kg_m3=state["concentration_kg_m3"],
            initial_loading_kg_kg=state["loading_kg_kg"],
            equilibrium=Linear(distribution_m3_kg=b["distribution_m3_kg"]),
            kinetics=LDF(rate_s_inv=b["rate_s_inv"]),
        )
        times = np.linspace(0, b["duration_s"], b["sample_count"])
        result = batch(config, time_s=times, options=self.options(method, tol))
        c, q = result.concentration_kg_m3[:, 0], result.loading_kg_kg[:, 0]
        ec, eq = batch_exact(b, state, times)
        error = max(
            scaled_rms(c, ec, b["concentration_scale_kg_m3"]),
            scaled_rms(q, eq, b["loading_scale_kg_kg"]),
        )
        crit = b["criteria"]
        self.check(case, "scaled_rms", error, crit["scaled_rms_all_max"])
        if level == len(b["tolerances"]) - 1:
            self.check(case, "finest_scaled_rms", error, crit["scaled_rms_finest_max"])
        self.cache[case] = (error, c, q)
        self.trace(case, times, c, ec, "c_kg_m3")
        self.trace(case, times, q, eq, "q_kg_kg")
        return self.diagnostics(case, result, tol)

    def column_config(self, p, duration):
        return SimulationConfig(
            species=Species(name="E01-A-solute"),
            bed=Bed(material="generic", **p["bed"]),
            operation=Operation(
                **{
                    k: p[k]
                    for k in (
                        "flow_m3_s",
                        "inlet_concentration_kg_m3",
                        "axial_dispersion_m2_s",
                        "initial_concentration_kg_m3",
                        "initial_loading_kg_kg",
                    )
                },
                duration_s=duration,
            ),
            equilibrium=Linear(distribution_m3_kg=p["distribution_m3_kg"]),
            kinetics=LDF(rate_s_inv=p["rate_s_inv"]),
        )

    def run_tracer(self, case, method, n):
        p = self.p["tracer"]
        bed = p["bed"]
        tau = (
            bed["porosity"]
            * math.pi
            * bed["diameter_m"] ** 2
            / 4
            * bed["length_m"]
            / p["flow_m3_s"]
        )
        duration = p["horizon_residence_times"] * tau
        times = np.linspace(0, duration, p["sample_count"])
        result = column(
            self.column_config(p, duration),
            time_s=times,
            options=self.options(method, p["tolerance"], axial_cells=n),
        )
        actual = result.outlet_concentration_kg_m3 / p["inlet_concentration_kg_m3"]
        reference = gammainc(n, n * times / tau)
        front_error = float(trapezoid(abs(actual - (times >= tau)), times) / tau)
        self.check(
            case,
            "tanks_linf_normalized",
            float(np.max(abs(actual - reference))),
            p["criteria"]["tanks_linf_normalized_max"],
        )
        t50error = abs(float(np.interp(0.5, actual, times)) / tau - 1)
        if n == p["axial_cells"][-1]:
            self.check(
                case,
                "finest_t50_relative_error",
                t50error,
                p["criteria"]["finest_t50_relative_error_max"],
            )
        self.cache[case] = front_error
        self.trace(case, times, actual, reference, "normalized_outlet_vs_FV")
        self.trace(
            case, times, actual, (times >= tau).astype(float), "normalized_outlet_vs_PDE_step"
        )
        return dict(
            front_l1_normalized=front_error,
            residence_time_s=tau,
            t10_s=float(np.interp(0.1, actual, times)),
            t50_s=float(np.interp(0.5, actual, times)),
            t90_s=float(np.interp(0.9, actual, times)),
            **self.diagnostics(case, result, p["tolerance"]),
        )

    def run_sphere(self, case, n):
        p = self.p["sphere"]
        r, ds, rho, qs = (
            p["radius_m"],
            p["surface_diffusivity_m2_s"],
            p["particle_density_kg_m3"],
            p["surface_loading_kg_kg"],
        )
        grid = SphereGrid(r, n)

        def flux(q):
            return rho * ds * (qs - q[-1]) / (r - grid.centers_m[-1])

        def rhs(t, q):
            return diffusion_rhs(
                q[None],
                np.array([flux(q)]),
                grid=grid,
                diffusivity_m2_s=ds,
                particle_density_kg_m3=rho,
            )[0]

        fo = np.array(p["fourier_times"])
        times = fo * r * r / ds
        solution = solve_ivp(
            rhs,
            (0, float(times[-1])),
            np.zeros(n),
            method="BDF",
            rtol=p["rtol"],
            atol=p["atol_loading_kg_kg"],
            dense_output=True,
        )
        if not solution.success or solution.sol is None:
            raise RuntimeError(solution.message)
        sampled = solution.sol(times)
        checked = np.concatenate([solution.y, sampled], axis=1)
        if not np.all(np.isfinite(checked)):
            raise RuntimeError("Nonfinite sphere state")
        terms = np.arange(1, p["series_terms"] + 1)[:, None]
        exact = 1 - 6 / math.pi**2 * np.sum(
            np.exp(-(terms**2) * math.pi**2 * fo) / terms**2, axis=0
        )
        mean = grid.mean_weights @ sampled / qs
        error = float(np.max(abs(mean - exact) / exact))
        identity = max(
            abs(float(grid.mean_weights @ rhs(t, q)) - 3 * flux(q) / (rho * r))
            for t, q in zip(times, sampled.T, strict=False)
        ) / (ds * qs / r**2)
        self.check(
            case,
            "sampled_radial_balance_scaled",
            identity,
            p["criteria"]["sampled_radial_balance_scaled_max"],
        )
        self.check(
            case,
            "min_q_kg_kg",
            float(np.min(checked)),
            -self.p["common"]["negative_atol_multiplier"] * p["atol_loading_kg_kg"],
            ">=",
        )
        if n == p["radial_cells"][-1]:
            self.check(
                case,
                "finest_mean_relative_error",
                error,
                p["criteria"]["finest_mean_relative_error_max"],
            )
        self.cache[case] = error
        self.trace(case, times, mean, exact, "normalized_mean_q")
        return dict(
            max_mean_relative_error=error,
            nfev=solution.nfev,
            njev=solution.njev,
            nlu=solution.nlu,
            accepted_steps=len(solution.t) - 1,
        )

    def run_matrix(self, case, method):
        p = self.p["matrix_ldf"]
        matrix, initial = affine_matrix(p)
        times = np.linspace(0, p["duration_s"], p["sample_count"])
        exact = np.array([(expm(matrix * t) @ initial)[:-1] for t in times])
        result = column(
            self.column_config(p, p["duration_s"]),
            time_s=times,
            options=self.options(method, p["tolerance"], axial_cells=p["axial_cells"]),
        )
        n = p["axial_cells"]
        for var, actual, reference in (
            ("concentration", result.concentration_kg_m3, exact[:, :n]),
            ("loading", result.loading_kg_kg, exact[:, n:]),
        ):
            unit = "kg_m3" if var == "concentration" else "kg_kg"
            self.check(
                case,
                f"{var}_linf_{unit}",
                float(np.max(abs(actual - reference))),
                p["criteria"][f"{var}_linf_{unit}_max"],
            )
            for i in range(n):
                self.trace(case, times, actual[:, i], reference[:, i], f"{var}_{unit}_cell_{i}")
        return self.diagnostics(case, result, p["tolerance"])

    def aggregates(self, case):
        p, b = self.p, self.p["batch"]
        finest = len(b["tolerances"]) - 1
        for state in b["initial_states"]:
            label = state["state_id"]
            for method in p["methods"]:
                if label in ("adsorption", "desorption"):
                    coarse = self.cache[f"batch_{label}_{method}_0"][0]
                    fine = self.cache[f"batch_{label}_{method}_{finest}"][0]
                    self.check(
                        case,
                        f"{label}_{method}_tolerance_error_ratio",
                        fine / coarse,
                        b["criteria"]["transient_finest_to_coarsest_error_ratio_max"],
                    )
            x, y = [self.cache[f"batch_{label}_{method}_{finest}"] for method in p["methods"]]
            disagreement = max(
                float(np.max(abs(x[i] - y[i]))) / b[scale]
                for i, scale in ((1, "concentration_scale_kg_m3"), (2, "loading_scale_kg_kg"))
            )
            self.check(
                case,
                f"{label}_method_disagreement",
                disagreement,
                b["criteria"]["method_disagreement_scaled_max"],
            )
        for method in p["methods"]:
            errors = [self.cache[f"tracer_{method}_{n}"] for n in p["tracer"]["axial_cells"]]
            for i, (a, z) in enumerate(zip(errors, errors[1:], strict=False)):
                self.check(
                    case,
                    f"tracer_{method}_refinement_ratio_{i}",
                    z / a,
                    p["tracer"]["criteria"]["front_l1_successive_ratio_max"],
                )
        meshes = p["sphere"]["radial_cells"]
        errors = [self.cache[f"sphere_BDF_{n}"] for n in meshes]
        for i in range(len(meshes) - 2, len(meshes)):
            order = math.log(errors[i - 1] / errors[i]) / math.log(meshes[i] / meshes[i - 1])
            self.check(
                case,
                f"sphere_order_{meshes[i]}",
                order,
                p["sphere"]["criteria"]["last_two_refinement_orders_min"],
                ">=",
            )

    def run(self):
        for state in self.p["batch"]["initial_states"]:
            for method in self.p["methods"]:
                for level in range(len(self.p["batch"]["tolerances"])):
                    self.execute(
                        f"batch_{state['state_id']}_{method}_{level}",
                        lambda case, m=method, lev=level, s=state: self.run_batch(case, m, lev, s),
                    )
        for method in self.p["methods"]:
            for n in self.p["tracer"]["axial_cells"]:
                self.execute(
                    f"tracer_{method}_{n}", lambda case, m=method, n=n: self.run_tracer(case, m, n)
                )
        for n in self.p["sphere"]["radial_cells"]:
            self.execute(f"sphere_BDF_{n}", lambda case, n=n: self.run_sphere(case, n))
        for method in self.p["methods"]:
            self.execute(f"matrix_ldf_{method}", lambda case, m=method: self.run_matrix(case, m))
        self.execute("cross_case_criteria", self.aggregates)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = args.protocol.read_bytes()
        p = json.loads(raw)
        validate_protocol(p)
        output = args.output.resolve()
        forbidden = [
            ROOT / x
            for x in ("src", "benchmarks", "datasets_benchmark_pyfast", "tests", "PAPER_ENVSOFT")
        ]
        if output == ROOT or any(output == x or x in output.parents for x in forbidden):
            raise ValueError("Output must be outside source, benchmarks and original data")
        if Path(pyfast.__file__).resolve() != ROOT / "src" / "pyfast" / "__init__.py":
            raise ValueError("Imported pyfast differs from hashed repository source")
        output.mkdir(parents=True, exist_ok=False)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Invalid input: {exc}\n")
    (output / "protocol.json").write_bytes(raw)
    started = datetime.now(UTC).isoformat()
    source_before = sources()
    git_before = {
        "head": git("rev-parse", "HEAD"),
        "status_porcelain": git("status", "--porcelain"),
        "protocol_baseline_commit": BASELINE,
    }
    study = Study(p)
    start = time.perf_counter()
    study.run()
    elapsed = time.perf_counter() - start
    source_after = sources()
    stable = source_before == source_after
    passed = all(x["status"] == "PASS" for x in study.cases) and stable
    for name, rows, fields in (
        ("metrics.csv", study.metrics, ["case_id", "name", "value", "relation", "limit", "passed"]),
        (
            "trajectories.csv",
            study.traces,
            ["case_id", "time_s", "variable", "actual", "reference"],
        ),
    ):
        with (output / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    plots = {"status": "unavailable"}
    try:
        os.environ["MPLCONFIGDIR"] = str(output / "matplotlib_config")
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 4))
        for method in p["methods"]:
            rows = [
                x
                for x in study.cases
                if x["case_id"].startswith(f"tracer_{method}_") and "front_l1_normalized" in x
            ]
            ax.loglog(
                [int(x["case_id"].split("_")[-1]) for x in rows],
                [x["front_l1_normalized"] for x in rows],
                "o-",
                label=method,
            )
        ax.set(
            xlabel="Axial cells",
            ylabel="Normalized L1 error vs PDE front",
            title="E01-A: zero-dispersion tracer",
        )
        ax.legend()
        fig.tight_layout()
        fig.savefig(output / "tracer_convergence.png", dpi=180)
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(7, 4))
        for n in p["sphere"]["radial_cells"]:
            rows = [x for x in study.traces if x["case_id"] == f"sphere_BDF_{n}"]
            ax.semilogx(
                [x["time_s"] for x in rows], [x["actual"] for x in rows], "o-", label=f"Nr={n}"
            )
        rows = [
            x
            for x in study.traces
            if x["case_id"] == f"sphere_BDF_{p['sphere']['radial_cells'][-1]}"
        ]
        ax.semilogx(
            [x["time_s"] for x in rows],
            [x["reference"] for x in rows],
            "k--",
            label="Dirichlet series",
        )
        ax.set(
            xlabel="Time (s)", ylabel="Mean q / surface q", title="E01-A: prescribed-surface sphere"
        )
        ax.legend()
        fig.tight_layout()
        fig.savefig(output / "sphere_uptake.png", dpi=180)
        plt.close(fig)
        plots = {"status": "generated", "matplotlib_version": matplotlib.__version__}
    except ImportError as exc:
        plots["reason"] = str(exc)
    except Exception as exc:
        plots = {"status": "error", "reason": str(exc)}
    summary = dict(
        protocol_id=p["protocol_id"],
        protocol_sha256=sha(raw),
        status="PASS_SCOPED_E01_A" if passed else "FAIL_OR_INCONCLUSIVE",
        full_e01_complete=False,
        experimental_validation=False,
        source_stable_during_execution=stable,
        cases=study.cases,
        criteria_count=len(study.metrics),
        criteria_failed=sum(not x["passed"] for x in study.metrics),
        elapsed_s=elapsed,
        plots=plots,
    )
    write_json(output / "summary.json", summary)
    manifest = dict(
        started_utc=started,
        finished_utc=datetime.now(UTC).isoformat(),
        python=sys.version,
        platform=platform.platform(),
        versions={x: version(x) for x in ("pyfast-adsorption", "numpy", "scipy")},
        pyfast_import_path=pyfast.__file__,
        git_before=git_before,
        git_after={
            "head": git("rev-parse", "HEAD"),
            "status_porcelain": git("status", "--porcelain"),
        },
        source_before=source_before,
        source_after=source_after,
        protocol_sha256=sha(raw),
        known_concurrency=(
            "Other workers active on GUI/documentation; elapsed times describe this execution, "
            "not comparative performance benchmarks."
        ),
        limitations=p["scope"],
        artifacts={
            str(x.relative_to(output)): sha(x.read_bytes())
            for x in sorted(output.iterdir())
            if x.is_file()
        },
    )
    write_json(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "status",
                    "protocol_sha256",
                    "criteria_count",
                    "criteria_failed",
                    "elapsed_s",
                )
            }
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Run frozen E01-B: continuous finite-Pe ADE tracer verification, not validation."""

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
from reference import ADEReference

import sorbflow
from sorbflow import LDF, Bed, Linear, Operation, SimulationConfig, Species
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions

ROOT = Path(__file__).resolve().parents[2]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate(p):
    template = json.loads(Path(__file__).with_name("protocol.json").read_text())

    def shape(value, reference, path):
        if isinstance(reference, dict):
            if not isinstance(value, dict) or value.keys() != reference.keys():
                raise ValueError(f"Missing/unknown fields: {path}")
            for key in reference:
                shape(value[key], reference[key], path + "." + key)
        elif isinstance(reference, list):
            if not isinstance(value, list) or not value:
                raise ValueError(f"Nonempty list required: {path}")
            for item in value:
                shape(item, reference[0], path)
        elif isinstance(reference, bool):
            if type(value) is not bool or value != reference:
                raise ValueError("Scientific scope cannot be promoted")
        elif isinstance(reference, (int, float)):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Finite positive number required: {path}")
            if isinstance(reference, int) and type(value) is not int:
                raise ValueError(f"Integer required: {path}")
        elif not isinstance(value, str) or not value:
            raise ValueError(f"Nonempty text required: {path}")

    shape(p, template, "protocol")
    if p["schema_version"] != 1 or p["protocol_id"] != "E01-B" or p["methods"] != ["BDF", "Radau"]:
        raise ValueError("Unsupported protocol or methods")
    if p["reference_modes"] != [64, 128]:
        raise ValueError("Reference truncation gate requires 64/128 modes")
    if (
        not 0 < p["bed"]["porosity"] < 1
        or p["sample_theta_start"] < 0.1
        or p["sample_theta_end"] <= p["sample_theta_start"]
        or p["sample_count"] < 3
    ):
        raise ValueError("Invalid bed or observation domain")
    if (
        len(p["axial_cells"]) < 4
        or any(type(n) is not int or n < 2 for n in p["axial_cells"])
        or any(a >= b for a, b in zip(p["axial_cells"], p["axial_cells"][1:], strict=False))
    ):
        raise ValueError("Need >=4 strictly increasing integer meshes")
    if len(p["peclet"]) != len(set(p["peclet"])):
        raise ValueError("Duplicate Peclet cases")
    for pe in p["peclet"]:
        ADEReference(pe)


def source_snapshot():
    core = ROOT / "src/sorbflow"
    paths = sorted(core.glob("*.py"))
    for folder in ("equilibrium", "kinetics", "reactors", "solvers"):
        paths.extend(sorted((core / folder).glob("*.py")))
    paths.extend(sorted(Path(__file__).parent.glob("*.py")))
    files = {x.relative_to(ROOT).as_posix(): sha(x.read_bytes()) for x in paths}
    return dict(files=files, combined_sha256=sha(json.dumps(files, sort_keys=True).encode()))


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


class Study:
    def __init__(self, p):
        self.p, self.metrics, self.cases, self.traces, self.cache = p, [], [], [], {}
        self.theta = np.linspace(p["sample_theta_start"], p["sample_theta_end"], p["sample_count"])

    def check(self, case, name, value, limit, relation="<="):
        passed = math.isfinite(value) and (value <= limit if relation == "<=" else value >= limit)
        self.metrics.append(
            dict(
                case_id=case,
                name=name,
                value=float(value),
                limit=float(limit),
                relation=relation,
                passed=passed,
            )
        )

    def execute(self, case, fn):
        start, index = time.perf_counter(), len(self.metrics)
        record = dict(case_id=case)
        try:
            record.update(fn(case) or {})
            record["status"] = "PASS" if all(x["passed"] for x in self.metrics[index:]) else "FAIL"
        except Exception as exc:
            record.update(status="INCONCLUSIVE", error_type=type(exc).__name__, error=str(exc))
        record["elapsed_s"] = time.perf_counter() - start
        self.cases.append(record)
        print(f"{case}: {record['status']} ({record['elapsed_s']:.3f}s)", flush=True)

    def reference_gate(self, case, pe):
        fine, coarse = ADEReference(pe, 128), ADEReference(pe, 64)
        crit = self.p["criteria"]
        for name, value in fine.checks(self.theta).items():
            self.check(case, name, value, crit[name + "_max"])
        truncation = 0.0
        minimum, maximum = math.inf, -math.inf
        for n in self.p["axial_cells"]:
            edges = np.linspace(0, 1, n + 1)
            cf, cc = fine.averages(edges, self.theta), coarse.averages(edges, self.theta)
            truncation = max(truncation, float(np.max(abs(cf - cc))))
            minimum, maximum = min(minimum, float(cf.min())), max(maximum, float(cf.max()))
        of, oc = fine.points([1], self.theta), coarse.points([1], self.theta)
        truncation = max(truncation, float(np.max(abs(of - oc))))
        self.check(case, "reference_64_128_linf", truncation, crit["reference_64_128_linf_max"])
        self.check(
            case,
            "reference_min",
            min(minimum, float(of.min())),
            -crit["reference_state_slack"],
            ">=",
        )
        self.check(
            case, "reference_max", max(maximum, float(of.max())), 1 + crit["reference_state_slack"]
        )
        late = fine.points(np.linspace(0, 1, 51), [crit["late_theta"]])
        self.check(
            case,
            "late_equilibrium_linf",
            float(np.max(abs(late - 1))),
            crit["late_equilibrium_linf_max"],
        )
        return dict(peclet=pe, reference_modes=128)

    def fv(self, case, pe, method, n):
        p, crit = self.p, self.p["criteria"]
        bed = Bed(material="E01-B-generic", **p["bed"])
        area = math.pi * p["bed"]["diameter_m"] ** 2 / 4
        velocity = p["flow_m3_s"] / (p["bed"]["porosity"] * area)
        tau = p["bed"]["length_m"] / velocity
        dispersion = velocity * p["bed"]["length_m"] / pe
        config = SimulationConfig(
            species=Species(name="E01-B-tracer"),
            bed=bed,
            operation=Operation(
                flow_m3_s=p["flow_m3_s"],
                inlet_concentration_kg_m3=p["inlet_concentration_kg_m3"],
                duration_s=p["sample_theta_end"] * tau,
                axial_dispersion_m2_s=dispersion,
            ),
            equilibrium=Linear(distribution_m3_kg=0),
            kinetics=LDF(rate_s_inv=0.1),
        )
        times = np.r_[0.0, self.theta * tau]
        result = column(
            config, time_s=times, options=SolverOptions(method=method, axial_cells=n, **p["solver"])
        )
        actual = result.concentration_kg_m3[1:] / p["inlet_concentration_kg_m3"]
        reference = ADEReference(pe, 128)
        expected = reference.averages(np.linspace(0, 1, n + 1), self.theta)
        outlet = reference.points([1], self.theta)[:, 0]
        error = actual - expected
        rms, linf, outlet_linf = (
            float(np.sqrt(np.mean(error**2))),
            float(np.max(abs(error))),
            float(np.max(abs(actual[:, -1] - outlet))),
        )
        if n == p["axial_cells"][-1]:
            for name, value in (
                ("finest_profile_rms_normalized", rms),
                ("finest_profile_linf_normalized", linf),
                ("finest_outlet_linf_normalized", outlet_linf),
            ):
                self.check(case, name, value, crit[name + "_max"])
        d = result.diagnostics
        for name, value in (
            ("mass_absolute_kg", d.max_abs_mass_residual_kg),
            ("mass_scaled", d.max_scaled_mass_residual),
        ):
            self.check(case, name, value, crit[name + "_max"])
        for name, value, atol in (
            ("min_c", d.min_concentration_kg_m3, p["solver"]["atol_concentration_kg_m3"]),
            ("min_q", d.min_loading_kg_kg, p["solver"]["atol_loading_kg_kg"]),
        ):
            self.check(case, name, value, -crit["negative_atol_multiplier"] * atol, ">=")
        self.cache[(pe, method, n)] = dict(profile_rms=rms, outlet_linf=outlet_linf, actual=actual)
        for ti, theta in enumerate(self.theta):
            for i in range(n):
                self.traces.append(
                    dict(
                        case_id=case,
                        theta=float(theta),
                        x_left=i / n,
                        x_right=(i + 1) / n,
                        variable="cell_average_normalized",
                        actual=float(actual[ti, i]),
                        reference=float(expected[ti, i]),
                    )
                )
            self.traces.append(
                dict(
                    case_id=case,
                    theta=float(theta),
                    x_left=1.0,
                    x_right=1.0,
                    variable="outlet_flux_concentration_normalized",
                    actual=float(actual[ti, -1]),
                    reference=float(outlet[ti]),
                )
            )
        return dict(
            peclet=pe,
            method=method,
            axial_cells=n,
            tau_s=tau,
            dispersion_m2_s=dispersion,
            profile_rms=rms,
            profile_linf=linf,
            outlet_linf=outlet_linf,
            diagnostics=asdict(d),
            numerical_sha256=result.numerical_sha256,
        )

    def aggregate(self, case):
        p, crit = self.p, self.p["criteria"]
        meshes = p["axial_cells"]
        for pe in p["peclet"]:
            for method in p["methods"]:
                for metric in ("profile_rms", "outlet_linf"):
                    for i in range(1, len(meshes)):
                        a, b = [self.cache[(pe, method, n)][metric] for n in meshes[i - 1 : i + 1]]
                        ratio = b / a
                        self.check(
                            case,
                            f"Pe{pe}_{method}_{metric}_ratio_N{meshes[i]}",
                            ratio,
                            crit["successive_error_ratio_max"],
                        )
                        if i >= len(meshes) - 2:
                            order = math.log(a / b) / math.log(meshes[i] / meshes[i - 1])
                            self.check(
                                case,
                                f"Pe{pe}_{method}_{metric}_order_N{meshes[i]}",
                                order,
                                crit["last_two_orders_min"],
                                ">=",
                            )
            for n in meshes:
                a, b = [self.cache[(pe, m, n)]["actual"] for m in p["methods"]]
                self.check(
                    case,
                    f"Pe{pe}_N{n}_method_disagreement",
                    float(np.max(abs(a - b))),
                    crit["method_disagreement_normalized_max"],
                )

    def run(self):
        for pe in self.p["peclet"]:
            self.execute(f"reference_Pe{pe}", lambda case, pe=pe: self.reference_gate(case, pe))
            for method in self.p["methods"]:
                for n in self.p["axial_cells"]:
                    self.execute(
                        f"Pe{pe}_{method}_N{n}",
                        lambda case, pe=pe, m=method, n=n: self.fv(case, pe, m, n),
                    )
        self.execute("refinement_and_method_criteria", self.aggregate)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        raw = args.protocol.read_bytes()
        p = json.loads(raw)
        validate(p)
        output = args.output.resolve()
        protected = [
            ROOT / x
            for x in ("src", "benchmarks", "tests", "datasets_benchmark_pyfast", "PAPER_ENVSOFT")
        ]
        if output == ROOT or any(output == x or x in output.parents for x in protected):
            raise ValueError("Output must be outside source/benchmarks/original data")
        if Path(sorbflow.__file__).resolve() != ROOT / "src/sorbflow/__init__.py":
            raise ValueError("Imported sorbflow differs from hashed source")
        output.mkdir(parents=True, exist_ok=False)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Invalid input: {exc}\n")
    (output / "protocol.json").write_bytes(raw)
    before = source_snapshot()
    started = datetime.now(UTC).isoformat()
    git_before = dict(
        head=git("rev-parse", "HEAD"),
        status_porcelain=git("status", "--porcelain"),
        protocol_last_commit=git("log", "-1", "--format=%H", "--", "benchmarks/e01b/protocol.json"),
    )
    study = Study(p)
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    study.run()
    cpu, wall = time.process_time() - start_cpu, time.perf_counter() - start_wall
    after = source_snapshot()
    stable = before == after
    passed = stable and all(x["status"] == "PASS" for x in study.cases)
    for name, rows, fields in (
        ("metrics.csv", study.metrics, ["case_id", "name", "value", "limit", "relation", "passed"]),
        (
            "trajectories.csv",
            study.traces,
            ["case_id", "theta", "x_left", "x_right", "variable", "actual", "reference"],
        ),
    ):
        with (output / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    plots = dict(status="unavailable")
    try:
        os.environ["MPLCONFIGDIR"] = str(output / "matplotlib_config")
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for pe in p["peclet"]:
            for method in p["methods"]:
                rows = [
                    x
                    for x in study.cases
                    if x.get("peclet") == pe and x.get("method") == method and "profile_rms" in x
                ]
                for ax, metric in zip(axes, ("profile_rms", "outlet_linf"), strict=True):
                    ax.loglog(
                        [x["axial_cells"] for x in rows],
                        [x[metric] for x in rows],
                        "o-",
                        label=f"Pe={pe}, {method}",
                    )
                    ax.set(xlabel="Axial cells", ylabel=metric + " / inlet scale")
        axes[0].legend()
        fig.suptitle("E01-B continuous ADE reference")
        fig.tight_layout()
        fig.savefig(output / "continuous_convergence.png", dpi=180)
        plt.close(fig)
        plots = dict(status="generated", matplotlib_version=matplotlib.__version__)
    except ImportError as exc:
        plots["reason"] = str(exc)
    except Exception as exc:
        plots = dict(status="error", reason=str(exc))
    summary = dict(
        protocol_id=p["protocol_id"],
        protocol_sha256=sha(raw),
        status="PASS_SCOPED_E01_B" if passed else "FAIL_OR_INCONCLUSIVE",
        full_e01_complete=False,
        experimental_validation=False,
        source_stable=stable,
        case_count=len(study.cases),
        criteria_count=len(study.metrics),
        criteria_failed=sum(not x["passed"] for x in study.metrics),
        cpu_time_s=cpu,
        wall_time_s=wall,
        cases=study.cases,
        plots=plots,
    )
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        dict(
            started_utc=started,
            finished_utc=datetime.now(UTC).isoformat(),
            python=sys.version,
            platform=platform.platform(),
            versions={name: version(name) for name in ("sorbflow", "numpy", "scipy")},
            sorbflow_import_path=sorbflow.__file__,
            git_before=git_before,
            git_after=dict(
                head=git("rev-parse", "HEAD"), status_porcelain=git("status", "--porcelain")
            ),
            protocol_sha256=sha(raw),
            source_before=before,
            source_after=after,
            known_concurrency=(
                "Other workers active on independent modules/docs; CPU and wall times are "
                "local execution measurements, not performance comparisons."
            ),
            scope=p["scope"],
            artifacts={
                x.name: sha(x.read_bytes()) for x in sorted(output.iterdir()) if x.is_file()
            },
        ),
    )
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "status",
                    "criteria_count",
                    "criteria_failed",
                    "cpu_time_s",
                    "wall_time_s",
                )
            }
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

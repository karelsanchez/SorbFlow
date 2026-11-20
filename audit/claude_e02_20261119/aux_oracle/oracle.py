"""Independent analytic oracle for the E02 statistical review.

ORIGINAL, SELF-CONTAINED. Does NOT import, call or transcribe PyFAST.
Only NumPy/SciPy general routines. Every value written by this script is an
`own_oracle` computation; none is a PyFAST result. PyFAST was not executed.

Usage (from any directory):  python -I oracle.py
Writes only: <this directory>/oracle_results.json
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy import optimize, stats

HERE = Path(__file__).resolve().parent
CUTOFF95 = float(stats.chi2.ppf(0.95, 1))
TOL_CLOSED = 1e-9          # closed form vs independent numerics (float64, chi2 = O(1e2))
DECISION_MARGIN = 0.05     # grid points must be at least this far from the cutoff
checks: list[dict] = []


def check(name: str, ok: bool, detail) -> None:
    checks.append({"check": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def margin_ok(deltas, case):
    worst = float(np.min(np.abs(np.asarray(deltas) - CUTOFF95)))
    check(f"{case}: grid decisions robust (|delta-cutoff| >= {DECISION_MARGIN})",
          worst >= DECISION_MARGIN, worst)


def bvls_chi2(A, b, lo, hi):
    """Exact bounded linear least squares (scipy BVLS); returns (x, chi2)."""
    r = optimize.lsq_linear(np.atleast_2d(A), b, bounds=(lo, hi), method="bvls", tol=1e-14)
    return r.x, float(2 * r.cost)


# ---------------------------------------------------------------- Case A ---
def case_a():
    y = np.array([2.1, 1.7, 2.4, 1.9, 2.6, 2.2, 1.8, 2.3])
    sigma, n = 0.5, y.size
    muhat = y.mean()
    chi2 = lambda mu: float(np.sum(((mu - y) / sigma) ** 2))
    out = {}
    # A1 interior: bounds [0.1, 10]
    grid = np.array([1.7, 1.8, 2.0, 2.4, 2.5])
    base = chi2(muhat)
    num = optimize.minimize_scalar(chi2, bounds=(0.1, 10), method="bounded",
                                   options={"xatol": 1e-12})
    check("A1 baseline numeric vs closed", abs(num.fun - base) < TOL_CLOSED, num.fun - base)
    d_closed = n * (grid - muhat) ** 2 / sigma ** 2
    d_direct = np.array([chi2(m) for m in grid]) - base
    check("A1 delta closed vs direct", np.max(np.abs(d_closed - d_direct)) < TOL_CLOSED,
          float(np.max(np.abs(d_closed - d_direct))))
    margin_ok(d_closed, "A1")
    out["A1"] = {"y": y.tolist(), "sigma": sigma, "bounds": [0.1, 10.0], "grid": grid.tolist(),
                 "muhat": muhat, "chi2_baseline": base, "delta": d_closed.tolist(),
                 "accepted_grid": grid[d_closed <= CUTOFF95].tolist()}
    # A2 bounds exclude muhat: [2.3, 5]
    lo, hi = 2.3, 5.0
    mut = float(np.clip(muhat, lo, hi))
    base2 = chi2(mut)
    x2, f2 = bvls_chi2(np.ones((n, 1)) / sigma, y / sigma, [lo], [hi])
    check("A2 restricted baseline BVLS vs closed", abs(f2 - base2) < TOL_CLOSED and abs(x2[0] - mut) < 1e-12,
          [f2 - base2, float(x2[0])])
    grid2 = np.array([2.3, 2.5, 2.6, 2.7])
    d2 = n * ((grid2 - muhat) ** 2 - (mut - muhat) ** 2) / sigma ** 2
    d2_direct = np.array([chi2(m) for m in grid2]) - base2
    d2_wrong = n * (grid2 - mut) ** 2 / sigma ** 2   # interior formula misapplied at mu_tilde
    d2_wrong_hat = n * (grid2 - muhat) ** 2 / sigma ** 2  # unrestricted baseline
    check("A2 delta closed vs direct", np.max(np.abs(d2 - d2_direct)) < TOL_CLOSED,
          float(np.max(np.abs(d2 - d2_direct))))
    margin_ok(d2[1:], "A2 (excluding the bound point, delta=0)")
    out["A2"] = {"bounds": [lo, hi], "grid": grid2.tolist(), "mu_tilde": mut,
                 "chi2_baseline_restricted": base2, "delta": d2.tolist(),
                 "accepted_grid": grid2[d2 <= CUTOFF95].tolist(),
                 "interior_formula_with_unrestricted_muhat_WRONG": d2_wrong_hat.tolist(),
                 "interior_formula_centered_at_mu_tilde_WRONG": d2_wrong.tolist()}
    return out


# ---------------------------------------------------------------- Case B ---
def case_b():
    x = np.arange(1.0, 7.0)
    y = np.array([1.32, 1.55, 1.71, 1.98, 2.12, 2.41])
    sigma, n = 0.2, x.size
    X = np.column_stack([np.ones(n), x])
    chi2 = lambda a, b: float(np.sum(((a + b * x - y) / sigma) ** 2))
    xbar, ybar = x.mean(), y.mean()
    sxx = float(np.sum((x - xbar) ** 2))
    bhat = float(np.sum((x - xbar) * (y - ybar)) / sxx)
    ahat = ybar - bhat * xbar
    base = chi2(ahat, bhat)
    ls = np.linalg.lstsq(X, y, rcond=None)[0]
    check("B1 OLS closed vs lstsq", np.max(np.abs(ls - [ahat, bhat])) < 1e-12,
          (ls - [ahat, bhat]).tolist())
    grid = np.array([0.08, 0.12, 0.17, 0.21, 0.24, 0.26, 0.30, 0.34])
    alpha_prof = ybar - grid * xbar
    d_closed = sxx * (grid - bhat) ** 2 / sigma ** 2
    d_direct = np.array([chi2(a, b) for a, b in zip(alpha_prof, grid)]) - base
    check("B1 profile delta closed vs direct", np.max(np.abs(d_closed - d_direct)) < TOL_CLOSED,
          float(np.max(np.abs(d_closed - d_direct))))
    margin_ok(d_closed, "B1")
    out = {"B1": {"x": x.tolist(), "y": y.tolist(), "sigma": sigma,
                  "bounds": {"alpha": [0.01, 5.0], "beta": [0.01, 2.0]},
                  "alpha_hat": ahat, "beta_hat": bhat, "Sxx": sxx, "chi2_baseline": base,
                  "grid_beta": grid.tolist(), "alpha_hat_of_beta": alpha_prof.tolist(),
                  "delta": d_closed.tolist(),
                  "accepted_grid": grid[d_closed <= CUTOFF95].tolist()}}
    check("B1 all profile nuisance interior", bool(np.all((alpha_prof > 0.01) & (alpha_prof < 5))),
          alpha_prof.tolist())

    # B2: bounded nuisance alpha in [1.12, 5]; beta in [0.01, 2]
    alo, ahi, blo, bhi = 1.12, 5.0, 0.01, 2.0
    a_c = np.clip(ybar - grid * xbar, alo, ahi)  # exact: chi2 convex quadratic in alpha
    prof = np.array([chi2(a, b) for a, b in zip(a_c, grid)])
    # restricted baseline: exact bounded linear LS
    bl = optimize.lsq_linear(X / sigma, y / sigma, bounds=([alo, blo], [ahi, bhi]),
                             method="bvls", tol=1e-14)
    base_r = float(2 * bl.cost)
    # explicit derivation: alpha_hat=ahat < alo  -> lower alpha bound active
    b_on_edge = float(np.clip(np.sum(x * (y - alo)) / np.sum(x * x), blo, bhi))
    base_edge = chi2(alo, b_on_edge)
    check("B2 restricted baseline: bvls vs explicit edge solution",
          abs(base_r - base_edge) < 1e-9 and abs(bl.x[1] - b_on_edge) < 1e-9,
          {"bvls": bl.x.tolist(), "edge_beta": b_on_edge})
    d2 = prof - base_r
    # independent numeric profile at each grid point (bounded 1-D minimisation)
    for b, p in zip(grid, prof):
        _, fb = bvls_chi2(np.ones((n, 1)) / sigma, (y - b * x) / sigma, [alo], [ahi])
        check(f"B2 profile beta={b} BVLS vs clip", abs(fb - p) < TOL_CLOSED, fb - p)
    margin_ok(d2, "B2")
    d2_interior_wrong = sxx * (grid - bhat) ** 2 / sigma ** 2
    out["B2"] = {"bounds": {"alpha": [alo, ahi], "beta": [blo, bhi]},
                 "unrestricted_alpha_hat_infeasible": ahat < alo,
                 "restricted_baseline": {"alpha": alo, "beta": b_on_edge, "chi2": base_r},
                 "grid_beta": grid.tolist(), "alpha_restricted_of_beta": a_c.tolist(),
                 "alpha_at_bound": (np.isclose(a_c, alo) | np.isclose(a_c, ahi)).tolist(),
                 "chi2_profile": prof.tolist(), "delta": d2.tolist(),
                 "accepted_grid": grid[d2 <= CUTOFF95].tolist(),
                 "interior_formula_WRONG_here": d2_interior_wrong.tolist()}

    # B3: fixed correlated covariance (AR(1)), algebraic whitening contrast
    rho = 0.5
    idx = np.arange(n)
    Sigma = sigma ** 2 * rho ** np.abs(idx[:, None] - idx[None, :])
    L = np.linalg.cholesky(Sigma)
    Si = np.linalg.inv(Sigma)
    theta_test = np.array([1.0, 0.2])
    e = X @ theta_test - y
    r = np.linalg.solve(L, e)
    check("B3 whitening r^T r == e^T Sigma^-1 e", abs(r @ r - e @ Si @ e) < 1e-9,
          float(r @ r - e @ Si @ e))
    A = X.T @ Si @ X
    gls = np.linalg.solve(A, X.T @ Si @ y)
    cov = np.linalg.inv(A)
    q = lambda th: float((X @ th - y) @ Si @ (X @ th - y))
    base_g = q(gls)
    d3 = []
    for b in grid:
        # profile alpha | beta under Sigma: minimise quadratic in alpha
        a = float((X[:, 0] @ Si @ (y - b * x)) / (X[:, 0] @ Si @ X[:, 0]))
        d3.append(q(np.array([a, b])) - base_g)
    d3 = np.array(d3)
    d3_closed = (grid - gls[1]) ** 2 / cov[1, 1]
    check("B3 GLS profile delta closed vs direct", np.max(np.abs(d3 - d3_closed)) < 1e-9,
          float(np.max(np.abs(d3 - d3_closed))))
    # what a diagonal-sigma (correlation ignored) objective would give at same grid
    out["B3"] = {"rho": rho, "Sigma_definition": "sigma^2 * rho^|i-j|",
                 "theta_test": theta_test.tolist(), "rTr": float(r @ r),
                 "eT_Sigma_inv_e": float(e @ Si @ e), "gls": gls.tolist(),
                 "var_beta_gls": float(cov[1, 1]), "chi2_baseline_gls": base_g,
                 "grid_beta": grid.tolist(), "delta_gls": d3.tolist(),
                 "delta_if_correlation_ignored_diag_sigma": d_closed.tolist(),
                 "note": "algebraic contrast only; LinearBatchObjective supports diagonal sigma only"}
    return out


# ---------------------------------------------------------------- Case C ---
def case_c():
    y = np.array([1.95, 2.08, 2.02, 1.90, 2.05])
    sigma, n = 0.1, y.size
    ybar = y.mean()
    alo, ahi, blo, bhi = 0.5, 4.0, 0.8, 3.0
    chi2 = lambda a, b: float(np.sum(((a * b - y) / sigma) ** 2))
    base = float(np.sum(((ybar - y) / sigma) ** 2))  # attained iff ybar in [alo*blo, ahi*bhi]
    check("C feasible ridge exists", alo * blo <= ybar <= ahi * bhi, [alo * blo, ybar, ahi * bhi])
    grid = np.array([0.5, 0.6, 0.65, 0.7, 1.0, 2.0, 2.5, 2.6, 2.8, 3.0, 4.0])
    bprof = np.clip(ybar / grid, blo, bhi)
    prof = np.array([chi2(a, b) for a, b in zip(grid, bprof)])
    for a, p in zip(grid, prof):
        _, fc = bvls_chi2(np.full((n, 1), a) / sigma, y / sigma, [blo], [bhi])
        check(f"C profile a={a} BVLS vs clip", abs(fc - p) < TOL_CLOSED, fc - p)
    d = prof - base
    margin_ok(d[d > 1e-12], "C (off-ridge points)")
    ridge = [ybar / bhi, ybar / blo]
    out = {"y": y.tolist(), "sigma": sigma, "ybar": ybar,
           "bounds": {"a": [alo, ahi], "b": [blo, bhi]},
           "chi2_min_global_feasible": base,
           "argmin_set": f"{{(a, ybar/a): a in [{ridge[0]}, {ridge[1]}]}}",
           "grid_a": grid.tolist(), "b_hat_of_a": bprof.tolist(),
           "b_at_bound": (np.isclose(bprof, blo) | np.isclose(bprof, bhi)).tolist(),
           "delta": d.tolist(), "accepted_grid": grid[d <= CUTOFF95].tolist(),
           "delta_outside_ridge_formula": "n*(a*b_bound - ybar)^2/sigma^2"}
    # without b-bounds (b in [1e-3, 1e3]) the same grid is entirely flat
    wide = np.clip(ybar / grid, 1e-3, 1e3)
    out["delta_with_wide_b_bounds"] = (np.array([chi2(a, b) for a, b in zip(grid, wide)]) - base).tolist()
    return out


# ------------------------------------------------------- Adverse contract --
def adverse_local_baseline():
    """chi2(t1,t2)=((t1-1)(t1-3))^2+(0.1(t1-3))^2+(t2-1)^2: local basin near 1, global at 3."""
    f = lambda t1: ((t1 - 1) * (t1 - 3)) ** 2 + (0.1 * (t1 - 3)) ** 2
    loc = optimize.minimize_scalar(f, bounds=(0.5, 2.0), method="bounded", options={"xatol": 1e-12})
    h = 1e-5
    curv = (f(loc.x + h) - 2 * f(loc.x) + f(loc.x - h)) / h ** 2
    check("ADV1 local minimum near 1 is strict", curv > 0 and 0.9 < loc.x < 1.1, [loc.x, curv])
    return {"t1_local": float(loc.x), "chi2_local": float(loc.fun), "curvature": float(curv),
            "chi2_global": 0.0, "expected_delta_at_t1_3": -float(loc.fun)}


def demo_closed_form_check():
    """Evaluate (no refit) the closed-form linear batch at reported parameters."""
    base = HERE.parents[2] / "PyFAST" / "runs" / "profile_batch_demo_20261119_release"
    files = {k: base / f"{k}.json" for k in ("specification", "data_0", "data_1", "report")}
    raw = {k: p.read_bytes() for k, p in files.items()}
    data = [json.loads(raw["data_0"]), json.loads(raw["data_1"])]
    rep = json.loads(raw["report"])
    exps = []
    for d in data:
        cfg = json.loads(d["config_json"])
        exps.append({"t": np.array(d["time_s"]), "c": np.array(d["concentration_kg_m3"]),
                     "s": d["sigma_kg_m3"], "beta": cfg["adsorbent_mass_kg"] / cfg["liquid_volume_m3"],
                     "c0": cfg["initial_concentration_kg_m3"]})

    def model(e, K, k):
        ceq = e["c0"] / (1 + e["beta"] * K)
        return ceq + (e["c0"] - ceq) * np.exp(-k * (1 + e["beta"] * K) * e["t"])

    def chi2(K, k):
        return float(sum(np.sum(((model(e, K, k) - e["c"]) / e["s"]) ** 2) for e in exps))

    z = [((e["c"] - model(e, 0.5, 0.02)) / e["s"]).tolist() for e in exps]
    pr = rep["profile"]
    rows = [{"where": "baseline", "params": pr["baseline_parameters"], "reported_chi2": pr["baseline_chi2"],
             "closed_form_chi2": chi2(*pr["baseline_parameters"])}]
    for p in pr["points"]:
        rows.append({"where": f"profile K={p['value']}", "params": p["parameters"],
                     "reported_chi2": p["chi2"], "closed_form_chi2": chi2(*p["parameters"])})
    for r in rows:
        r["closed_minus_reported"] = r["closed_form_chi2"] - r["reported_chi2"]
    calls = sum(t["callback_calls"] for t in pr["baseline_trials"]) + sum(
        t["callback_calls"] for p in pr["points"] for t in p["trials"])
    dz = np.concatenate([np.array(v) for v in z])
    return {
        "sha256": {k: hashlib.sha256(v).hexdigest() for k, v in raw.items()},
        "z_at_truth_K0.5_k0.02": z,
        "chi2_at_truth": chi2(0.5, 0.02),
        "n_observations": int(dz.size),
        "max_abs_z": float(np.max(np.abs(dz))),
        "min_concentration_over_sigma": float(min(np.min(e["c"]) / e["s"] for e in exps)),
        "evaluations_at_reported_parameters": rows,
        "max_abs_closed_minus_reported_chi2": float(max(abs(r["closed_minus_reported"]) for r in rows)),
        "profile_chi2_K0.5_le_chi2_truth": pr["points"][1]["chi2"] <= chi2(0.5, 0.02) + 1e-6,
        "sum_trial_callback_calls": calls, "reported_callback_calls": pr["callback_calls"],
        "reported_physical_solves": rep["physical_solves"],
        "solves_equal_2x_calls": rep["physical_solves"] == 2 * pr["callback_calls"],
        "cutoff_recomputed": CUTOFF95, "cutoff_reported": pr["cutoff"],
        "deltas_recomputed": [p["chi2"] - pr["baseline_chi2"] for p in pr["points"]],
        "deltas_reported": [p["delta_chi2"] for p in pr["points"]],
        "note": "own_oracle evaluation of closed-form truth model at REPORTED parameters; no refit",
    }


def wilson_design():
    z = float(stats.norm.ppf(0.975))
    def half(M, p=0.95):
        den = 1 + z * z / M
        return float(z / den * np.sqrt(p * (1 - p) / M + z * z / (4 * M * M)))
    def need(h, p=0.95):
        M = 10
        while half(M, p) > h:
            M += 1
        return M
    return {"z": z, "p_design": 0.95,
            "half_width": {str(M): half(M) for M in (50, 100, 500, 1000, 1825, 2000)},
            "M_needed": {str(h): need(h) for h in (0.02, 0.015, 0.0135, 0.01)},
            "note": "Wilson score half-width evaluated at hypothesised p=0.95; design precision only"}


def main():
    results = {
        "provenance": "own_oracle",
        "pyfast_imported": "pyfast" in sys.modules,
        "environment": {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__,
                        "platform": platform.platform()},
        "oracle_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cutoff_chi2_1_095": CUTOFF95,
        "A": case_a(), "B": case_b(), "C": case_c(),
        "adverse_local_baseline": adverse_local_baseline(),
        "demo_closed_form": demo_closed_form_check(),
        "wilson_design": wilson_design(),
    }
    check("PyFAST never imported", not any(m.split(".")[0] == "pyfast" for m in sys.modules), "ok")
    results["checks"] = checks
    out = HERE / "oracle_results.json"
    out.write_text(json.dumps(results, indent=2, allow_nan=False, default=lambda o: o.item()) + "\n", encoding="utf-8")
    print(f"{len(checks)} checks passed; wrote {out}")


if __name__ == "__main__":
    main()

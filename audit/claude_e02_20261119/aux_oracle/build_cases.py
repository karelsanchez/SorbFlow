"""Assemble ANALYTIC_REFERENCE_CASES.json from oracle_results.json (own_oracle values).

No PyFAST import. Expected PyFAST-side statuses are `proposed` (derived from reading
profile.py), never observed: PyFAST was not executed in this review.
Usage: python -I build_cases.py
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "oracle_results.json").read_text(encoding="utf-8"))
A, B, C = R["A"], R["B"], R["C"]
CUT = R["cutoff_chi2_1_095"]


def val(v, prov):
    return {"value": v, "provenance": prov}


TOL = {
    "oracle_internal": val({"abs_chi2": 1e-9}, "own_oracle"),
    "oracle_internal_justification": "float64 closed forms vs independent BVLS/lstsq/direct sums; "
        "chi2 magnitudes <= 1e3, so rounding is ~1e-12 relative; 1e-9 absolute leaves margin.",
    "comparison_to_pyfast": val({"abs_chi2_and_delta": "1e-6 + 1e-8*|value|",
                                  "rel_parameters_identified_interior": 1e-5,
                                  "parameters_on_ridge": "not comparable (set-valued argmin)",
                                  "accepted_decision": "exact"}, "proposed"),
    "comparison_justification": "profile.py:156-159 uses ftol=xtol=gtol=1e-10 on 0.5*chi2; "
        "for chi2 <= 1e3 that bounds the optimizer cost error at ~1e-7; 1e-6 matches the default "
        "baseline_tolerance (profile.py:198). All grid points sit >= 0.05 from the cutoff "
        "(checked by the oracle), so accept/reject decisions must match exactly. Bound-active "
        "optima: trf keeps strictly feasible iterates (SciPy docs), so chi2 at an active bound may "
        "exceed the exact restricted minimum by gradient*distance; see A2/B2 notes.",
}


def grid_rows(grid, delta):
    return [{"grid_value": g, "delta_chi2": val(d, "own_oracle"),
             "accepted": val(d <= CUT, "own_oracle")} for g, d in zip(grid, delta)]


cases = []
a1 = A["A1"]
cases.append({
    "id": "A1_gaussian_mean_interior",
    "family": "gaussian_mean_known_sigma",
    "hypotheses": "y_i = mu + sigma*z_i, z_i iid N(0,1), sigma known fixed; mu interior to bounds.",
    "units_scale": "dimensionless (declare unit '1' or any recognised unit consistently); O(1) scale",
    "data": {"y": A["A1"]["y"], "sigma": a1["sigma"], "n": len(A["A1"]["y"])},
    "parameters": [{"name": "mu", "lower": 0.1, "upper": 10.0}],
    "profiled": "mu", "grid": a1["grid"], "starts_proposed": [[0.5], [5.0]],
    "formulas": {"muhat": "mean(y)", "chi2_min": "sum((y-muhat)^2)/sigma^2",
                 "delta": "n*(mu-muhat)^2/sigma^2", "Lambda": "exp(-delta/2)"},
    "expected": {"muhat": val(a1["muhat"], "analytic_derivation"),
                 "chi2_baseline": val(a1["chi2_baseline"], "own_oracle"),
                 "points": grid_rows(a1["grid"], a1["delta"]),
                 "accepted_grid": val(a1["accepted_grid"], "own_oracle"),
                 "edge_status": val(["REJECTED", "REJECTED"], "proposed"),
                 "status": val("COMPLETE", "proposed"),
                 "profile_trials_status": val("EVALUATED (no nuisance)", "proposed")},
    "applicability": "Regular interior case; chi2(1) cutoff exact here because delta is exactly "
                     "chi2(1) at the truth for Gaussian mean with known sigma.",
})
a2 = A["A2"]
cases.append({
    "id": "A2_gaussian_mean_bound_projected",
    "family": "gaussian_mean_known_sigma",
    "hypotheses": "Same data as A1; bounds [2.3, 5] exclude muhat=2.125, so the restricted MLE is "
                  "the projection mu_tilde = clip(muhat, lower, upper).",
    "units_scale": "as A1",
    "data": "same as A1",
    "parameters": [{"name": "mu", "lower": 2.3, "upper": 5.0}],
    "profiled": "mu", "grid": a2["grid"], "starts_proposed": [[2.5], [4.0]],
    "formulas": {"mu_tilde": "clip(muhat, lower, upper)",
                 "chi2_baseline": "chi2_min + n*(mu_tilde-muhat)^2/sigma^2",
                 "delta": "n*[(mu-muhat)^2 - (mu_tilde-muhat)^2]/sigma^2"},
    "expected": {"mu_tilde": val(a2["mu_tilde"], "analytic_derivation"),
                 "chi2_baseline_restricted": val(a2["chi2_baseline_restricted"], "own_oracle"),
                 "points": grid_rows(a2["grid"], a2["delta"]),
                 "accepted_grid": val(a2["accepted_grid"], "own_oracle"),
                 "edge_status": val(["BOUND_LIMITED", "REJECTED"], "proposed"),
                 "bound_limited_point_2.3": val(True, "proposed"),
                 "status": val("COMPLETE, or BASELINE_INCONSISTENT only if the bound-active baseline "
                               "stops more than baseline_tolerance above 3.68 (see note)", "proposed")},
    "wrong_formulas_for_contrast": {
        "interior_formula_with_unrestricted_muhat": val(a2["interior_formula_with_unrestricted_muhat_WRONG"], "own_oracle"),
        "interior_formula_centered_at_mu_tilde": val(a2["interior_formula_centered_at_mu_tilde_WRONG"], "own_oracle")},
    "note": "The grid point 2.3 is evaluated exactly at the bound, the baseline is reached by trf "
            "from the interior: delta(2.3) = -(baseline excess), expected within [-1e-6, 0]. A "
            "larger excess would trigger BASELINE_INCONSISTENT spuriously (finding F12).",
    "applicability": "Truth/estimate at a boundary: chi2(1) cutoff is NOT justified (Chernoff 1954; "
                     "mixture-type limits). Use only as algebraic reference, not for coverage.",
})
b1 = B["B1"]
cases.append({
    "id": "B1_linear_regression_nuisance_interior",
    "family": "linear_regression_known_sigma",
    "hypotheses": "y_i = alpha + beta*x_i + sigma*z_i, sigma known, full-rank design, interior optimum.",
    "units_scale": "x dimensionless 1..6, y O(1); declare consistent units",
    "data": {"x": b1["x"], "y": b1["y"], "sigma": b1["sigma"]},
    "parameters": [{"name": "alpha", "lower": 0.01, "upper": 5.0},
                   {"name": "beta", "lower": 0.01, "upper": 2.0}],
    "profiled": "beta", "grid": b1["grid_beta"], "starts_proposed": [[0.5, 0.05], [3.0, 1.0]],
    "formulas": {"beta_hat": "Sxy/Sxx", "alpha_hat": "ybar - beta_hat*xbar",
                 "alpha_hat_of_beta": "ybar - beta*xbar", "delta": "Sxx*(beta-beta_hat)^2/sigma^2"},
    "expected": {"alpha_hat": val(b1["alpha_hat"], "analytic_derivation"),
                 "beta_hat": val(b1["beta_hat"], "analytic_derivation"),
                 "Sxx": val(b1["Sxx"], "analytic_derivation"),
                 "chi2_baseline": val(b1["chi2_baseline"], "own_oracle"),
                 "alpha_hat_of_beta": val(b1["alpha_hat_of_beta"], "own_oracle"),
                 "points": grid_rows(b1["grid_beta"], b1["delta"]),
                 "accepted_grid": val(b1["accepted_grid"], "own_oracle"),
                 "edge_status": val(["REJECTED", "REJECTED"], "proposed"),
                 "bound_limited_any": val(False, "proposed"), "status": val("COMPLETE", "proposed")},
    "applicability": "Regular interior; delta exactly chi2(1) at truth (linear Gaussian, known sigma).",
})
b2 = B["B2"]
cases.append({
    "id": "B2_linear_regression_bounded_nuisance",
    "family": "linear_regression_known_sigma",
    "hypotheses": "Data as B1; alpha restricted to [1.12, 5] so alpha_hat=1.1053 is infeasible.",
    "data": "same as B1",
    "parameters": [{"name": "alpha", "lower": 1.12, "upper": 5.0},
                   {"name": "beta", "lower": 0.01, "upper": 2.0}],
    "profiled": "beta", "grid": b2["grid_beta"], "starts_proposed": [[1.5, 0.05], [3.0, 1.0]],
    "formulas": {"alpha_restricted_of_beta": "clip(ybar - beta*xbar, alpha_lo, alpha_hi) (exact: chi2 is a convex 1-D quadratic in alpha)",
                 "restricted_baseline": "alpha=alpha_lo, beta=clip(sum(x*(y-alpha_lo))/sum(x^2), beta_lo, beta_hi); confirmed by BVLS",
                 "delta": "chi2(alpha_restricted(beta), beta) - chi2_restricted_baseline"},
    "expected": {"restricted_baseline": val(b2["restricted_baseline"], "own_oracle"),
                 "alpha_restricted_of_beta": val(b2["alpha_restricted_of_beta"], "own_oracle"),
                 "nuisance_at_bound": val(b2["alpha_at_bound"], "own_oracle"),
                 "chi2_profile": val(b2["chi2_profile"], "own_oracle"),
                 "points": grid_rows(b2["grid_beta"], b2["delta"]),
                 "accepted_grid": val(b2["accepted_grid"], "own_oracle"),
                 "edge_status": val(["REJECTED", "REJECTED"], "proposed"),
                 "point_bound_limited": val(b2["alpha_at_bound"], "proposed"),
                 "baseline_bound_parameters": val(["alpha"], "proposed")},
    "wrong_formula_for_contrast": {"interior_formula": val(b2["interior_formula_WRONG_here"], "own_oracle")},
    "applicability": "Nuisance on a bound: test of bound reporting (F02). The chi2(1) cutoff is "
                     "not justified asymptotically here; algebraic reference only.",
})
b3 = B["B3"]
cases.append({
    "id": "B3_fixed_correlated_covariance_whitening",
    "family": "linear_regression_known_covariance",
    "hypotheses": "Same design/data as B1 with fixed known Sigma_ij = sigma^2*rho^|i-j|, rho=0.5. "
                  "Sigma does not depend on parameters, so log det Sigma is constant.",
    "data": "same as B1",
    "formulas": {"whitening": "Sigma = L L^T (Cholesky); r = L^{-1}(h - y); r^T r = (h-y)^T Sigma^{-1} (h-y)",
                 "gls": "theta_hat = (X^T Sigma^-1 X)^-1 X^T Sigma^-1 y",
                 "delta": "(beta - beta_gls)^2 / [(X^T Sigma^-1 X)^-1]_{beta,beta}"},
    "expected": {"rTr_at_theta_test": val(b3["rTr"], "own_oracle"),
                 "quadratic_form_at_theta_test": val(b3["eT_Sigma_inv_e"], "own_oracle"),
                 "theta_test": b3["theta_test"],
                 "gls": val(b3["gls"], "own_oracle"), "var_beta_gls": val(b3["var_beta_gls"], "own_oracle"),
                 "chi2_baseline": val(b3["chi2_baseline_gls"], "own_oracle"),
                 "grid_beta": b3["grid_beta"], "delta_gls": val(b3["delta_gls"], "own_oracle"),
                 "delta_if_correlation_ignored": val(b3["delta_if_correlation_ignored_diag_sigma"], "own_oracle")},
    "applicability": "Algebraic contrast only. profile_gaussian_known_sigma accepts any user-supplied "
                     "whitened residual, so a user could pass L^{-1}(h-y); LinearBatchObjective builds "
                     "diagonal (h-y)/sigma only (batch_objective.py:114-116) and must not be described as "
                     "supporting general covariance. Parameter-dependent Sigma requires the log-det term: "
                     "outside the current API.",
})
cases.append({
    "id": "C1_product_ridge_bounded",
    "family": "product_ridge",
    "hypotheses": "y_i = a*b + sigma*z_i, a,b>0 with finite bounds; only the product ab is identified.",
    "units_scale": "dimensionless, ab ~ 2",
    "data": {"y": C["y"], "sigma": C["sigma"], "ybar": C["ybar"]},
    "parameters": [{"name": "a", "lower": 0.5, "upper": 4.0}, {"name": "b", "lower": 0.8, "upper": 3.0}],
    "profiled": "a", "grid": C["grid_a"], "starts_proposed": [[0.6, 2.5], [3.0, 1.0]],
    "formulas": {"b_hat_of_a": "clip(ybar/a, b_lo, b_hi)",
                 "chi2_min_global_feasible": "sum((y-ybar)^2)/sigma^2, attained on the ridge a*b=ybar, a in [ybar/b_hi, ybar/b_lo]",
                 "delta_off_ridge": C["delta_outside_ridge_formula"]},
    "expected": {"chi2_min_global_feasible": val(C["chi2_min_global_feasible"], "own_oracle"),
                 "argmin_set": val(C["argmin_set"], "analytic_derivation"),
                 "b_hat_of_a": val(C["b_hat_of_a"], "own_oracle"),
                 "nuisance_at_bound": val(C["b_at_bound"], "own_oracle"),
                 "points": grid_rows(C["grid_a"], C["delta"]),
                 "accepted_grid": val(C["accepted_grid"], "own_oracle"),
                 "edge_status": val(["REJECTED", "REJECTED"], "proposed"),
                 "point_bound_limited": val(C["b_at_bound"], "proposed"),
                 "baseline_parameters": val("any point of the ridge; not comparable", "analytic_derivation")},
    "interpretation": "Every rejection in this grid happens where b is pinned at a bound. "
                      "edge_status=REJECTED/REJECTED looks closed, but the closure comes from the bounds of b, "
                      "not from information about a. A perfect fit (delta=0 over the ridge) does not "
                      "identify a and b separately: the likelihood depends on ab only.",
    "variant_wide_b_bounds": {"b_bounds": [1e-3, 1e3],
                              "delta": val(C["delta_with_wide_b_bounds"], "own_oracle"),
                              "edge_status": val(["BOUND_LIMITED", "BOUND_LIMITED"], "proposed"),
                              "accepted_grid": val(C["grid_a"], "own_oracle")},
    "applicability": "Non-identifiable; no chi2(1) calibration applies. Use to test reporting "
                     "(bound flags, edge statuses), never coverage.",
})

adv = R["adverse_local_baseline"]
residual = "r(t) = [(t1-1)*(t1-3), 0.1*(t1-3), t2-1]"
cases.append({
    "id": "ADV1_baseline_inconsistent_local_minimum",
    "family": "adverse_contract",
    "callback": residual,
    "parameters": [{"name": "t1", "lower": 0.5, "upper": 5.0}, {"name": "t2", "lower": 0.5, "upper": 2.0}],
    "starts": [[0.8, 1.5]], "profiled": "t1", "grid": [1.0, 3.0],
    "derivation": {"local_minimum": val({"t1": adv["t1_local"], "t2": 1.0, "chi2": adv["chi2_local"],
                                         "curvature_t1": adv["curvature"]}, "own_oracle"),
                   "global_minimum": val({"t1": 3.0, "t2": 1.0, "chi2": 0.0}, "analytic_derivation")},
    "precondition": "Check that the recorded baseline trial chi2 is ~0.0399. If the optimizer reached "
                    "the global basin, report NOT_EXERCISED, not PASS.",
    "expected_contract": val({"baseline_inconsistent": True, "status": "BASELINE_INCONSISTENT",
                              "delta_chi2_at_3.0": adv["expected_delta_at_t1_3"],
                              "delta_clipped": False, "accepted_all_points": None, "accepted_grid": [],
                              "edge_status": ["UNAVAILABLE", "UNAVAILABLE"]}, "proposed"),
    "code_basis": "profile.py:247-251, 256-257, 265-267, 272",
})
cases.append({
    "id": "ADV2_budget_exhausted_during_baseline",
    "family": "adverse_contract",
    "setup": "B1 data/parameters/starts, max_callback_calls=3",
    "derivation": "least_squares evaluates fun(x0) (call 1), then a 3-point Jacobian needs 2n=4 more "
                  "calls; call 4 is refused (profile.py:104-106).",
    "expected_contract": val({"status": "BUDGET_EXHAUSTED", "budget_exhausted": True, "callback_calls": 3,
                              "baseline_trials": [{"status": "BUDGET_EXHAUSTED", "callback_calls": 3,
                                                   "chi2": "last finite evaluation (not None)"},
                                                  {"status": "BUDGET_EXHAUSTED", "callback_calls": 0}],
                              "baseline_chi2": None, "points_trials": "() for every grid point",
                              "points_chi2": None, "accepted_grid": [],
                              "edge_status": ["UNAVAILABLE", "UNAVAILABLE"]}, "proposed"),
    "code_basis": "profile.py:104-109, 170-176, 239-246, 266-267, 272-275",
    "note": "BUDGET_EXHAUSTED takes precedence over BASELINE_FAILED (profile.py:272-274).",
})
cases.append({
    "id": "ADV3_budget_exhausted_mid_profile",
    "family": "adverse_contract",
    "setup": "B1; phase 1 unlimited run records N_base = sum(baseline trial callback_calls); "
             "phase 2 uses max_callback_calls = N_base + 5 (two-phase so no count is guessed).",
    "expected_contract": val({"status": "BUDGET_EXHAUSTED", "callback_calls": "N_base + 5",
                              "baseline_preserved": True, "some_points_chi2_None": True,
                              "later_trials_callback_calls": 0, "silent_retry": False}, "proposed"),
})
cases.append({
    "id": "ADV4_failed_trial_below_baseline",
    "family": "adverse_contract",
    "callback": residual + "; raises RuntimeError when t1 > 2.9 and t2 != 1.0 (a pure function of theta, not stateful)",
    "parameters": [{"name": "t1", "lower": 0.5, "upper": 5.0}, {"name": "t2", "lower": 0.5, "upper": 2.0}],
    "starts": [[0.8, 1.5], [0.8, 1.0]], "profiled": "t1", "grid": [1.0, 3.0],
    "derivation": "At t1=3, start t2=1.0 evaluates chi2=0 exactly (first call), then the Jacobian "
                  "perturbs t2 and the callback raises: trial ERROR with recorded chi2=0 < baseline 0.0399.",
    "expected_by_current_code": val({"status": "INCOMPLETE", "baseline_inconsistent": False,
                                     "point_3.0_chi2": None, "point_1.0_accepted": True}, "proposed"),
    "recommended_contract": val({"baseline_inconsistent": True,
                                 "reason": "a recorded attained chi2 at a feasible theta is below "
                                           "baseline - tolerance"}, "proposed"),
    "code_basis": "profile.py:170-176, 181-185, 247-251",
    "finding": "F01",
})

out = {
    "title": "E02 independent analytic reference cases",
    "status": "REFERENCE_PROPOSAL; PyFAST NOT executed; expected PyFAST statuses are proposed from code reading",
    "provenance_legend": {"analytic_derivation": "closed form derived by hand",
                          "own_oracle": "computed by aux_oracle/oracle.py (NumPy/SciPy only, no PyFAST)",
                          "proposed": "expected contract/tolerance proposed by this review; not observed"},
    "oracle": {"script": "aux_oracle/oracle.py", "sha256": R["oracle_sha256"],
               "results": "aux_oracle/oracle_results.json",
               "results_sha256": hashlib.sha256((HERE / "oracle_results.json").read_bytes()).hexdigest(),
               "environment": R["environment"], "checks_passed": sum(c["passed"] for c in R["checks"]),
               "checks_total": len(R["checks"])},
    "cutoff_chi2_1_0.95": val(CUT, "own_oracle"),
    "tolerances": TOL,
    "naming_rule": "accepted grid points are NOT confidence intervals",
    "cases": cases,
}
(HERE.parent / "ANALYTIC_REFERENCE_CASES.json").write_text(
    json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print("wrote", HERE.parent / "ANALYTIC_REFERENCE_CASES.json", len(cases), "cases")

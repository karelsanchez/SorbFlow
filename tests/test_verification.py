"""Decision-oriented error control: GCI against the Thomas solution, adaptivity,
constraint classification and censoring."""
from __future__ import annotations

import dataclasses
import json
import math

import numpy as np
import pytest
from scipy import integrate, optimize, special

from sorbflow import HSDM, LDF, Bed, Langmuir, Linear, Operation, SimulationConfig, Species
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions
from sorbflow.verification import (
    BedVolumesAt,
    BreakthroughTime,
    Constraint,
    EffluentAt,
    ExceedanceTime,
    GridRun,
    QuantityValue,
    UsefulCapacity,
    classify,
    classify_report,
    converge,
    estimate_quantities,
    extract,
    mesh_sequence,
    observed_order,
    richardson_estimate,
)

# --------------------------------------------------------------------------------------
# Independent reference: Thomas/Anzelius solution of linear LDF plug flow.
#   eps dc/dt + v dc/dz + rho_b dq/dt = 0,  dq/dt = k (K c - q),  c(0,t) = c_in.
# With tau = t - eps z / v, xi = k rho_b K z / v and y = k tau:  c/c_in = J(xi, y),
#   J(x, y) = 1 - int_0^x exp(-y - s) I0(2 sqrt(y s)) ds,   for tau > 0.
# The integrand is evaluated as ive(0, 2 sqrt(ys)) exp(-(sqrt(y) - sqrt(s))^2).
# --------------------------------------------------------------------------------------


def thomas_j(x: float, y: float) -> float:
    def integrand(s: float) -> float:
        return float(special.ive(0, 2 * math.sqrt(y * s))
                     * math.exp(-(math.sqrt(y) - math.sqrt(s)) ** 2))

    value, _ = integrate.quad(integrand, 0.0, x, limit=200, epsabs=1e-14, epsrel=1e-12)
    return 1.0 - value


def thomas_breakthrough_s(config: SimulationConfig, fraction: float) -> float:
    bed, op = config.bed, config.operation
    assert isinstance(config.equilibrium, Linear) and isinstance(config.kinetics, LDF)
    velocity = op.flow_m3_s / (bed.volume_m3 / bed.length_m)
    k, partition = config.kinetics.rate_s_inv, config.equilibrium.distribution_m3_kg
    xi = k * bed.bulk_density_kg_m3 * partition * bed.length_m / velocity
    delay = bed.porosity * bed.length_m / velocity
    assert math.exp(-xi) < fraction  # front leakage below the level: smooth crossing
    y = optimize.brentq(lambda s: thomas_j(xi, s) - fraction, 1e-12, 10 * xi + 50,
                        xtol=1e-14, rtol=1e-15)
    return delay + y / k


def thomas_config(rate_s_inv: float, duration_s: float = 400.0) -> SimulationConfig:
    return SimulationConfig(
        species=Species(name="thomas-solute"),
        bed=Bed(length_m=0.1, diameter_m=0.01, particle_diameter_m=1e-4, porosity=0.4,
                particle_density_kg_m3=1000.0, material="generic"),
        operation=Operation(flow_m3_s=1e-7, inlet_concentration_kg_m3=0.01,
                            duration_s=duration_s),
        equilibrium=Linear(distribution_m3_kg=0.002),
        kinetics=LDF(rate_s_inv=rate_s_inv),
    )


BASE = SolverOptions(axial_cells=25, rtol=1e-8)


def test_thomas_reference_limits() -> None:
    assert thomas_j(0.0, 3.0) == pytest.approx(1.0)
    assert thomas_j(2.0, 0.0) == pytest.approx(math.exp(-2.0), rel=1e-10)
    # Symmetry of the Thomas function: J(x, y) + J(y, x) = 1 + exp(-x-y) I0(2 sqrt(xy)).
    x, y = 3.0, 5.0
    assert thomas_j(x, y) + thomas_j(y, x) == pytest.approx(
        1 + math.exp(-x - y) * special.i0(2 * math.sqrt(x * y)), rel=1e-10)


# Number of transfer units xi = 4.7 (early leakage), 18.8 and 94.2 (sharp front).
@pytest.mark.parametrize("rate_s_inv", [0.05, 0.2, 1.0])
def test_gci_brackets_true_error_of_thomas_breakthrough(rate_s_inv: float) -> None:
    config = thomas_config(rate_s_inv)
    quantities = [BreakthroughTime(fraction=0.1), BreakthroughTime(fraction=0.5)]
    grids = mesh_sequence(config, quantities, levels=3, options=BASE)
    assert [g.axial_cells for g in grids] == [25, 50, 100]
    reports = estimate_quantities(grids, quantities, formal_order=1.0)
    for quantity, report in zip(quantities, reports, strict=True):
        exact = thomas_breakthrough_s(config, quantity.fraction)
        assert report.value is not None and report.error_bound is not None
        assert report.estimate is not None and report.estimate.asymptotic
        assert report.estimate.convergence == "monotone"
        true_error = abs(report.value - exact)
        # The GCI brackets the true finest-grid error without being vacuous.
        assert true_error <= report.error_bound <= 3.0 * true_error
        # Richardson extrapolation is markedly closer than the finest grid.
        assert report.extrapolated is not None
        assert abs(report.extrapolated - exact) < 0.5 * true_error


def test_adaptive_converge_reaches_tolerance_with_predicted_solves() -> None:
    config = thomas_config(0.2)
    quantities = [BreakthroughTime(fraction=0.1), BreakthroughTime(fraction=0.5)]
    report = converge(config, quantities, rel_tol=0.01, max_cells=3200, budget_solves=8,
                      options=BASE)
    assert report.stop_reason == "converged"
    assert all(q.status == "CONVERGED" for q in report.quantities)
    first_prediction = report.predicted_solves[0]
    assert first_prediction[0] == 3
    assert report.solves_used == first_prediction[1] == 6
    assert [g.axial_cells for g in report.grids] == [25, 50, 100, 200, 400, 800]
    for q in report.quantities:
        assert q.error_bound is not None and q.value is not None
        assert q.error_bound <= q.tolerance
        exact = thomas_breakthrough_s(config, 0.1 if q.key == "t_0.1_s" else 0.5)
        assert abs(q.value - exact) <= q.tolerance
    # Frozen, JSON-serialisable, reproducible fingerprint (manifest/timings excluded).
    data = json.loads(report.to_json())
    assert data["fingerprint"] == report.fingerprint and len(report.fingerprint) == 64
    assert data["sorbflow_version"] == report.sorbflow_version
    assert set(report.manifest.input_sha256) == {g.numerical_sha256 for g in report.grids}
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.solves_used = 0  # type: ignore[misc]


def test_budget_and_max_cells_stop_unconverged() -> None:
    config = thomas_config(0.2)
    quantities = [BreakthroughTime(fraction=0.1)]
    budget = converge(config, quantities, rel_tol=1e-4, budget_solves=4, options=BASE)
    assert budget.stop_reason == "budget_exhausted" and budget.solves_used == 4
    assert budget.quantity("t_0.1_s").status == "NOT_CONVERGED"
    capped = converge(config, quantities, rel_tol=1e-4, max_cells=100, options=BASE)
    assert capped.stop_reason == "max_cells" and capped.solves_used == 3
    again = converge(config, quantities, rel_tol=1e-4, max_cells=100, options=BASE)
    assert again.fingerprint == capped.fingerprint
    assert again.manifest.run_id != capped.manifest.run_id
    two = converge(config, quantities, rel_tol=0.5, min_grids=2, options=BASE)
    estimate = two.quantity("t_0.1_s").estimate
    assert two.solves_used == 2 and estimate is not None
    assert estimate.safety_factor == 3.0 and estimate.convergence == "two_grid"


# ------------------------------- Richardson / GCI ------------------------------------


@pytest.mark.parametrize("order", [1.0, 2.0])
def test_richardson_recovers_exact_power_law(order: float) -> None:
    h = [0.04, 0.02, 0.01]
    values = [3.0 + 5.0 * x**order for x in h]
    estimate = richardson_estimate(values, h, formal_order=order)
    assert estimate.p_observed == pytest.approx(order, rel=1e-10)
    assert estimate.extrapolated == pytest.approx(3.0, abs=1e-12)
    assert estimate.values[0] == values[-1]
    assert estimate.error_bound == pytest.approx(1.25 * 5.0 * 0.01**order, rel=1e-9)


def test_observed_order_nonconstant_ratio() -> None:
    h = [0.01, 0.015, 0.03]
    values = [1.0 + 2.0 * x**1.5 for x in h]
    assert observed_order(values, h) == pytest.approx(1.5, rel=1e-8)


def test_non_asymptotic_sequences_fall_back_conservatively() -> None:
    h = [0.01, 0.02, 0.04]
    oscillatory = richardson_estimate([1.0, 1.1, 0.95], h, formal_order=1.0)
    assert not oscillatory.asymptotic and "oscillatory" in oscillatory.flags
    assert oscillatory.extrapolated == 1.0
    assert oscillatory.error_bound == pytest.approx(3.0 * max(0.1, 0.15 / 2))
    divergent = richardson_estimate([1.0, 1.2, 1.3], h, formal_order=1.0)
    assert divergent.convergence == "divergent" and divergent.error_bound == pytest.approx(0.6)
    high = richardson_estimate([1.0, 1.0 + 1e-4, 1.1], h, formal_order=1.0)
    assert "order_above_band" in high.flags and not high.asymptotic
    assert high.error_bound == pytest.approx(3.0 * 0.0999 / 2)
    flat = richardson_estimate([2.0, 2.0, 2.0], h)
    assert flat.convergence == "grid_independent" and flat.error_bound == 0.0
    with pytest.raises(ValueError, match="formal_order"):
        richardson_estimate([1.0, 1.1], [0.01, 0.02])
    single = richardson_estimate([1.0], [0.01])
    assert single.error_bound is None


# --------------------------------- classification ------------------------------------


def synthetic_grids(phi_exact: float, slope: float, key: str = "t_0.1_s",
                    cells: tuple[int, ...] = (25, 50, 100)) -> tuple[GridRun, ...]:
    """phi(h) = phi_exact + slope h, h = 1/N: exact first-order behaviour."""
    return tuple(GridRun(axial_cells=n, radial_cells=None, h_m=1.0 / n,
                         numerical_sha256="0" * 64, cpu_s=0.0,
                         values=(QuantityValue(key=key, units="s",
                                               value=phi_exact + slope / n),))
                 for n in cells)


def report_for(phi_exact: float, slope: float, cells: tuple[int, ...] = (25, 50, 100)):
    (report,) = estimate_quantities(synthetic_grids(phi_exact, slope, cells=cells),
                                    [BreakthroughTime(fraction=0.1)], formal_order=1.0)
    return report


def test_classification_near_threshold() -> None:
    report = report_for(1000.0, 500.0)  # finest 1005, extrapolated 1000, GCI 6.25
    assert report.value == pytest.approx(1005.0)
    assert report.extrapolated == pytest.approx(1000.0)
    assert report.error_bound == pytest.approx(6.25)

    def status(sense: str, threshold: float) -> str:
        return classify(report, Constraint(quantity_key="t_0.1_s", sense=sense,
                                           threshold=threshold)).status

    assert status(">=", 998.7) == "SATISFIED"
    assert status(">=", 998.8) == "UNDETERMINED"
    assert status(">=", 1011.2) == "UNDETERMINED"
    assert status(">=", 1011.3) == "VIOLATED"
    assert status("<=", 1011.3) == "SATISFIED"
    assert status("<=", 998.7) == "VIOLATED"
    # The exact value always lies on the side the classification implies.
    for threshold in np.linspace(990, 1020, 61):
        decided = status(">=", float(threshold))
        if decided == "SATISFIED":
            assert 1000.0 >= threshold
        elif decided == "VIOLATED":
            assert 1000.0 < threshold


def test_undetermined_recommendation_resolves_decision() -> None:
    threshold = 998.0  # margin 12 s below the finest value 1010; GCI 12.5
    report = report_for(1000.0, 1000.0)  # finest 1010, GCI 12.5
    constraint = Constraint(quantity_key="t_0.1_s", sense=">=", threshold=threshold)
    first = classify(report, constraint)
    assert first.status == "UNDETERMINED" and first.margin == pytest.approx(12.0)
    assert first.recommended_axial_cells == 200
    assert "refine" in first.recommendation
    refined = report_for(1000.0, 1000.0, cells=(50, 100, 200))
    assert classify(refined, constraint).status == "SATISFIED"
    tie = classify(report, Constraint(quantity_key="t_0.1_s", sense=">=", threshold=1010.0))
    assert tie.status == "UNDETERMINED" and tie.recommended_axial_cells is None
    with pytest.raises(ValueError, match="different quantities"):
        classify(report, Constraint(quantity_key="t_0.5_s", sense=">=", threshold=1.0))


# ------------------------------------ censoring --------------------------------------


def test_censoring_is_explicit_and_classified() -> None:
    config = thomas_config(0.2, duration_s=110.0)  # t_10 ~ 88 s, t_50 ~ 123 s
    quantities = [BreakthroughTime(fraction=0.1), BreakthroughTime(fraction=0.5),
                  BedVolumesAt(fraction=0.5), UsefulCapacity(fraction=0.5),
                  ExceedanceTime(limit_kg_m3=0.02)]
    report = converge(config, quantities, rel_tol=0.05, options=BASE, budget_solves=4)
    t10, t50 = report.quantity("t_0.1_s"), report.quantity("t_0.5_s")
    assert t10.status in ("CONVERGED", "NOT_CONVERGED") and t10.value is not None
    for key in ("t_0.5_s", "bv_0.5", "capacity_0.5_kg_kg", "t_exceed_0.02kg_m3_s"):
        entry = report.quantity(key)
        assert entry.status == "CENSORED" and entry.censoring == "right"
        assert entry.value is None and entry.error_bound is None
        assert entry.censored_bound is not None and math.isfinite(entry.censored_bound)
    assert t50.censored_bound == 110.0
    text = report.to_json()
    assert "NaN" not in text and "Infinity" not in text
    assert json.loads(text)["quantities"][1]["status"] == "CENSORED"
    satisfied, violated, unknown = classify_report(report, [
        Constraint(quantity_key="t_0.5_s", sense=">=", threshold=100.0),
        Constraint(quantity_key="t_0.5_s", sense="<=", threshold=100.0),
        Constraint(quantity_key="t_0.5_s", sense=">=", threshold=150.0)])
    assert (satisfied.status, violated.status, unknown.status) == (
        "SATISFIED", "VIOLATED", "UNDETERMINED")
    assert "extend duration_s" in unknown.recommendation


def test_left_censoring_and_mixed_censoring() -> None:
    config = thomas_config(0.2)
    preloaded = dataclasses.replace(config, operation=dataclasses.replace(
        config.operation, initial_concentration_kg_m3=0.005))
    result = column(preloaded, time_s=np.linspace(0, 400, 401), options=BASE)
    (value,) = extract(result, [BreakthroughTime(fraction=0.1)])
    assert value.censoring == "left" and value.value is None and value.bound == 0.0
    grids = synthetic_grids(100.0, 50.0)
    censored = (dataclasses.replace(grids[0], values=(QuantityValue(
        key="t_0.1_s", units="s", value=None, censoring="right", bound=400.0),)),) + grids[1:]
    (report,) = estimate_quantities(censored, [BreakthroughTime(fraction=0.1)],
                                    formal_order=1.0)
    assert report.status == "NOT_CONVERGED" and "coarse_grids_censored" in report.flags
    assert report.estimate is not None and len(report.estimate.values) == 2
    with pytest.raises(ValueError):
        QuantityValue(key="x", units="s", value=float("nan"))


# --------------------------------- quantity contract ---------------------------------


def test_quantity_extraction_consistency() -> None:
    config = thomas_config(0.2)
    result = column(config, time_s=np.linspace(0, 400, 2001), options=BASE)
    t10, bv10, cap10, linear, effluent, exceed = extract(result, [
        BreakthroughTime(fraction=0.1), BedVolumesAt(fraction=0.1),
        UsefulCapacity(fraction=0.1), BreakthroughTime(fraction=0.1, interpolation="linear"),
        EffluentAt(service_time_s=0.0), ExceedanceTime(limit_kg_m3=0.001)])
    assert t10.value is not None and bv10.value is not None and cap10.value is not None
    assert bv10.value == pytest.approx(config.operation.flow_m3_s * t10.value
                                       / config.bed.volume_m3, rel=1e-14)
    assert linear.value == pytest.approx(t10.value, abs=0.2)
    assert exceed.value == pytest.approx(t10.value, rel=1e-12)
    assert effluent.value == pytest.approx(0.0, abs=1e-12)
    # Capacity against an independent trapezoidal effluent integral.
    t = np.asarray(result.time_s)
    c_out = np.asarray(result.outlet_concentration_kg_m3)
    mask = t <= t10.value
    removed = config.operation.flow_m3_s * (config.operation.inlet_concentration_kg_m3
                                            * t10.value - np.trapezoid(c_out[mask], t[mask]))
    adsorbent = config.bed.bulk_density_kg_m3 * config.bed.volume_m3
    assert cap10.value == pytest.approx(removed / adsorbent, rel=2e-3)
    service = EffluentAt(service_time_s=t10.value)
    (at,) = extract(result, [service])
    assert at.value == pytest.approx(0.1 * config.operation.inlet_concentration_kg_m3,
                                     rel=1e-9)
    with pytest.raises(ValueError, match="unique"):
        extract(result, [BreakthroughTime(fraction=0.1), BreakthroughTime(fraction=0.1)])
    with pytest.raises(ValueError, match="duration_s"):
        converge(config, [EffluentAt(service_time_s=500.0)], options=BASE)
    with pytest.raises(ValueError):
        BreakthroughTime(fraction=1.0)


def test_hsdm_sequence_refines_both_directions() -> None:
    config = SimulationConfig(
        species=Species(name="hsdm-solute"),
        bed=Bed(length_m=0.1, diameter_m=0.01, particle_diameter_m=2e-4, porosity=0.4,
                particle_density_kg_m3=1000.0, material="generic"),
        operation=Operation(flow_m3_s=1e-7, inlet_concentration_kg_m3=0.01, duration_s=12000.0),
        equilibrium=Langmuir(qmax_kg_kg=0.002, affinity_m3_kg=100.0),
        kinetics=HSDM(surface_diffusivity_m2_s=1e-11, film_coefficient_m_s=1e-4),
    )
    options = SolverOptions(axial_cells=8, radial_cells=4, rtol=1e-7)
    report = converge(config, [BreakthroughTime(fraction=0.5)], rel_tol=0.2,
                      options=options, budget_solves=3)
    assert report.refine == "both"
    assert [(g.axial_cells, g.radial_cells) for g in report.grids] == [(8, 4), (16, 8), (32, 16)]
    entry = report.quantity("t_0.5_s")
    assert entry.estimate is not None and entry.error_bound is not None
    with pytest.raises(ValueError, match="HSDM"):
        converge(thomas_config(0.2), refine="radial", options=BASE)

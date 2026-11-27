"""Batch HSDM: closed, perfectly mixed liquid + spherical surface diffusion + film."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from sorbflow import HSDM, LDF, BatchConfig, Freundlich, Langmuir, Linear, Species
from sorbflow.equilibrium import isotherm_from_parameters
from sorbflow.io import export_result
from sorbflow.schemas import BatchParticle
from sorbflow.simulate import batch
from sorbflow.solvers import SolverOptions
from sorbflow.validate import mass_balance

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

# Synthetic reference problem: R = 0.25 mm, D_s = 1e-12 m2/s (R^2/D_s = 62 500 s).
RADIUS, DS, VOLUME, MASS, K, C0, RHO = 2.5e-4, 1e-12, 1e-3, 2e-3, 0.5, 0.01, 1000.0
TAU = RADIUS**2 / DS
TIGHT = {"rtol": 1e-10, "atol_concentration_kg_m3": 1e-14, "atol_loading_kg_kg": 1e-15}


def make(**changes):
    config = BatchConfig(
        species=Species(name="synthetic"),
        material="generic-adsorbent",
        liquid_volume_m3=VOLUME,
        adsorbent_mass_kg=MASS,
        duration_s=0.5 * TAU,
        initial_concentration_kg_m3=C0,
        initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=K),
        kinetics=HSDM(surface_diffusivity_m2_s=DS, film_coefficient_m_s=1e3),
        particle=BatchParticle(diameter_m=2 * RADIUS, density_kg_m3=RHO),
        schema_version=2,
    )
    return replace(config, **changes)


# --- Independent reference: Crank (1975), The Mathematics of Diffusion, eq. 6.30 ---
# Sphere of radius a in a well-stirred solution of limited volume, surface always
# in equilibrium with the solution, linear partition. alpha = V_L / (m_s K) is the
# ratio of solute finally in solution to solute finally in the particles.
#   M_t/M_inf = 1 - sum_n 6 alpha (alpha+1) exp(-D q_n^2 t / a^2) / (9 + 9 alpha + q_n^2 alpha^2)
#   tan q_n = 3 q_n / (3 + alpha q_n^2),  q_n in (n pi, n pi + pi/2).


def crank_roots(alpha, count):
    def g(x):  # (3 + alpha x^2) sin x - 3 x cos x: tan equation without poles
        return (3 + alpha * x * x) * np.sin(x) - 3 * x * np.cos(x)

    return np.array(
        [
            brentq(g, n * np.pi, n * np.pi + np.pi / 2, xtol=1e-14, rtol=1e-15)
            for n in range(1, count + 1)
        ]
    )


def crank_uptake(alpha, tau, terms=4000):
    q = crank_roots(alpha, terms)[:, None]
    tau = np.atleast_1d(np.asarray(tau, dtype=float))[None, :]
    series = 6 * alpha * (alpha + 1) * np.exp(-q * q * tau) / (9 + 9 * alpha + q * q * alpha**2)
    return 1 - np.sum(series, axis=0)


def test_crank_reference_self_check():
    alpha = 1.0
    roots = crank_roots(alpha, 50)
    assert_allclose(np.tan(roots), 3 * roots / (3 + alpha * roots**2), rtol=1e-10, atol=1e-12)
    assert np.all(np.diff(roots) > 0)
    # t -> 0: coefficients sum to one (series truncation O(1/terms)).
    assert abs(crank_uptake(alpha, 0.0, terms=20000)[0]) < 1e-4
    # Short times: semi-infinite penetration from a surface at c0,
    # M_t/M_inf -> (1+alpha)/alpha * 6 sqrt(tau/pi), with an O(sqrt(tau)) relative correction.
    tau = np.array([1e-8, 1e-6])
    leading = (1 + alpha) / alpha * 6 * np.sqrt(tau / np.pi)
    deviation = np.abs(crank_uptake(alpha, tau, terms=20000) / leading - 1)
    assert deviation[0] < 1e-3
    assert 5 < deviation[1] / deviation[0] < 20
    # alpha -> infinity recovers the infinite-bath series 1 - 6/pi^2 sum exp(-n^2 pi^2 tau)/n^2.
    tau = np.array([0.02, 0.1, 0.5])
    n = np.arange(1, 4001)[:, None]
    bath = 1 - 6 / np.pi**2 * np.sum(np.exp(-(n**2) * np.pi**2 * tau) / n**2, axis=0)
    assert_allclose(crank_uptake(1e6, tau), bath, rtol=0, atol=1e-5)  # O(1/alpha)
    # Long time: uptake tends to one; monotone in time.
    late = crank_uptake(alpha, np.linspace(0.01, 1, 50))
    assert np.all(np.diff(late) > 0) and abs(crank_uptake(alpha, 5.0)[0] - 1) < 1e-12


def test_linear_negligible_film_against_crank_and_radial_order():
    """Bi = k_f R / (rho_p K D_s) = 5e8: surface equilibrium, Crank eq. 6.30 applies."""
    config = make()
    alpha = VOLUME / (MASS * K)
    times = np.linspace(0, config.duration_s, 101)
    q_inf = K * C0 * VOLUME / (VOLUME + MASS * K)
    exact = crank_uptake(alpha, times[1:] / TAU)
    errors, late = [], []
    for cells in (10, 20, 40, 80):
        result = batch(config, time_s=times, options=SolverOptions(radial_cells=cells, **TIGHT))
        uptake = result.loading_kg_kg[1:, 0] / q_inf
        deviation = np.abs(uptake - exact)
        errors.append(deviation.max())
        late.append(deviation[times[1:] >= 0.05 * TAU].max())
        # Liquid concentration is consistent with the same reference through mass.
        c_exact = C0 - MASS * q_inf * exact / VOLUME
        assert np.max(np.abs(result.concentration_kg_m3[1:, 0] - c_exact)) <= 2 * C0 * errors[-1]
        assert result.diagnostics.max_scaled_mass_residual < 1e-12
    order = np.log2(np.array(errors[:-1]) / np.array(errors[1:]))
    late_order = np.log2(np.array(late[:-1]) / np.array(late[1:]))
    # Measured: max error 3.65e-2, 5.83e-3, 1.35e-3, 3.31e-4 (first sample tau=0.005);
    # tau >= 0.05: 1.88e-4, 4.88e-5, 1.23e-5, 3.09e-6 -> second order.
    assert errors[-1] < 5e-4 and late[-1] < 5e-6
    assert np.all(order > 1.8) and np.all(late_order > 1.8)


@pytest.mark.parametrize("method", ["BDF", "Radau"])
@pytest.mark.parametrize(
    "equilibrium",
    [
        Freundlich(q_ref_kg_kg=0.01, c_ref_kg_m3=0.01, exponent=0.43),
        Langmuir(qmax_kg_kg=0.05, affinity_m3_kg=200),
    ],
    ids=["freundlich-0.43", "langmuir"],
)
@pytest.mark.parametrize("direction", ["adsorption", "desorption"])
def test_nonlinear_adsorption_desorption_mass_and_equilibrium(method, equilibrium, direction):
    c_init, q_init = (C0, 0.0) if direction == "adsorption" else (0.0, 0.004)
    config = make(
        equilibrium=equilibrium,
        initial_concentration_kg_m3=c_init,
        initial_loading_kg_kg=q_init,
        kinetics=HSDM(surface_diffusivity_m2_s=DS, film_coefficient_m_s=1e-5),
        duration_s=4 * TAU,
    )
    result = batch(config, options=SolverOptions(method=method, radial_cells=20))
    c = result.concentration_kg_m3[:, 0]
    q_mean = result.loading_kg_kg[:, 0]
    assert result.diagnostics.max_scaled_mass_residual < 1e-12
    assert mass_balance(result).passed
    assert_allclose(VOLUME * c + MASS * q_mean, VOLUME * c_init + MASS * q_init, rtol=1e-12)
    sign = -1 if direction == "adsorption" else 1
    assert np.all(sign * np.diff(c) >= -1e-7 * C0)  # monotone to solver tolerance
    assert result.diagnostics.min_loading_kg_kg >= 0
    # Long-time limit: the closed-system equilibrium V c + m q*(c) = V c0 + m q0.
    model = isotherm_from_parameters(equilibrium)
    total = VOLUME * c_init + MASS * q_init
    ceq = brentq(lambda x: VOLUME * x + MASS * model.loading(np.array([x]))[0] - total, 0, 1)
    assert_allclose(c[-1], ceq, rtol=1e-5)
    radial = result.radial_loading_kg_kg[-1, 0]
    assert_allclose(radial, model.loading(np.array([ceq]))[0], rtol=1e-4)


def test_both_integrators_agree_for_freundlich():
    config = make(
        equilibrium=Freundlich(q_ref_kg_kg=0.01, c_ref_kg_m3=0.01, exponent=0.43),
        kinetics=HSDM(surface_diffusivity_m2_s=DS, film_coefficient_m_s=1e-5),
    )
    a = batch(config, options=SolverOptions(method="BDF", radial_cells=16, rtol=1e-9))
    b = batch(config, options=SolverOptions(method="Radau", radial_cells=16, rtol=1e-9))
    assert_allclose(a.concentration_kg_m3, b.concentration_kg_m3, rtol=1e-6, atol=1e-11)
    assert_allclose(a.radial_loading_kg_kg, b.radial_loading_kg_kg, rtol=1e-5, atol=1e-11)


@pytest.mark.parametrize(
    "equilibrium",
    [Linear(distribution_m3_kg=K), Freundlich(q_ref_kg_kg=0.01, c_ref_kg_m3=0.01, exponent=0.43)],
    ids=["linear", "freundlich-0.43"],
)
def test_very_fast_surface_diffusion_is_the_film_limited_model(equilibrium):
    """D_s -> infinity: uniform particle at q*(c_s), m_s dq/dt = m_s 3 k_f (c - c_s)/(rho_p R)."""
    kf = 1e-6
    config = make(
        equilibrium=equilibrium,
        kinetics=HSDM(surface_diffusivity_m2_s=1e-6, film_coefficient_m_s=kf),
        duration_s=1e5,
    )
    times = np.linspace(0, config.duration_s, 101)
    result = batch(config, time_s=times, options=SolverOptions(radial_cells=12, rtol=1e-9))
    beta = 3 * kf / (RHO * RADIUS)
    if isinstance(equilibrium, Linear):
        # Equivalent to an LDF on the loading with k = beta / K.
        reference = batch(
            replace(config, kinetics=LDF(rate_s_inv=beta / K), particle=None),
            time_s=times,
            options=SolverOptions(rtol=1e-10),
        ).concentration_kg_m3[:, 0]
    else:
        n, q_ref, c_ref = 0.43, 0.01, 0.01

        def film_only(_t, y):
            c, q = y
            surface = c_ref * (max(q, 0) / q_ref) ** (1 / n)
            rate = beta * (c - surface)
            return [-MASS / VOLUME * rate, rate]

        reference = solve_ivp(
            film_only,
            (0, times[-1]),
            [C0, 0],
            method="Radau",
            t_eval=times,
            rtol=1e-11,
            atol=[1e-15, 1e-15],
        ).y[0]
    radial = result.radial_loading_kg_kg[:, 0]
    assert np.max(np.ptp(radial, axis=1)) < 1e-6 * np.max(radial)
    assert np.max(np.abs(result.concentration_kg_m3[:, 0] - reference)) < 1e-6 * C0


def test_large_film_coefficient_vs_glueckauf_ldf_at_long_times():
    """Qualitative: k_LDF = 15 D_s/R^2 differs early but converges at long times.

    Measured max |c_HSDM - c_LDF| / (c0 - c_eq) by window (40 shells):
    tau < 0.05: 0.24; 0.2-0.5: 0.021; 0.5-1: 3.6e-4; 1-2: 3.5e-7.
    """
    config = make(duration_s=2 * TAU)
    times = np.linspace(0, config.duration_s, 401)
    options = SolverOptions(radial_cells=40, rtol=1e-9)
    hsdm = batch(config, time_s=times, options=options)
    ldf = batch(
        replace(config, kinetics=LDF(rate_s_inv=15 * DS / RADIUS**2)),
        time_s=times,
        options=options,
    )
    ceq = C0 * VOLUME / (VOLUME + MASS * K)
    gap = np.abs(hsdm.concentration_kg_m3[:, 0] - ldf.concentration_kg_m3[:, 0]) / (C0 - ceq)

    def window(a, b):
        return gap[(times >= a * TAU) & (times <= b * TAU)].max()

    assert window(0, 0.05) > 0.1  # LDF misses the sqrt(t) start of diffusion.
    assert window(0.2, 0.5) < 0.05
    assert window(0.5, 1) < 1e-3
    assert window(1, 2) < 1e-5
    assert window(1, 2) < window(0.5, 1) < window(0.2, 0.5)


def test_result_exposes_radial_profile_and_metadata(tmp_path):
    config = make(
        kinetics=HSDM(surface_diffusivity_m2_s=DS, film_coefficient_m_s=1e-5),
        duration_s=3600,
    )
    result = batch(config, time_s=np.linspace(0, 3600, 7), options=SolverOptions(radial_cells=6))
    assert result.reactor == "batch" and result.z_m is None
    assert result.radial_loading_kg_kg.shape == (7, 1, 6)
    assert result.r_m.shape == (6,) and np.all(np.diff(result.r_m) > 0)
    assert result.r_m[-1] < RADIUS
    weights = np.diff(np.linspace(0, RADIUS, 7) ** 3) / RADIUS**3
    assert_allclose(result.loading_kg_kg[:, 0], result.radial_loading_kg_kg[:, 0] @ weights)
    # Surface shell loads first during adsorption.
    assert np.all(np.diff(result.radial_loading_kg_kg[-1, 0]) > 0)
    assert np.all(result.inlet_mass_kg == 0) and np.all(result.outlet_mass_kg == 0)
    data = json.loads(result.to_json())
    assert data["config"]["particle"] == {"density_kg_m3": RHO, "diameter_m": 2 * RADIUS}
    assert np.array(data["radial_loading_kg_kg"]).shape == (7, 1, 6)
    export_result(result, tmp_path / "run")
    assert (tmp_path / "run" / "result.json").exists()
    with pytest.raises(ValueError):
        result.radial_loading_kg_kg[0, 0, 0] = 1


def test_hsdm_batch_rejects_unsupported_numerics():
    config = make(duration_s=10)
    with pytest.raises(ValueError, match="Analytic Jacobian"):
        batch(config, options=SolverOptions(jacobian="analytic"))
    with pytest.raises(ValueError, match="Streaming"):
        batch(config, options=SolverOptions(history="streaming"))


def test_fingerprint_is_reproducible_and_depends_on_particle():
    config = make(duration_s=100)
    a = batch(config, time_s=[0, 100], options=SolverOptions(radial_cells=4))
    b = batch(config, time_s=[0, 100], options=SolverOptions(radial_cells=4))
    other = replace(config, particle=BatchParticle(diameter_m=4e-4, density_kg_m3=RHO))
    c = batch(other, time_s=[0, 100], options=SolverOptions(radial_cells=4))
    assert a.numerical_sha256 == b.numerical_sha256 != c.numerical_sha256
    assert config.sha256 != other.sha256
    assert_allclose(a.radial_loading_kg_kg, b.radial_loading_kg_kg, rtol=0, atol=0)


# --- Schema contract -------------------------------------------------------------


def test_v1_json_still_reads_with_unchanged_canonical_form():
    text = (EXAMPLES / "batch_ldf.json").read_text(encoding="utf-8")
    config = BatchConfig.from_json(text)
    assert config.schema_version == 1 and config.particle is None
    assert "particle" not in json.loads(config.to_json())
    assert config.to_json() == json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))
    assert BatchConfig.from_json(config.to_json()) == config
    data = json.loads(text)
    data["particle"] = None  # The particle key is a v2 field.
    with pytest.raises(ValueError, match="schema v1"):
        BatchConfig.from_json(json.dumps(data))


def test_v2_roundtrip_example_and_ldf_variant():
    text = (EXAMPLES / "batch_hsdm.json").read_text(encoding="utf-8")
    config = BatchConfig.from_json(text)
    assert isinstance(config.kinetics, HSDM) and config.schema_version == 2
    assert BatchConfig.from_json(config.to_json()) == config
    ldf = replace(config, kinetics=LDF(rate_s_inv=0.01), particle=None)
    data = json.loads(ldf.to_json())
    assert data["particle"] is None and data["schema_version"] == 2
    assert BatchConfig.from_json(ldf.to_json()) == ldf
    with_particle = replace(ldf, particle=config.particle)
    assert BatchConfig.from_json(with_particle.to_json()) == with_particle
    result = batch(
        config, time_s=np.linspace(0, config.duration_s, 5), options=SolverOptions(radial_cells=6)
    )
    assert result.diagnostics.max_scaled_mass_residual < 1e-12


def test_schema_rejects_hsdm_without_particle_and_version_mismatch():
    with pytest.raises(ValueError, match="requires particle"):
        make(particle=None)
    with pytest.raises(ValueError, match="schema_version=1"):
        make(schema_version=1)
    with pytest.raises(ValueError, match="schema_version=1"):
        replace(make(kinetics=LDF(rate_s_inv=0.1)), schema_version=1)
    with pytest.raises(ValueError):
        make(schema_version=3)
    with pytest.raises(ValueError, match="particle"):
        make(particle={"diameter_m": 1e-3, "density_kg_m3": 1000})
    for bad in (
        {"diameter_m": 0, "density_kg_m3": 1000},
        {"diameter_m": 1e-3, "density_kg_m3": float("nan")},
        {"diameter_m": -1e-3, "density_kg_m3": 1},
    ):
        with pytest.raises(ValueError):
            BatchParticle(**bad)
    data = json.loads(make().to_json())
    for mutate, match in (
        (lambda d: d.update(particle=None), "requires particle"),
        (lambda d: d.update(schema_version=1), "schema v1"),
        (lambda d: d.pop("particle"), "schema v2"),
        (lambda d: d["particle"].update(extra=1), "Unknown"),
        (lambda d: d.update(schema_version="2"), "schema_version"),
    ):
        broken = json.loads(json.dumps(data))
        mutate(broken)
        with pytest.raises(ValueError, match=match):
            BatchConfig.from_json(json.dumps(broken))
    v1 = json.loads((EXAMPLES / "batch_ldf.json").read_text(encoding="utf-8"))
    v1["kinetics"] = {
        "kind": "hsdm",
        "surface_diffusivity_m2_s": 1e-12,
        "film_coefficient_m_s": 1e-5,
    }
    with pytest.raises(ValueError, match="Unknown model kind"):
        BatchConfig.from_json(json.dumps(v1))

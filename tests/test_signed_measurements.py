from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest
from numpy.testing import assert_allclose

from pyfast import LDF, BatchConfig, Linear, Observations, Species
from pyfast.calibration.batch_objective import BatchExperiment, LinearBatchObjective
from pyfast.calibration.measurements import SignedGaussianMeasurements


def measurements(**changes):
    values = dict(experiment_id="signed", species_name="solute", time_s=(0., 10., 50.),
                  concentration_kg_m3=(-0.0, -0.002, 0.004), std_kg_m3=(0.001,) * 3,
                  source_sha256="0" * 64)
    values.update(changes)
    return SignedGaussianMeasurements(**values)


def config(mass=0.002):
    return BatchConfig(
        species=Species(name="solute"), material="generic", liquid_volume_m3=.001,
        adsorbent_mass_kg=mass, duration_s=100., initial_concentration_kg_m3=.01,
        initial_loading_kg_kg=0., equilibrium=Linear(distribution_m3_kg=.5),
        kinetics=LDF(rate_s_inv=.02),
    )


def test_signed_values_and_negative_zero_are_preserved_bit_exact():
    source = [-0.0, -0.002, np.nextafter(-1., 0.)]
    data = measurements(concentration_kg_m3=source)
    assert np.asarray(data.concentration_kg_m3).tobytes() == np.asarray(source).tobytes()
    source[1] = 99.
    assert data.concentration_kg_m3[1] == -.002
    with pytest.raises(FrozenInstanceError):
        data.species_name = "changed"


def test_existing_observations_still_reject_negatives():
    data = measurements()
    with pytest.raises(ValueError):
        Observations(experiment_id=data.experiment_id, species_name=data.species_name,
                     time_s=data.time_s, concentration_kg_m3=data.concentration_kg_m3,
                     std_kg_m3=data.std_kg_m3, source_sha256=data.source_sha256)


@pytest.mark.parametrize("change", [
    {"time_s": ()}, {"time_s": (-1., 10., 50.)}, {"time_s": (0., 10., 10.)},
    {"time_s": (0., True, 50.)}, {"concentration_kg_m3": (0., np.nan, 1.)},
    {"concentration_kg_m3": (0., np.inf, 1.)}, {"concentration_kg_m3": (0., True, 1.)},
    {"concentration_kg_m3": (0., 1.)}, {"std_kg_m3": None},
    {"std_kg_m3": (1., 0., 1.)}, {"std_kg_m3": (1., -1., 1.)},
    {"std_kg_m3": (1., np.inf, 1.)}, {"std_kg_m3": (1.,)},
    {"experiment_id": " "}, {"species_name": None}, {"source_sha256": "invalid"},
])
def test_invalid_contract_is_rejected(change):
    with pytest.raises(ValueError):
        measurements(**change)


def test_signed_objective_matches_analytic_residuals_and_counts_solves():
    first = measurements()
    second = replace(first, experiment_id="second")
    objective = LinearBatchObjective([
        BatchExperiment(config(), first), BatchExperiment(config(.004), second),
    ])
    expected = []
    for beta, data in [(2., first), (4., second)]:
        times = np.asarray(data.time_s)
        ceq = .01 / (1 + beta * .5)
        predictor = ceq + (.01 - ceq) * np.exp(-.02 * (1 + beta * .5) * times)
        expected.extend((predictor - data.concentration_kg_m3) / data.std_kg_m3)
    before = first.concentration_kg_m3
    assert_allclose(objective([.5, .02]), expected, rtol=1e-8, atol=1e-7)
    assert objective.physical_solves == 2
    assert first.concentration_kg_m3 == before
    objective([.5, .02])
    assert objective.physical_solves == 4
    assert objective.input_hashes[0][2] == first.source_sha256


def test_all_twenty_signed_datasets_are_retained_without_clipping_or_redraw():
    # The generator is a test fixture, not a production coverage driver.
    rng = np.random.default_rng(20261120)
    draws = rng.normal(size=(20, 3))
    expected = .001 + .01 * draws
    datasets = [measurements(experiment_id=f"replica-{i}",
                             concentration_kg_m3=tuple(values), std_kg_m3=(.01,) * 3)
                for i, values in enumerate(expected)]
    assert len(datasets) == 20
    actual = np.array([item.concentration_kg_m3 for item in datasets])
    assert actual.tobytes() == expected.tobytes()
    assert np.any(actual < 0)


def test_signed_batch_contract_keeps_species_and_duration_checks():
    with pytest.raises(ValueError, match="species"):
        BatchExperiment(config(), measurements(species_name="other"))
    with pytest.raises(ValueError, match="duration"):
        BatchExperiment(config(), measurements(time_s=(0., 10., 101.)))

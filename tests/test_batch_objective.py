from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose

from sorbflow import LDF, BatchConfig, Langmuir, Linear, Observations, Species
from sorbflow.calibration.batch_objective import BatchExperiment, LinearBatchObjective
from sorbflow.solvers.integration import SimulationError


def experiment(identity: str = "one", mass: float = 0.002) -> BatchExperiment:
    config = BatchConfig(species=Species(name="test-solute"), material="generic",
                         liquid_volume_m3=0.001, adsorbent_mass_kg=mass, duration_s=300,
                         initial_concentration_kg_m3=0.01, initial_loading_kg_kg=0,
                         equilibrium=Linear(distribution_m3_kg=0.5), kinetics=LDF(rate_s_inv=0.02))
    times = np.array([10.0, 40.0, 100.0])
    beta = mass / config.liquid_volume_m3
    ceq = 0.01 / (1 + beta * 0.5)
    values = ceq + (0.01 - ceq) * np.exp(-0.02 * (1 + beta * 0.5) * times)
    observations = Observations(experiment_id=identity, species_name="test-solute",
                                time_s=tuple(times), concentration_kg_m3=tuple(values),
                                std_kg_m3=(1e-5,) * 3, source_sha256="0" * 64)
    return BatchExperiment(config, observations)


def test_joint_objective_matches_exact_solution_on_observation_times() -> None:
    first, second = experiment(), experiment("two", 0.004)
    original = first.config.to_json()
    objective = LinearBatchObjective((first, second))
    assert objective.physical_solves == 0
    assert_allclose(objective([0.5, 0.02]), np.zeros(6), atol=1e-4)
    assert objective.physical_solves == 2
    assert first.config.to_json() == original
    assert objective.input_hashes[0] == ("one", first.config.sha256, "0" * 64)


def test_known_sigma_weights_are_not_estimated_or_imputed() -> None:
    item = experiment()
    shifted = replace(item.observations, concentration_kg_m3=tuple(
        value + 2e-5 for value in item.observations.concentration_kg_m3))
    objective = LinearBatchObjective((BatchExperiment(item.config, shifted),))
    assert_allclose(objective([0.5, 0.02]), [-2] * 3, atol=1e-4)


@pytest.mark.parametrize("parameters", [[True, 0.02], ["0.5", 0.02], [0, 0.02],
                                        [0.5, -1], [np.nan, 0.02], [[0.5], [0.02]]])
def test_bad_parameters_do_not_attempt_a_physical_solve(parameters: object) -> None:
    objective = LinearBatchObjective((experiment(),))
    with pytest.raises(ValueError):
        objective(parameters)
    assert objective.physical_solves == 0


@pytest.mark.parametrize("change", ["sigma", "species", "time", "model"])
def test_incompatible_data_are_rejected(change: str) -> None:
    item = experiment()
    config, observations = item.config, item.observations
    if change == "sigma":
        observations = replace(observations, std_kg_m3=None)
    elif change == "species":
        observations = replace(observations, species_name="different")
    elif change == "time":
        observations = replace(observations, time_s=(0, 10, 301))
    else:
        config = replace(config, equilibrium=Langmuir(qmax_kg_kg=0.1, affinity_m3_kg=1))
    with pytest.raises(ValueError):
        BatchExperiment(config, observations)


def test_shared_parameters_require_compatible_experiments() -> None:
    first, second = experiment(), experiment("two")
    with pytest.raises(ValueError, match="unique"):
        LinearBatchObjective((first, first))
    for config in (replace(second.config, material="other"),
                   replace(second.config, temperature_k=310)):
        with pytest.raises(ValueError, match="common"):
            LinearBatchObjective((first, BatchExperiment(config, second.observations)))
    with pytest.raises(ValueError):
        LinearBatchObjective(())


def test_failed_physical_attempt_is_still_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise SimulationError("deliberate failure")
    monkeypatch.setattr("sorbflow.calibration.batch_objective.simulate_batch", fail)
    objective = LinearBatchObjective((experiment(),))
    with pytest.raises(SimulationError):
        objective([0.5, 0.02])
    assert objective.physical_solves == 1

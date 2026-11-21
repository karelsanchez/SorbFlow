import json
from dataclasses import replace

import pytest

from sorbflow import LDF, AdsorbentBlend, BatchConfig, BlendComponent, Linear, Species
from sorbflow.solvers import SolverOptions


@pytest.fixture
def batch_config():
    return BatchConfig(
        species=Species(name="any-solute"),
        material="any-material",
        liquid_volume_m3=0.001,
        adsorbent_mass_kg=0.002,
        duration_s=300,
        initial_concentration_kg_m3=0.01,
        initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=0.5),
        kinetics=LDF(rate_s_inv=0.02),
    )


def test_arbitrary_number_of_materials_and_independent_recipe():
    components = [
        BlendComponent(material_id=f"material-{i}", dry_mass_fraction=1 / 7) for i in range(7)
    ]
    blend = AdsorbentBlend(name="seven-component-biochar", components=components)
    components.clear()
    assert len(blend.components) == 7
    assert len(json.loads(blend.to_json())["components"]) == 7
    assert "qmax" not in blend.to_json()  # No unverified parameter mixing law.


@pytest.mark.parametrize(
    "components",
    [
        (),
        ("bad",),
        (BlendComponent(material_id="a", dry_mass_fraction=0.5),),
        (
            BlendComponent(material_id="a", dry_mass_fraction=0.5),
            BlendComponent(material_id="a", dry_mass_fraction=0.5),
        ),
    ],
)
def test_bad_blends(components):
    with pytest.raises(ValueError):
        AdsorbentBlend(name="recipe", components=components)


@pytest.mark.parametrize("fraction", [0, -1, 1.1, True, float("nan")])
def test_bad_fraction(fraction):
    with pytest.raises(ValueError):
        BlendComponent(material_id="x", dry_mass_fraction=fraction)


def test_batch_json_roundtrip_and_linear_column_variant(config, batch_config):
    assert BatchConfig.from_json(batch_config.to_json()) == batch_config
    assert len(batch_config.sha256) == 64
    linear = replace(config, equilibrium=Linear(distribution_m3_kg=0))
    assert type(config).from_json(linear.to_json()) == linear
    data = json.loads(batch_config.to_json())
    data["extra"] = 1
    with pytest.raises(ValueError):
        BatchConfig.from_json(json.dumps(data))
    with pytest.raises(ValueError):
        replace(batch_config, liquid_volume_m3=0)
    with pytest.raises(ValueError):
        replace(batch_config, schema_version=True)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"method": "RK45"},
        {"rtol": 0},
        {"rtol": 1e-18},
        {"rtol": 1},
        {"atol_loading_kg_kg": -1},
        {"mass_reference_kg": 0},
        {"mass_rtol": 1},
        {"max_step_s": float("inf")},
        {"max_step_s": 0},
        {"axial_cells": 1},
        {"axial_cells": True},
    ],
)
def test_bad_solver_options(kwargs):
    with pytest.raises(ValueError):
        SolverOptions(**kwargs)

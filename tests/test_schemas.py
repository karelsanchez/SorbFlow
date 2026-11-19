import json
import math
from dataclasses import FrozenInstanceError, replace

import pytest

from pyfast import (
    HSDM,
    LDF,
    Bed,
    Freundlich,
    Langmuir,
    Observations,
    Operation,
    RunManifest,
    SimulationConfig,
    Species,
    quantity,
)


def test_quantity_factories_and_geometry(config):
    bed = Bed.from_quantities(
        length=quantity(30, "cm"),
        diameter=quantity(2, "cm"),
        particle_diameter=quantity(0.5, "mm"),
        porosity=0.4,
        particle_density=quantity(1.2, "g/cm^3"),
        material="test-material",
    )
    assert bed.particle_density_kg_m3 == pytest.approx(config.bed.particle_density_kg_m3)
    assert bed.length_m == pytest.approx(config.bed.length_m)
    assert bed.diameter_m == pytest.approx(config.bed.diameter_m)
    assert bed.particle_diameter_m == pytest.approx(config.bed.particle_diameter_m)
    assert bed.bulk_density_kg_m3 == pytest.approx(720)
    assert bed.volume_m3 == pytest.approx(math.pi * 0.01**2 * 0.3)
    op = Operation.from_quantities(
        flow=quantity(6, "mL/min"),
        inlet_concentration=quantity(10, "mg/L"),
        duration=quantity(1, "hour"),
        temperature=quantity(25, "degC"),
    )
    assert op.flow_m3_s == pytest.approx(config.operation.flow_m3_s)
    assert op.temperature_k == pytest.approx(298.15)


@pytest.mark.parametrize(
    "name,value",
    [
        ("porosity", 0),
        ("porosity", 1),
        ("porosity", -0.1),
        ("length_m", 0),
        ("diameter_m", -1),
        ("particle_density_kg_m3", math.inf),
        ("particle_diameter_m", 0.1),
        ("mass_basis", "wet"),
        ("material", ""),
        ("porosity", True),
        ("length_m", "0.3"),
    ],
)
def test_bad_bed(config, name, value):
    with pytest.raises(ValueError):
        replace(config.bed, **{name: value})


@pytest.mark.parametrize(
    "name,value",
    [
        ("flow_m3_s", 0),
        ("temperature_k", 0),
        ("duration_s", -1),
        ("inlet_concentration_kg_m3", -1),
        ("axial_dispersion_m2_s", -1),
        ("initial_loading_kg_kg", math.nan),
        ("duration_s", True),
    ],
)
def test_bad_operation(config, name, value):
    with pytest.raises(ValueError):
        replace(config.operation, **{name: value})


@pytest.mark.parametrize(
    "factory,kwargs",
    [
        (Langmuir, {"qmax_kg_kg": 0, "affinity_m3_kg": 1}),
        (Langmuir, {"qmax_kg_kg": 1, "affinity_m3_kg": -1}),
        (Freundlich, {"q_ref_kg_kg": 1, "c_ref_kg_m3": 0, "exponent": 0.5}),
        (Freundlich, {"q_ref_kg_kg": 1, "c_ref_kg_m3": 1, "exponent": math.nan}),
        (LDF, {"rate_s_inv": 0}),
        (HSDM, {"surface_diffusivity_m2_s": 0, "film_coefficient_m_s": 1}),
        (Species, {"name": "x", "molar_mass_kg_mol": -1}),
        (Species, {"name": " "}),
    ],
)
def test_bad_model_parameters(factory, kwargs):
    with pytest.raises(ValueError):
        factory(**kwargs)


def test_config_invariants_and_immutability(config):
    with pytest.raises(FrozenInstanceError):
        config.bed.porosity = 0.5
    with pytest.raises(ValueError):
        replace(config, species={"name": "x"})
    with pytest.raises(ValueError):
        replace(config, operation=replace(config.operation, initial_loading_kg_kg=0.06))
    # A preloaded bed can desorb; do not demand initial liquid/solid equilibrium.
    assert replace(config, operation=replace(config.operation, initial_loading_kg_kg=0.03))


@pytest.mark.parametrize("version", [0, 2, True, "1", 1.0])
def test_schema_versions(config, version):
    with pytest.raises(ValueError):
        replace(config, schema_version=version)


@pytest.mark.parametrize("freundlich", [False, True])
@pytest.mark.parametrize("hsdm", [False, True])
def test_json_roundtrip_hash_and_model_discriminators(config, freundlich, hsdm):
    if freundlich:
        config = replace(
            config, equilibrium=Freundlich(q_ref_kg_kg=0.01, c_ref_kg_m3=1, exponent=0.5)
        )
    if hsdm:
        config = replace(
            config, kinetics=HSDM(surface_diffusivity_m2_s=1e-12, film_coefficient_m_s=1e-5)
        )
    restored = SimulationConfig.from_json(config.to_json())
    assert restored == config
    assert restored.sha256 == config.sha256
    # JSON key order is not scientifically relevant.
    payload = json.dumps(dict(reversed(list(json.loads(config.to_json()).items()))))
    assert SimulationConfig.from_json(payload).sha256 == config.sha256
    assert (
        replace(config, operation=replace(config.operation, duration_s=7200)).sha256
        != config.sha256
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(extra=1),
        lambda d: d.pop("schema_version"),
        lambda d: d["bed"].update(extra=1),
        lambda d: d["equilibrium"].update(kind="other"),
        lambda d: d["kinetics"].update(kind=[]),
        lambda d: d["operation"].update(flow_m3_s="1e-7"),
        lambda d: d["operation"].update(duration_s=float("nan")),
        lambda d: d.update(bed=[]),
        lambda d: d["species"].pop("name"),
    ],
)
def test_invalid_json(config, mutation):
    data = json.loads(config.to_json())
    mutation(data)
    with pytest.raises(ValueError):
        SimulationConfig.from_json(json.dumps(data))


@pytest.mark.parametrize("payload", ["[]", "null", '{"x":1,"x":2}', "{broken"])
def test_nonobject_duplicate_or_malformed_json(payload):
    with pytest.raises(ValueError):
        SimulationConfig.from_json(payload)


def observations(**kwargs):
    defaults = dict(
        experiment_id="synthetic",
        species_name="x",
        time_s=(0, 1),
        concentration_kg_m3=(0, 0.1),
        source_sha256="a" * 64,
        std_kg_m3=(0.01, 0.02),
    )
    return Observations(**(defaults | kwargs))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"time_s": ()},
        {"time_s": (1, 1)},
        {"time_s": (-1, 1)},
        {"concentration_kg_m3": (0,)},
        {"std_kg_m3": (0.01,)},
        {"std_kg_m3": (0, 1)},
        {"concentration_kg_m3": (0, math.inf)},
        {"source_sha256": "bad"},
        {"time_s": "01"},
        {"species_name": ""},
    ],
)
def test_bad_observations(kwargs):
    with pytest.raises(ValueError):
        observations(**kwargs)


def test_observations_copy_mutable_inputs():
    times = [0, 1]
    result = observations(time_s=times, std_kg_m3=None)
    times[0] = -10
    assert result.time_s == (0, 1)
    assert result.std_kg_m3 is None


def manifest(**kwargs):
    defaults = dict(
        run_id="00000000-0000-4000-8000-000000000001",
        created_utc="2026-11-18T12:00:00+00:00",
        config_sha256="a" * 64,
        code_revision="uncommitted",
        python_version="3.11.2",
        package_versions=("pint==0.25", "pyfast-adsorption==0.1.0.dev0"),
        seed=42,
    )
    return RunManifest(**(defaults | kwargs))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"run_id": "invalid"},
        {"created_utc": "2026-11-18T12:00:00"},
        {"created_utc": "2026-11-18T12:00:00-05:00"},
        {"config_sha256": "bad"},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**64},
        {"code_revision": "main"},
        {"package_versions": ()},
        {"package_versions": ("pint",)},
        {"input_sha256": ("bad",)},
        {"package_versions": ("x==1", "x==1")},
        {"package_versions": "x==1"},
        {"python_version": ""},
    ],
)
def test_bad_manifest(kwargs):
    with pytest.raises(ValueError):
        manifest(**kwargs)


def test_manifest_canonical_provenance():
    first = manifest(input_sha256=("b" * 64,), code_revision="a" * 40)
    second = replace(first, package_versions=tuple(reversed(first.package_versions)))
    assert first.to_json() == second.to_json()
    assert json.loads(first.to_json())["seed"] == 42

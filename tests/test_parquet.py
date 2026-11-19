import importlib.util
import json
from dataclasses import replace

import numpy as np
import pytest
from numpy.testing import assert_allclose

from pyfast import LDF, BatchConfig, Linear, Species
from pyfast.io.parquet import export_parquet
from pyfast.simulate import batch, column
from pyfast.solvers import SolverOptions

HAS_ARROW = importlib.util.find_spec("pyarrow") is not None


@pytest.fixture
def batch_result():
    config = BatchConfig(
        species=Species(name="arbitrary-solute"),
        material="arbitrary-material",
        liquid_volume_m3=0.001,
        adsorbent_mass_kg=0.002,
        duration_s=20,
        initial_concentration_kg_m3=0.01,
        initial_loading_kg_kg=0,
        equilibrium=Linear(distribution_m3_kg=0.5),
        kinetics=LDF(rate_s_inv=0.02),
    )
    return batch(config, time_s=[0, 10, 20])


@pytest.mark.skipif(not HAS_ARROW, reason="optional pyarrow is not installed")
@pytest.mark.parametrize("reactor", ["batch", "column"])
def test_parquet_roundtrip_si_units_and_reproducibility_metadata(
    reactor, config, batch_result, tmp_path
):
    import pyarrow as arrow
    from pyarrow import parquet

    result = batch_result
    if reactor == "column":
        config = replace(config, equilibrium=Linear(distribution_m3_kg=0))
        result = column(
            config,
            time_s=[0, 100, config.operation.duration_s],
            options=SolverOptions(axial_cells=6),
        )
    path = export_parquet(result, tmp_path / "nested" / "timeseries.parquet")
    table = parquet.read_table(path)
    expected = {
        "time_s": result.time_s,
        "outlet_concentration_kg_m3": result.outlet_concentration_kg_m3,
        "inventory_kg": result.inventory_kg,
        "inlet_mass_kg": result.inlet_mass_kg,
        "outlet_mass_kg": result.outlet_mass_kg,
        "mass_residual_kg": result.mass_residual_kg,
    }
    assert table.column_names == list(expected)
    assert table.num_rows == 3
    for name, values in expected.items():
        assert_allclose(table.column(name).to_numpy(), values, rtol=0, atol=0)
        assert table.schema.field(name).type == arrow.float64()
        assert not table.schema.field(name).nullable
        assert b"unit" in table.schema.field(name).metadata
    assert table.schema.field("time_s").metadata[b"unit"] == b"s"
    assert table.schema.field("outlet_concentration_kg_m3").metadata[b"unit"] == b"kg/m^3"
    metadata = table.schema.metadata
    assert metadata[b"pyfast.export_schema_version"] == b"1"
    assert metadata[b"pyfast.export_scope"] == b"outlet_timeseries_and_global_mass_balance"
    assert metadata[b"pyfast.reactor"] == reactor.encode()
    assert metadata[b"pyfast.numerical_sha256"].decode() == result.numerical_sha256
    assert json.loads(metadata[b"pyfast.config_json"]) == json.loads(result.config_json)
    assert json.loads(metadata[b"pyfast.solver_options_json"]) == json.loads(result.options_json)
    assert (
        json.loads(metadata[b"pyfast.manifest_json"])["config_sha256"]
        == result.manifest.config_sha256
    )
    assert metadata[b"pyfast.experimental_validation"] == b"not_performed"
    assert "radial_loading_kg_kg" not in table.column_names


def test_parquet_existing_file_is_preserved(batch_result, tmp_path):
    path = tmp_path / "existing.parquet"
    path.write_bytes(b"existing simulation data")
    with pytest.raises(FileExistsError):
        export_parquet(batch_result, path)
    assert path.read_bytes() == b"existing simulation data"


def test_parquet_missing_optional_dependency_is_actionable(batch_result, tmp_path, monkeypatch):
    def unavailable(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("pyfast.io.parquet.import_module", unavailable)
    target = tmp_path / "missing" / "result.parquet"
    with pytest.raises(ImportError, match=r"pyfast-adsorption\[parquet\]"):
        export_parquet(batch_result, target)
    assert not target.exists()
    assert not target.parent.exists()


@pytest.mark.skipif(not HAS_ARROW, reason="optional pyarrow is not installed")
def test_parquet_rejects_inconsistent_vectors_before_creating_file(batch_result, tmp_path):
    malformed = replace(batch_result, inventory_kg=np.array([1.0]))
    path = tmp_path / "bad.parquet"
    with pytest.raises(ValueError, match="matching time_s"):
        export_parquet(malformed, path)
    assert not path.exists()


def test_parquet_requires_simulation_result(tmp_path):
    with pytest.raises(ValueError, match="SimulationResult"):
        export_parquet({}, tmp_path / "bad.parquet")

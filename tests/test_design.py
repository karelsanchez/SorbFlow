import pytest

from sorbflow import Bed
from sorbflow.design import CostBasis, cost_estimate, export_dxf, hydraulics


@pytest.fixture
def bed():
    # Area chosen implicitly through diameter; speed is supplied through Q/A below.
    return Bed(
        length_m=1,
        diameter_m=0.1,
        particle_diameter_m=0.001,
        porosity=0.4,
        particle_density_kg_m3=1200,
        material="arbitrary-material",
    )


def test_ergun_known_pressure_residence_power_and_cost(bed):
    flow = bed.volume_m3 * 0.01
    result = hydraulics(
        bed, flow_m3_s=flow, fluid_density_kg_m3=1000, viscosity_pa_s=0.001, pump_efficiency=0.5
    )
    # At u=0.01 m/s: viscous=8437.5 Pa/m; inertial=1640.625 Pa/m.
    assert result.pressure_drop_pa == pytest.approx(10078.125)
    assert result.ebct_s == pytest.approx(100)
    assert result.liquid_residence_s == pytest.approx(40)
    assert result.pump_power_w == pytest.approx(flow * 10078.125 / 0.5)
    assert result.particle_reynolds == pytest.approx(10)
    prices = CostBasis(
        currency="test_currency", base_year=2026, adsorbent_per_kg=10, electricity_per_kwh=2
    )
    expected = result.dry_adsorbent_mass_kg * 10 + result.pump_power_w / 1000 * 2
    assert cost_estimate(result, prices, service_time_s=3600) == pytest.approx(expected)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"flow_m3_s": 0},
        {"viscosity_pa_s": -1},
        {"fluid_density_kg_m3": True},
        {"pump_efficiency": 1.1},
    ],
)
def test_bad_hydraulics(bed, kwargs):
    defaults = dict(flow_m3_s=1e-6, viscosity_pa_s=0.001, fluid_density_kg_m3=1000) | kwargs
    with pytest.raises(ValueError):
        hydraulics(bed, **defaults)


def test_cad_envelope_dimensions_units_and_no_overwrite(bed, tmp_path):
    import ezdxf

    path = export_dxf(bed, tmp_path / "bed.dxf")
    document = ezdxf.readfile(path)
    assert document.units == 6
    modelspace = document.modelspace()
    assert len(modelspace.query("LINE")) == 4
    circle = modelspace.query("CIRCLE")[0]
    assert circle.dxf.radius == pytest.approx(bed.diameter_m / 2)
    audit = document.audit()
    assert not audit.errors and not audit.fixes
    # Read DXF group-code pairs independently of the exporter's Python structures.
    lines = path.read_text().splitlines()
    pairs = [(int(lines[i]), lines[i + 1]) for i in range(0, len(lines), 2)]
    assert pairs[pairs.index((9, "$INSUNITS")) + 1] == (70, "6")
    assert sum(pair == (0, "LINE") for pair in pairs) == 4
    assert sum(pair == (0, "CIRCLE") for pair in pairs) == 1
    assert (40, str(bed.diameter_m / 2)) in pairs
    assert (21, str(bed.length_m)) in pairs
    assert pairs[-1] == (0, "EOF")
    with pytest.raises(FileExistsError):
        export_dxf(bed, path)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"currency": ""},
        {"base_year": True},
        {"base_year": 1800},
        {"electricity_per_kwh": -1},
    ],
)
def test_cost_basis_is_explicit(kwargs):
    defaults = dict(currency="USD", base_year=2026, adsorbent_per_kg=1, electricity_per_kwh=1)
    with pytest.raises(ValueError):
        CostBasis(**(defaults | kwargs))

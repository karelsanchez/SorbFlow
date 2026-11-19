import pytest

from pyfast import LDF, Bed, Langmuir, Operation, SimulationConfig, Species


@pytest.fixture
def config():
    return SimulationConfig(
        species=Species(name="test-solute", molar_mass_kg_mol=0.1),
        bed=Bed(
            length_m=0.3,
            diameter_m=0.02,
            particle_diameter_m=0.0005,
            porosity=0.4,
            particle_density_kg_m3=1200,
            material="test-material",
        ),
        operation=Operation(flow_m3_s=1e-7, inlet_concentration_kg_m3=0.01, duration_s=3600),
        equilibrium=Langmuir(qmax_kg_kg=0.05, affinity_m3_kg=10),
        kinetics=LDF(rate_s_inv=0.001),
    )

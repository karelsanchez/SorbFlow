"""Create and round-trip a synthetic configuration, without running a solver."""

from pyfast import LDF, Bed, Langmuir, Operation, SimulationConfig, Species, quantity

config = SimulationConfig(
    species=Species(name="synthetic-solute"),
    bed=Bed.from_quantities(
        length=quantity(30, "cm"),
        diameter=quantity(2, "cm"),
        particle_diameter=quantity(0.5, "mm"),
        porosity=0.4,
        particle_density=quantity(1200, "kg/m^3"),
        material="synthetic-adsorbent",
    ),
    operation=Operation.from_quantities(
        flow=quantity(5, "mL/min"),
        inlet_concentration=quantity(10, "mg/L"),
        duration=quantity(8, "hour"),
        temperature=quantity(25, "degC"),
    ),
    equilibrium=Langmuir(qmax_kg_kg=0.05, affinity_m3_kg=10),
    kinetics=LDF(rate_s_inv=0.001),
)
assert SimulationConfig.from_json(config.to_json()) == config
if __name__ == "__main__":
    print(config.to_json())
    print(config.sha256)

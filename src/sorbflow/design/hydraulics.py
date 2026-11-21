"""SI hydraulic design for uniform spherical-particle liquid beds."""

from __future__ import annotations

from dataclasses import dataclass

from ..schemas import Bed
from ..units import finite_scalar


def _positive(value: object, name: str) -> float:
    number = finite_scalar(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


@dataclass(frozen=True, slots=True)
class HydraulicDesign:
    bed_volume_m3: float
    dry_adsorbent_mass_kg: float
    superficial_velocity_m_s: float
    ebct_s: float
    liquid_residence_s: float
    pressure_drop_pa: float
    pump_power_w: float
    particle_reynolds: float
    pump_efficiency: float


def hydraulics(
    bed: Bed,
    *,
    flow_m3_s: float,
    fluid_density_kg_m3: float,
    viscosity_pa_s: float,
    pump_efficiency: float = 1.0,
) -> HydraulicDesign:
    """Ergun pressure drop for a fixed uniform bed, including viscous/inertial terms.

    Fluid properties are supplied, never inferred from a contaminant name. Particle
    shape, wall effects, swelling, fouling and support losses are excluded.
    """
    flow = _positive(flow_m3_s, "flow_m3_s")
    rho = _positive(fluid_density_kg_m3, "fluid_density_kg_m3")
    mu = _positive(viscosity_pa_s, "viscosity_pa_s")
    efficiency = _positive(pump_efficiency, "pump_efficiency")
    if efficiency > 1:
        raise ValueError("pump_efficiency cannot exceed one")
    volume = bed.volume_m3
    speed = flow / (volume / bed.length_m)
    eps, dp = bed.porosity, bed.particle_diameter_m
    gradient = 150 * mu * (1 - eps) ** 2 * speed / (eps**3 * dp**2)
    gradient += 1.75 * rho * (1 - eps) * speed**2 / (eps**3 * dp)
    drop = finite_scalar(gradient * bed.length_m, "pressure_drop_pa")
    return HydraulicDesign(
        volume,
        volume * bed.bulk_density_kg_m3,
        speed,
        volume / flow,
        eps * volume / flow,
        drop,
        flow * drop / efficiency,
        rho * speed * dp / mu,
        efficiency,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class CostBasis:
    """Caller-provided prices; no exchange-rate or market-price assumptions."""

    currency: str
    base_year: int
    adsorbent_per_kg: float
    electricity_per_kwh: float

    def __post_init__(self) -> None:
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise ValueError("currency must be explicit")
        if type(self.base_year) is not int or not 1900 <= self.base_year <= 9999:
            raise ValueError("base_year must be an explicit integer year")
        for name in ("adsorbent_per_kg", "electricity_per_kwh"):
            if finite_scalar(getattr(self, name), name) < 0:
                raise ValueError(f"{name} must be nonnegative")


def cost_estimate(design: HydraulicDesign, prices: CostBasis, *, service_time_s: float) -> float:
    """Adsorbent plus pumping electricity in the stated currency/base year.

    Excludes vessel CAPEX, labor, pretreatment, regeneration/disposal, financing and
    replacement schedules. It is not an economic lifecycle model.
    """
    duration = _positive(service_time_s, "service_time_s")
    energy_kwh = design.pump_power_w * duration / 3.6e6
    return (
        design.dry_adsorbent_mass_kg * prices.adsorbent_per_kg
        + energy_kwh * prices.electricity_per_kwh
    )

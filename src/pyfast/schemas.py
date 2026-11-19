"""Immutable schema v1. Direct constructor fields are explicitly in SI units.

These data contracts describe proposed models; they do not evaluate isotherms,
integrate equations or certify physical validity outside their stated domain.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any, Literal, TypeVar
from uuid import UUID

import pint

from .units import finite_scalar, to_si


def _number(obj: object, name: str, *, positive: bool = False) -> None:
    value = finite_scalar(getattr(obj, name), name)
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'}")
    object.__setattr__(obj, name, value)


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _instance(value: object, cls: type | tuple[type, ...], name: str) -> None:
    if not isinstance(value, cls):
        raise ValueError(f"Invalid {name} type")


def _sha(value: object, name: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")


def _canonical(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _json_object(payload: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    data = json.loads(payload, object_pairs_hook=unique)
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a JSON object")
    return data


@dataclass(frozen=True, slots=True, kw_only=True)
class Species:
    """Solute identity; mass basis is kg of this solute, never inferred ppm."""

    name: str
    molar_mass_kg_mol: float | None = None

    def __post_init__(self) -> None:
        _text(self.name, "name")
        if self.molar_mass_kg_mol is not None:
            _number(self, "molar_mass_kg_mol", positive=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class BlendComponent:
    """One arbitrary adsorbent component, expressed as a dry mass fraction."""

    material_id: str
    dry_mass_fraction: float

    def __post_init__(self) -> None:
        _text(self.material_id, "material_id")
        _number(self, "dry_mass_fraction", positive=True)
        if self.dry_mass_fraction > 1:
            raise ValueError("dry_mass_fraction cannot exceed one")


@dataclass(frozen=True, slots=True, kw_only=True)
class AdsorbentBlend:
    """Recipe metadata only; no mixing law for equilibrium/kinetics is assumed."""

    name: str
    components: tuple[BlendComponent, ...]

    def __post_init__(self) -> None:
        _text(self.name, "name")
        if not isinstance(self.components, (tuple, list)) or not self.components:
            raise ValueError("components must be a nonempty sequence")
        for component in self.components:
            _instance(component, BlendComponent, "component")
        ids = [c.material_id for c in self.components]
        if len(set(ids)) != len(ids):
            raise ValueError("Blend material identifiers must be unique")
        if not math.isclose(
            sum(c.dry_mass_fraction for c in self.components), 1, abs_tol=1e-9, rel_tol=0
        ):
            raise ValueError("Dry mass fractions must sum to one")
        object.__setattr__(self, "components", tuple(self.components))

    def to_json(self) -> str:
        """Serialize recipe provenance; supply fitted properties separately."""
        return _canonical(asdict(self))


@dataclass(frozen=True, slots=True, kw_only=True)
class Bed:
    """Uniform cylindrical bed. Density is dry mass/apparent particle volume."""

    length_m: float
    diameter_m: float
    particle_diameter_m: float
    porosity: float
    particle_density_kg_m3: float
    material: str
    mass_basis: Literal["dry"] = "dry"

    def __post_init__(self) -> None:
        for name in ("length_m", "diameter_m", "particle_diameter_m", "particle_density_kg_m3"):
            _number(self, name, positive=True)
        _number(self, "porosity", positive=True)
        if self.porosity >= 1:
            raise ValueError("porosity must lie strictly between zero and one")
        _text(self.material, "material")
        if self.mass_basis != "dry":
            raise ValueError("Schema v1 supports dry adsorbent mass only")
        if self.particle_diameter_m >= min(self.length_m, self.diameter_m):
            raise ValueError("Particle diameter must be smaller than bed dimensions")

    @classmethod
    def from_quantities(
        cls,
        *,
        length: pint.Quantity[Any],
        diameter: pint.Quantity[Any],
        particle_diameter: pint.Quantity[Any],
        porosity: float,
        particle_density: pint.Quantity[Any],
        material: str,
    ) -> Bed:
        """Normalize dimensional inputs to SI; porosity is a scalar fraction."""
        return cls(
            length_m=to_si(length, "m"),
            diameter_m=to_si(diameter, "m"),
            particle_diameter_m=to_si(particle_diameter, "m"),
            porosity=porosity,
            particle_density_kg_m3=to_si(particle_density, "kg/m^3"),
            material=material,
        )

    @property
    def bulk_density_kg_m3(self) -> float:
        """Dry mass per total bed volume."""
        return (1 - self.porosity) * self.particle_density_kg_m3

    @property
    def volume_m3(self) -> float:
        """Total bed volume, including interparticle voids."""
        return math.pi * self.diameter_m**2 * self.length_m / 4


@dataclass(frozen=True, slots=True, kw_only=True)
class Operation:
    """Constant inlet/flow, uniform initial fields, no thermal equation."""

    flow_m3_s: float
    inlet_concentration_kg_m3: float
    duration_s: float
    temperature_k: float = 298.15
    axial_dispersion_m2_s: float = 0.0
    initial_concentration_kg_m3: float = 0.0
    initial_loading_kg_kg: float = 0.0

    def __post_init__(self) -> None:
        for name in ("flow_m3_s", "duration_s", "temperature_k"):
            _number(self, name, positive=True)
        for name in (
            "inlet_concentration_kg_m3",
            "axial_dispersion_m2_s",
            "initial_concentration_kg_m3",
            "initial_loading_kg_kg",
        ):
            _number(self, name)

    @classmethod
    def from_quantities(
        cls,
        *,
        flow: pint.Quantity[Any],
        inlet_concentration: pint.Quantity[Any],
        duration: pint.Quantity[Any],
        temperature: pint.Quantity[Any],
    ) -> Operation:
        """Construct the common clean-bed case using explicit dimensional inputs."""
        return cls(
            flow_m3_s=to_si(flow, "m^3/s"),
            inlet_concentration_kg_m3=to_si(inlet_concentration, "kg/m^3"),
            duration_s=to_si(duration, "s"),
            temperature_k=to_si(temperature, "K"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Langmuir:
    """Parameter contract only: q*=qmax*b*c/(1+b*c), dry mass basis."""

    qmax_kg_kg: float
    affinity_m3_kg: float
    kind: Literal["langmuir"] = field(default="langmuir", init=False)

    def __post_init__(self) -> None:
        _number(self, "qmax_kg_kg", positive=True)
        _number(self, "affinity_m3_kg", positive=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class Freundlich:
    """Normalized contract q*=q_ref*(c/c_ref)**exponent, no hidden units of K_F."""

    q_ref_kg_kg: float
    c_ref_kg_m3: float
    exponent: float
    kind: Literal["freundlich"] = field(default="freundlich", init=False)

    def __post_init__(self) -> None:
        for name in ("q_ref_kg_kg", "c_ref_kg_m3", "exponent"):
            _number(self, name, positive=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class Linear:
    """Linear equilibrium q*=K*c; K=0 is the nonadsorbing tracer reference."""

    distribution_m3_kg: float
    kind: Literal["linear"] = field(default="linear", init=False)

    def __post_init__(self) -> None:
        _number(self, "distribution_m3_kg")


@dataclass(frozen=True, slots=True, kw_only=True)
class LDF:
    """Effective overall rate. It must not be interpreted as film coefficient."""

    rate_s_inv: float
    kind: Literal["ldf"] = field(default="ldf", init=False)

    def __post_init__(self) -> None:
        _number(self, "rate_s_inv", positive=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class HSDM:
    """Future surface diffusion plus film parameter contract; no solver attached."""

    surface_diffusivity_m2_s: float
    film_coefficient_m_s: float
    kind: Literal["hsdm"] = field(default="hsdm", init=False)

    def __post_init__(self) -> None:
        _number(self, "surface_diffusivity_m2_s", positive=True)
        _number(self, "film_coefficient_m_s", positive=True)


T = TypeVar("T")


def _construct(cls: type[T], data: object) -> T:
    if not isinstance(data, dict):
        raise ValueError(f"{cls.__name__} must be an object")
    allowed = {f.name for f in fields(cls) if f.init}  # type: ignore[arg-type]
    if set(data) - allowed:
        raise ValueError(f"Unknown {cls.__name__} fields: {set(data) - allowed}")
    try:
        return cls(**data)
    except TypeError as exc:
        raise ValueError(f"Invalid {cls.__name__} fields") from exc


def _model(data: object, options: dict[str, type[Any]]) -> Any:
    if not isinstance(data, dict) or not isinstance(data.get("kind"), str):
        raise ValueError("Model requires a string kind discriminator")
    kind = data["kind"]
    if kind not in options:
        raise ValueError(f"Unknown model kind: {kind}")
    return _construct(options[kind], {k: v for k, v in data.items() if k != "kind"})


@dataclass(frozen=True, slots=True, kw_only=True)
class SimulationConfig:
    """Single-species schema v1; deterministic JSON is the public persistence form."""

    species: Species
    bed: Bed
    operation: Operation
    equilibrium: Langmuir | Freundlich | Linear
    kinetics: LDF | HSDM
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("Only integer schema_version=1 is supported")
        for value, cls, name in (
            (self.species, Species, "species"),
            (self.bed, Bed, "bed"),
            (self.operation, Operation, "operation"),
            (self.equilibrium, (Langmuir, Freundlich, Linear), "equilibrium"),
            (self.kinetics, (LDF, HSDM), "kinetics"),
        ):
            _instance(value, cls, name)
        if isinstance(self.equilibrium, Langmuir):
            if self.operation.initial_loading_kg_kg > self.equilibrium.qmax_kg_kg:
                raise ValueError("Initial loading exceeds Langmuir capacity")

    def to_json(self) -> str:
        """Serialize SI data with stable key order, without NaN or Infinity."""
        return _canonical(asdict(self))

    @property
    def sha256(self) -> str:
        """Configuration content hash, excluding run timestamps and identifiers."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, payload: str) -> SimulationConfig:
        """Load strict version-1 JSON; reject unknown fields and model kinds."""

        data = _json_object(payload)
        expected = {f.name for f in fields(cls)}
        if set(data) != expected:
            raise ValueError("Configuration fields must match schema v1 exactly")
        return cls(
            species=_construct(Species, data["species"]),
            bed=_construct(Bed, data["bed"]),
            operation=_construct(Operation, data["operation"]),
            equilibrium=_model(
                data["equilibrium"],
                {"langmuir": Langmuir, "freundlich": Freundlich, "linear": Linear},
            ),
            kinetics=_model(data["kinetics"], {"ldf": LDF, "hsdm": HSDM}),
            schema_version=data["schema_version"],
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class BatchConfig:
    """Closed, perfectly mixed liquid plus dry adsorbent; all fields are SI."""

    species: Species
    material: str
    liquid_volume_m3: float
    adsorbent_mass_kg: float
    duration_s: float
    initial_concentration_kg_m3: float
    initial_loading_kg_kg: float
    equilibrium: Langmuir | Freundlich | Linear
    kinetics: LDF
    temperature_k: float = 298.15
    schema_version: int = 1

    def __post_init__(self) -> None:
        _instance(self.species, Species, "species")
        _instance(self.equilibrium, (Langmuir, Freundlich, Linear), "equilibrium")
        _instance(self.kinetics, LDF, "kinetics")
        _text(self.material, "material")
        for name in ("liquid_volume_m3", "adsorbent_mass_kg", "duration_s", "temperature_k"):
            _number(self, name, positive=True)
        for name in ("initial_concentration_kg_m3", "initial_loading_kg_kg"):
            _number(self, name)
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("Only integer schema_version=1 is supported")
        if isinstance(self.equilibrium, Langmuir):
            if self.initial_loading_kg_kg > self.equilibrium.qmax_kg_kg:
                raise ValueError("Initial loading exceeds Langmuir capacity")

    def to_json(self) -> str:
        """Canonical SI problem description, independent of numerical options."""
        return _canonical(asdict(self))

    @property
    def sha256(self) -> str:
        """SHA-256 of the canonical physical configuration."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, payload: str) -> BatchConfig:
        """Read strict batch schema v1, without dropping unknown data."""
        data = _json_object(payload)
        if set(data) != {f.name for f in fields(cls)}:
            raise ValueError("Batch fields must match schema v1 exactly")
        data["species"] = _construct(Species, data["species"])
        data["equilibrium"] = _model(
            data["equilibrium"], {"langmuir": Langmuir, "freundlich": Freundlich, "linear": Linear}
        )
        data["kinetics"] = _model(data["kinetics"], {"ldf": LDF})
        return cls(**data)


@dataclass(frozen=True, slots=True, kw_only=True)
class Observations:
    """One outlet series; standard deviations refer to concentration measurements.

    Replicates use separate series. Censored observations need a future schema.
    """

    experiment_id: str
    species_name: str
    time_s: tuple[float, ...]
    concentration_kg_m3: tuple[float, ...]
    source_sha256: str
    std_kg_m3: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        _text(self.experiment_id, "experiment_id")
        _text(self.species_name, "species_name")
        _sha(self.source_sha256, "source_sha256")
        for name in ("time_s", "concentration_kg_m3", "std_kg_m3"):
            values = getattr(self, name)
            if name == "std_kg_m3" and values is None:
                continue
            if not isinstance(values, (tuple, list)):
                raise ValueError(f"{name} must be a sequence")
            normalized = tuple(finite_scalar(v, name) for v in values)
            if any(v < 0 or (name == "std_kg_m3" and v == 0) for v in normalized):
                raise ValueError(f"Invalid {name} range")
            object.__setattr__(self, name, normalized)
        if not self.time_s or len(self.time_s) != len(self.concentration_kg_m3):
            raise ValueError("Nonempty matching time and concentration arrays are required")
        if any(b <= a for a, b in zip(self.time_s, self.time_s[1:], strict=False)):
            raise ValueError("Observation times must strictly increase")
        if self.std_kg_m3 is not None and len(self.std_kg_m3) != len(self.time_s):
            raise ValueError("Standard deviations must match observations")


@dataclass(frozen=True, slots=True, kw_only=True)
class RunManifest:
    """Manual provenance contract; creation does not execute a simulation."""

    run_id: str
    created_utc: str
    config_sha256: str
    code_revision: str
    python_version: str
    package_versions: tuple[str, ...]
    seed: int
    input_sha256: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.run_id, "run_id")
        UUID(self.run_id)
        _text(self.created_utc, "created_utc")
        timestamp = datetime.fromisoformat(self.created_utc)
        offset = timestamp.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            raise ValueError("created_utc must include UTC timezone")
        _sha(self.config_sha256, "config_sha256")
        if not isinstance(self.code_revision, str) or (
            self.code_revision != "uncommitted"
            and re.fullmatch(r"[0-9a-f]{7,40}", self.code_revision) is None
        ):
            raise ValueError("code_revision must be a Git hash or 'uncommitted'")
        _text(self.python_version, "python_version")
        if type(self.seed) is not int or self.seed < 0 or self.seed >= 2**64:
            raise ValueError("seed must be an unsigned 64-bit integer")
        for name in ("package_versions", "input_sha256"):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)):
                raise ValueError(f"{name} must be a sequence")
            for value in values:
                if name == "input_sha256":
                    _sha(value, name)
                else:
                    _text(value, name)
                    if re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s=]+", value) is None:
                        raise ValueError("Package versions require name==version")
            if len(set(values)) != len(values):
                raise ValueError(f"Duplicate {name} entries")
            object.__setattr__(self, name, tuple(sorted(values)))
        if not self.package_versions:
            raise ValueError("package_versions must not be empty")

    def to_json(self) -> str:
        """Return canonical run metadata, suitable for archival."""
        return _canonical(asdict(self))

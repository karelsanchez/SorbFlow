import math

import pint
import pytest

from sorbflow import UnitError, quantity, to_si


@pytest.mark.parametrize(
    "value,unit,target,expected",
    [
        (10, "mg/L", "kg/m^3", 0.01),
        (5, "mg/g", "kg/kg", 0.005),
        (1, "mL/min", "m^3/s", 1e-6 / 60),
        (2, "mm", "m", 0.002),
        (2, "hour", "s", 7200),
        (25, "degC", "K", 298.15),
        (1, "L/mg", "m^3/kg", 1000),
        (1, "1/min", "1/s", 1 / 60),
        (1, "cm^2/s", "m^2/s", 1e-4),
    ],
)
def test_known_conversions(value, unit, target, expected):
    assert to_si(quantity(value, unit), target) == pytest.approx(expected)


@pytest.mark.parametrize("unit,target", [("s", "m"), ("mol/L", "kg/m^3"), ("kg", "kg/m^3")])
def test_incompatible_dimensions(unit, target):
    with pytest.raises(UnitError):
        to_si(quantity(1, unit), target)


@pytest.mark.parametrize("value", [True, False, math.nan, math.inf, -math.inf, [1], "2", 1j])
def test_invalid_scalar(value):
    with pytest.raises(ValueError):
        quantity(value, "m")


@pytest.mark.parametrize("unit", ["", "no_such_unit_sorbflow", None])
def test_invalid_unit(unit):
    with pytest.raises(UnitError):
        quantity(1, unit)


def test_bare_scalar_and_nonfinite_external_quantity_rejected():
    with pytest.raises(UnitError):
        to_si(1.0, "m")
    with pytest.raises(ValueError):
        to_si(pint.UnitRegistry().Quantity(math.nan, "m"), "m")


def test_foreign_registry_and_round_trip():
    other = pint.UnitRegistry()
    assert to_si(other.Quantity(3, "cm"), "m") == pytest.approx(0.03)
    q = quantity(10, "mg/L")
    assert quantity(to_si(q, "kg/m^3"), "kg/m^3").to("mg/L").magnitude == pytest.approx(10)

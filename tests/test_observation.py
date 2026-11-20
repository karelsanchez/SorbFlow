"""Analytic checks of causal observation operators, independent of fitted curves."""
import math

import numpy as np
import pytest

from pyfast.observation import (
    CollectionWindow,
    LiquidSegment,
    SampledSignal,
    collection_window,
    fraction_average,
    plug_delay,
)


def test_segment_is_separate_ideal_transport_without_porosity():
    segment = LiquidSegment(7e-6)
    assert segment.residence_time(1e-6) == pytest.approx(7)
    assert LiquidSegment(7e-6, model="none").residence_time(1e-6) == 0
    assert LiquidSegment(0).residence_time(1e-6) == 0
    with pytest.raises(ValueError):
        LiquidSegment(1, model="cstr")
    with pytest.raises(ValueError):
        LiquidSegment(1, position="downstream")


@pytest.mark.parametrize("rule,left,right", [("start", 5, 9), ("mid", 3, 7), ("end", 1, 5)])
def test_collection_assignment(rule, left, right):
    window = collection_window(5, 8, 2, rule=rule)
    assert (window.start_s, window.end_s, window.volume_m3) == (left, right, 8)
    assert not window.flags
    assert collection_window(0, 2, 1).flags == ("WINDOW_STARTS_BEFORE_T0",)


def test_constant_history_and_mass_reference_offset_cancel():
    window = CollectionWindow(-1, 3, 8)
    # Q=2, C=3 for all time: signed cumulative integral, arbitrary origin 17.
    def mass(t):
        return 17 + 6 * t
    assert fraction_average(mass, window, delay_s=5, mass_history=mass) == 3
    assert plug_delay(lambda t: 3, -2, 5, history=lambda t: 3) == 3


def test_step_window_crosses_arrival_without_truncating_volume():
    window = CollectionWindow(0, 10, 20)  # Q=2, C=3, arrival at4.
    assert fraction_average(lambda t: 6*t, window, delay_s=4,
                            initially_at_rest=True) == pytest.approx(1.8)
    assert plug_delay(lambda t: 3, 3.9, 4, initially_at_rest=True) == 0
    assert plug_delay(lambda t: 3, 4, 4, initially_at_rest=True) == 3


def test_pulse_mass_and_causal_history():
    # Q=1, C=2 for t in[0,3], followed by clean carrier, delay5.
    def mass(t):
        return 2 * min(t, 3)
    assert fraction_average(mass, CollectionWindow(0, 10, 10), delay_s=5,
                            initially_at_rest=True) == pytest.approx(.6)
    assert fraction_average(mass, CollectionWindow(0, 4, 4), delay_s=5,
                            initially_at_rest=True) == 0
    assert fraction_average(mass, CollectionWindow(9, 10, 1), delay_s=5) == 0


def test_exponential_reference_and_zero_window_limit():
    def mass(t):
        return -math.expm1(-t)
    for width in (.1, .01, .001):
        mean = fraction_average(mass, CollectionWindow(1-width/2, 1+width/2, width))
        exact = math.exp(-1) * 2 * math.sinh(width/2) / width
        assert mean == pytest.approx(exact, rel=1e-12)
    assert plug_delay(lambda t: math.exp(-t), 1, 0) == pytest.approx(math.exp(-1))


def test_variable_flow_uses_integrated_mass_and_volume_without_mass_shift():
    # Q(t)=1+t, C(t)=2+t. V=integral0to2 Q=4; M=integral0to2(2+3t+t²).
    def mass(t):
        return 2*t + 1.5*t*t + t**3/3
    assert fraction_average(mass, CollectionWindow(0, 2, 4)) == pytest.approx(19/6)


def test_sampled_endpoints_exact_without_interpolation():
    times, values = [0, 1, 2], [0, 3, 6]
    mass = SampledSignal(times, values)
    times[1] = 9
    values[1] = 99
    assert mass(1) == 3
    assert fraction_average(mass, CollectionWindow(0, 2, 2)) == 3
    with pytest.raises(ValueError, match="Missing exact"):
        mass(np.nextafter(1., 2.))
    with pytest.raises(ValueError, match="Missing exact"):
        fraction_average(mass, CollectionWindow(.5, 2, 1.5))


@pytest.mark.parametrize("bad", [True, 1j, float("nan"), float("inf"), [1]])
def test_nonfinite_and_nonreal_rejected(bad):
    with pytest.raises(ValueError):
        LiquidSegment(bad)
    with pytest.raises(ValueError):
        CollectionWindow(0, 1, bad)
    with pytest.raises(ValueError):
        plug_delay(lambda t: 1, bad, 0)


@pytest.mark.parametrize("start,end,volume", [(0,0,1), (2,1,1), (0,1,0), (0,1,-1)])
def test_invalid_windows_rejected(start, end, volume):
    with pytest.raises(ValueError):
        CollectionWindow(start, end, volume)


def test_missing_history_and_bad_signal_rejected():
    with pytest.raises(ValueError, match="Negative time"):
        plug_delay(lambda t: 1, 0, 1)
    with pytest.raises(ValueError, match="Negative time"):
        fraction_average(lambda t: t, CollectionWindow(-1, 1, 2))
    with pytest.raises(ValueError):
        plug_delay(lambda t: 1, 1, -1)
    with pytest.raises(ValueError):
        plug_delay(lambda t: 1, 1, 0, initially_at_rest=1)
    with pytest.raises(ValueError):
        plug_delay(lambda t: float("nan"), 1, 0)
    with pytest.raises(ValueError):
        plug_delay(lambda t: 1, -1, 0, history=lambda t: float("inf"))
    with pytest.raises(ValueError):
        collection_window(1, 1, 1, rule="instant")
    with pytest.raises(ValueError):
        collection_window(1, 1, 0)
    with pytest.raises(ValueError):
        SampledSignal([0, 0], [1, 1])
    with pytest.raises(ValueError):
        SampledSignal([[0]], [1])
    with pytest.raises(ValueError):
        SampledSignal([0], [])

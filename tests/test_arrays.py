import numpy as np
import pytest
from numpy.testing import assert_array_equal

from sorbflow._arrays import real_array


@pytest.mark.parametrize("value", [
    [True, 1.2], [[1.0, False], [2.0, 3.0]], (np.bool_(True), 2),
    [np.array([True, False]), np.array([1.0, 2.0])],
])
def test_mixed_boolean_inputs_are_rejected_before_numpy_coercion(value: object) -> None:
    with pytest.raises(ValueError, match="booleans"):
        real_array(value, "measurement")


def test_real_arrays_keep_shape_and_are_independent_copies() -> None:
    original = np.array([[1, 2], [3, 4]])
    copied = real_array(original, "measurement")
    assert copied.shape == original.shape
    copied[0, 0] = 99
    assert_array_equal(original, [[1, 2], [3, 4]])

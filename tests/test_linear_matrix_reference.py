"""An independently assembled affine matrix verifies the discrete systems."""

import runpy
from pathlib import Path


def test_independent_linear_matrix_exponential_reference():
    source = Path(__file__).parents[1] / "examples" / "linear_matrix_reference.py"
    reference = runpy.run_path(str(source))
    metrics = reference["run_reference"]()
    assert set(metrics) == {"ldf", "hsdm"}
    for result in metrics.values():
        assert result["max_concentration_error_kg_m3"] < 2e-10
        assert result["max_loading_error_kg_kg"] < 2e-12

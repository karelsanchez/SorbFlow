# S1: proposed `SolverOptions.radial_growth` (not applied)

Status: **not applied**. `src/sorbflow/solvers/options.py` is edited in parallel by
another engineer, so the option is only available today through
`SphereGrid(radius_m, cells, growth=...)`. `simulate_hsdm_column` already reads
`getattr(settings, "radial_growth", 1.0)`, so once the field below exists it is
wired, validated by `SphereGrid` and included in the numerical fingerprint
(`result_metadata` hashes `asdict(options)`). Without the field every HSDM run uses
the uniform grid exactly as before.

## Meaning

`radial_growth` is the width ratio of consecutive radial shells from the particle
centre outward. `1.0` (default) is the historical uniform grid, bit for bit.
`0 < radial_growth < 1` refines the shells geometrically toward the surface, where
HSDM gradients are steepest. Shell volumes are exact, so mass conservation is
unchanged.

Measured at equal cell counts (see `tests/test_film_solver.py`):

- Sphere uptake series, t = 0.001..1 (dimensionless), max error of mean loading:
  10 cells 5.0e-2 (uniform) vs 1.5e-2 (0.85); 20 cells 1.9e-2 vs 1.1e-3.
- Freundlich n = 0.43 column (L = 0.1 m, dp = 1 mm, Ds = 1e-14, kf = 2e-5,
  40 axial cells), max outlet error / C0 against 64 uniform radial cells:
  12 cells 4.4e-2 (uniform) vs 9.0e-3 (0.85) vs 6.9e-3 (0.8); runtime +10-20 %.

## Patch to `src/sorbflow/solvers/options.py`

```python
    radial_cells: int = 20
    # HSDM radial shell width ratio, centre -> surface; 1 = uniform (historical).
    radial_growth: float = 1.0
```

and in `__post_init__`, next to the other positive checks:

```python
        # finite_scalar is already imported in options.py.
        if not 0 < finite_scalar(self.radial_growth, "radial_growth") <= 1:
            raise ValueError("radial_growth must satisfy 0 < radial_growth <= 1")
```

Optionally, in `src/sorbflow/reactors/hsdm.py` the `getattr` can then become
`settings.radial_growth`. Tests to add after applying it: `SolverOptions(radial_growth=0)`
raises, and an HSDM column with `radial_growth=0.85` keeps
`max_scaled_mass_residual < 1e-8` and a distinct `numerical_sha256`.

# S3: parche propuesto para CLI y web (batch HSDM, no aplicado)

Estado: **no aplicado**; `cli.py` y `web/` no se editaron en S3.

## CLI (`src/sorbflow/cli.py`)

No hace falta ningún cambio funcional: `BatchConfig.from_json` lee v1 y v2 y
`simulate_batch` despacha a HSDM según `config.kinetics`; `--radial-cells` ya se
transmite a `SolverOptions`. Verificado con
`sorbflow batch examples/batch_hsdm.json --output <dir> --radial-cells 20`.
Cambios cosméticos sugeridos:

- `description="SorbFlow — aqueous LDF simulations in SI"` →
  `"SorbFlow — aqueous LDF/HSDM simulations in SI"` (y el docstring del módulo).
- Ayuda de `--radial-cells`: `"Radial shells for HSDM (column and batch)"`.

## Web (`src/sorbflow/web/config.py`, `parse_request`)

Una petición batch HSDM v2 ya se acepta y se ejecuta (la rama `else` de cinética
valida `surface_diffusivity_m2_s` y `film_coefficient_m_s`), pero `particle` no
tiene comprobación de rango. Añadir en la rama `reactor == "batch"`:

```python
        if config.particle is not None:
            _range(config.particle.diameter_m, "particle diameter_m", 1e-5, 0.1)
            _range(config.particle.density_kg_m3, "particle density_kg_m3", 1, 1e4)
```

(los mismos límites que `Bed.particle_diameter_m` y `Bed.particle_density_kg_m3`
para la columna). Opcional: un cuarto ejemplo en `examples()` con
`kinetics=HSDM(surface_diffusivity_m2_s=1e-12, film_coefficient_m_s=1e-5)`,
`particle=BatchParticle(diameter_m=5e-4, density_kg_m3=1000)`, `schema_version=2`
y `duration_s` del orden de 3.6e4 s (el ejemplo LDF de 300 s es demasiado corto
para $R^2/D_s$ = 6.25e4 s). La vista previa web usa solo la concentración de
salida; `radial_loading_kg_kg` queda en `results/result.json`.

## Exportación pública (no aplicado)

`BatchParticle` se importa desde `sorbflow.schemas`. Si se desea
`from sorbflow import BatchParticle`, añadirlo a `src/sorbflow/__init__.py`
(import y `__all__`), que no es de S3.

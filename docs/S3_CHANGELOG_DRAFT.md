# Borrador de entrada para CHANGELOG.md (S3, no aplicado)

## 0.4.0 (borrador) — HSDM en el reactor batch

- Nuevo: cinética HSDM (difusión superficial homogénea + película externa) en el
  reactor batch cerrado y perfectamente mezclado. Reutiliza `SphereGrid`,
  `diffusion_rhs` y `film_flux` de la columna HSDM (sin cambios en
  `kinetics/sphere.py`). `simulate_batch` despacha según `config.kinetics`; el
  resultado expone `radial_loading_kg_kg` con forma `(tiempo, 1, capas)` y `r_m`,
  y `loading_kg_kg` es la media volumétrica.
- Esquema: `BatchConfig` admite `schema_version` 1 o 2. v1 queda igual (solo LDF,
  sin `particle`; JSON canónico y `sha256` idénticos). v2 añade
  `particle: BatchParticle(diameter_m, density_kg_m3) | None` (siempre
  serializado) y el tipo `hsdm`, que exige `particle`. Errores explícitos para HSDM
  sin partícula, partícula/HSDM con v1 y claves que no coinciden con la versión.
- Conservación: la fuente del líquido es la suma ponderada de las fuentes de las
  capas y el jacobiano por diferencias se ensambla con la misma estructura
  (bloque de difusión exacto, derivadas de película centradas, fila del líquido
  derivada de la conservación). Residuo de masa escalado ~1e-15 frente a ~5e-9 con
  el jacobiano por columnas de SciPy. `jacobian="analytic"` y
  `history="streaming"` se rechazan para batch HSDM.
- Verificación: Crank ec. 6.30 (lineal, película despreciable) con orden radial
  observado ≈ 2 (3.1e-6 con 80 capas para τ ≥ 0.05); Freundlich n = 0.43 y
  Langmuir en adsorción y desorción; límites de película controlante
  ($D_s\to\infty$) y LDF de Glueckauf a tiempos largos. Ver `docs/batch_hsdm.md`.
- `fit_batch_rate` rechaza explícitamente configuraciones batch que no sean LDF.
- Ejemplo sintético `examples/batch_hsdm.json`.

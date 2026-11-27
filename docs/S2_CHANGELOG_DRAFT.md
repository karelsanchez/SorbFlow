# Borrador de CHANGELOG (S2, rama dev-0.4)

## Añadido

- `SolverOptions(axial_scheme="upwind1" | "tvd")`. `"tvd"` es una
  reconstrucción MUSCL con limitador van Albada (segundo orden en zonas suaves,
  LED/positivo para el esquema semidiscreto) para la advección axial de la
  columna LDF. La dispersión sigue siendo central; la entrada de Danckwerts
  (Dirichlet con `D_ax = 0`) y la salida de gradiente nulo se conservan, con
  celdas fantasma de segundo orden. Las masas acumuladas de entrada y salida
  usan los mismos flujos de cara que las celdas: la conservación sigue siendo
  exacta.
- `sorbflow.reactors.column.AxialTransport`: flujos de cara axiales y sus
  derivadas, compartibles con HSDM (parche descrito en `docs/S2_hsdm_patch.md`).
- `sorbflow.reactors.column.effluent_concentration(result)`: concentración de
  la cara de salida (`d(outlet_mass)/dt / Q`); con `tvd` es el efluente de
  segundo orden en `z = L`.
- Jacobiano analítico LDF para `tvd`, con la derivada exacta del limitador, y
  patrón de dispersión ensanchado para diferencias finitas.
- Documentación: `docs/axial_schemes.md` (formulación, verificación Klinkenberg,
  coste, positividad) y una sección nueva en `docs/analytic_jacobian.md`.
- Pruebas: `tests/test_axial_scheme.py` (orden observado ~1 y ~2, LED, frente
  escalón sin extremos nuevos, conservación, Jacobiano frente a un `rhs`
  independiente, flujo de salida) y una variante `tvd` en `tests/test_column.py`.

## Cambiado

- El valor por defecto sigue siendo `axial_scheme="upwind1"` con trayectorias
  idénticas bit a bit. El nuevo campo aparece en `options_json` y entra en
  `numerical_sha256`, por lo que las huellas numéricas cambian respecto a 0.3.x.
- `LDFColumnJacobian(config, cells, transport=None)` acepta un proveedor de
  derivadas de flujo opcional; sin él, el comportamiento no cambia.

## Limitaciones conocidas

- HSDM: `axial_scheme="tvd"` se rechaza con `ValueError` en `simulate_column`
  hasta aplicar el parche en `hsdm.py`. Una llamada directa a
  `simulate_hsdm_column` todavía ignora el campo.
- Con igual número de celdas `tvd` cuesta 2–20 veces más CPU (pasos de tiempo
  más cortos por un frente más empinado); para igual precisión es entre 10 y 30
  veces más barato (Klinkenberg ξ = 20, L∞ ≤ 1e-3: ~70 celdas tvd frente a
  ~4000 upwind1).
- `result.outlet_concentration_kg_m3` sigue siendo la última celda (centrada
  en `L − dz/2`), con error O(dz) frente a `c(L)` en ambos esquemas; usar
  `effluent_concentration` para comparar con soluciones en `z = L`.
- Sin cambios en `atol_concentration_kg_m3` por defecto; se documenta la
  recomendación `atol_c ≈ rtol · c_in`.

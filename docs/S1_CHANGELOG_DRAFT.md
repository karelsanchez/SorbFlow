# Borrador de entrada para CHANGELOG.md (S1, no aplicado)

## 0.4.0 (borrador) — HSDM: acoplamiento película/superficie rápido

- Rendimiento: la condición implícita película/superficie del modelo HSDM
  (`k_f c_s + G q*(c_s) = k_f c + G q_ext`) ya no se resuelve por bisección
  (50–80 evaluaciones validadas de la isoterma por evaluación del lado derecho).
  Lineal: forma cerrada. Langmuir: raíz positiva de la cuadrática con la fórmula sin
  cancelación. Freundlich: Newton en `log c_s` desde una cota superior (convergencia
  monótona; la pendiente `k_f c + n G q*` es finita aunque `dq*/dc` no esté acotada en
  c = 0), típicamente 4–6 evaluaciones. Otras isotermas del protocolo: Newton
  salvaguardado con `derivative()` y bisección (geométrica) como respaldo.
  Toda raíz se certifica como antes (residuo ≤ 512 ε |T| o intervalo cerrado a
  precisión de máquina); el fallo genuino sigue lanzando `SimulationError`.
  Se conservan la continuación impar para estados de prueba y la elección del flujo
  (lado película o lado sólido) con menor cancelación.
  Medido: columna `examples/column_hsdm.json` (100×20 celdas) 4,40 s → 0,88 s (mediana de 3; ×5,0);
  columna Freundlich n = 0,43 (40×12) 14,4 s → 0,93 s (×15,5). Curvas de salida idénticas
  a la versión 0.3.1 con error absoluto ≤ 3,6e-15 kg/m3 (relativo ≤ 6e-11 donde c > 1e-3 C0) (mismo número de evaluaciones del integrador).
- Núcleos internos sin validación (`_loading_unchecked`, `_derivative_unchecked`,
  `equilibrium.isotherms._loading_kernel`) para bucles internos; `loading()` y
  `derivative()` públicos validan exactamente como antes y devuelven los mismos valores.
- `SphereGrid` precalcula caras, centros, volúmenes y pesos (las propiedades públicas
  devuelven copias) y admite `growth` (0 < growth ≤ 1): refinamiento geométrico de las
  capas hacia la superficie con volúmenes exactos y conservación de masa. Por defecto
  `growth = 1` (malla uniforme, idéntica a la anterior). Con 12 celdas radiales y
  `growth = 0,85`, el error de la curva de salida de la columna Freundlich frente a una
  referencia de 64 celdas uniformes baja de 4,4e-2 a 9,0e-3 C0. La opción a nivel de
  `SolverOptions` (`radial_growth`) está propuesta en `docs/S1_options_patch.md`.
- Pruebas nuevas `tests/test_film_solver.py`: comparación con `scipy.optimize.brentq`
  para lineal, Langmuir y Freundlich (n = 0,3–1,5), magnitudes 1e-30–1e-1, adsorción,
  desorción y estados de prueba negativos o de signo mixto; isotermas genéricas con y
  sin derivada; número de evaluaciones; malla refinada.

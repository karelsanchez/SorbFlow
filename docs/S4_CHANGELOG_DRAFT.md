# Borrador de entrada para CHANGELOG.md (S4, no aplicado)

## 0.4.0 (borrador) — Control del error numérico orientado a decisiones

- Nuevo paquete `sorbflow.verification` (solo usa la API pública
  `sorbflow.simulate.column` y `SolverOptions`; no cambia ningún reactor):
  - Magnitudes de decisión con interpolación documentada (PCHIP monótono por
    defecto, lineal opcional) y censura explícita (`right`/`left`, nunca NaN):
    `BreakthroughTime` (`t_x`), `BedVolumesAt` (`Q t_x / V_lecho`),
    `UsefulCapacity` (`(M_in − M_out)(t_x)/(ρ_b V_lecho)`), `EffluentAt`
    (`C_eff(t_servicio)`), `ExceedanceTime` (primer cruce de un límite).
  - `richardson_estimate` / `observed_order`: orden observado (iteración de
    Celik et al. para razones no constantes), extrapolación de Richardson y GCI
    de Roache (`F_s = 1.25` con ≥3 mallas, `3` con 2 mallas y orden formal);
    detección de secuencias oscilatorias, divergentes u órdenes fuera de banda
    con cota conservadora `3·max(|ε21|, |ε32|/r^p_formal)`.
  - `mesh_sequence` y `converge`: secuencias geométricas axiales (y radiales en
    HSDM), refinamiento hasta `max(abs_tol, rel_tol·|φ|)` con límites
    `budget_solves`/`max_cells` y predicción del número de resoluciones.
    `ConvergenceReport` congelado y serializable a JSON canónico, con estado por
    magnitud (`CONVERGED`/`NOT_CONVERGED`/`CENSORED`), CPU, versión,
    `RunManifest` y huella SHA-256 del contenido reproducible.
  - `Constraint`, `classify`, `classify_report`: clasificación
    `SATISFIED`/`VIOLATED`/`UNDETERMINED` de restricciones de diseño con la banda
    de error, y malla recomendada cuando la decisión queda indeterminada.
- Validación frente a la solución analítica de Thomas (LDF lineal, flujo pistón)
  con referencia independiente en la prueba: el GCI acota el error verdadero de
  `t_10` y `t_50` en la malla más fina en ξ = 4.7, 18.8 y 94.2 (GCI/error
  1.33–1.69 con 25/50/100 celdas; 1.27–1.51 con 100/200/400).
- Documentación `docs/decision_error_control.md`; ejemplo
  `examples/decision_error_control.py`; pruebas `tests/test_verification.py`.
- Pendiente de integración: añadir `docs/decision_error_control.md` a la
  navegación de `mkdocs.yml`.

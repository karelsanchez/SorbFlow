# Registro de cambios

## 0.4.0 — 2026-11-27

**Rendimiento y exactitud**

- HSDM: la condición película–superficie se resuelve en forma cerrada (lineal, Langmuir) o
  por Newton en log c_s (Freundlich, incluido exponente < 1), con Newton salvaguardado para
  cualquier otra isoterma. Las curvas coinciden con 0.3.1 hasta 1e-15 y el cálculo es entre
  5 y 15 veces más rápido.
- Esquema axial de alta resolución `SolverOptions(axial_scheme="tvd")`: reconstrucción
  MUSCL con limitador van Albada, segundo orden en zonas suaves, sin nuevos extremos y con
  conservación exacta, para columnas LDF y HSDM, con Jacobiano analítico LDF que incluye la
  derivada del limitador. En la referencia de Thomas–Klinkenberg alcanza un error de 1e-3
  con unas 70 celdas frente a unas 4.000 del esquema de primer orden. El valor por defecto
  sigue siendo `"upwind1"`, idéntico bit a bit.
- Malla radial refinada hacia la superficie (`radial_growth`, por defecto 1 = uniforme):
  con las mismas capas el error radial baja unas cinco veces.
- `effluent_concentration(result)`: concentración en la cara de salida (z = L).

**Nuevas capacidades**

- HSDM en el reactor batch. `BatchConfig` versión 2 con `BatchParticle` (diámetro y
  densidad de partícula); los archivos de versión 1 se leen y se firman igual que antes.
  Verificado frente a la solución de Crank para esferas en un volumen limitado (orden
  radial ≈ 2, residuo de masa ≈ 1e-15).
- `sorbflow.verification`: control del error numérico orientado a la decisión. Extrae
  cantidades de diseño (tiempo de ruptura, volúmenes de lecho, capacidad útil, efluente en
  el tiempo de servicio, tiempo de superación de un límite) con censura explícita; estima
  su error de discretización por extrapolación de Richardson y el índice de convergencia
  de malla (GCI); refina de forma adaptativa hasta una tolerancia; y clasifica cada
  restricción de diseño como cumplida, incumplida o indeterminada. En la referencia de
  Thomas–Klinkenberg el GCI cubrió el error real de t₁₀ y t₅₀ en todos los regímenes.
- CLI: opciones `--axial-scheme` y `--radial-growth`; la interfaz local valida los
  parámetros de partícula del batch HSDM.

**Compatibilidad**

- Las opciones nuevas forman parte de `numerical_sha256`: las huellas numéricas cambian
  respecto a 0.3.x aunque los resultados con las opciones por defecto no cambien.
- Incluye la corrección de 0.3.1 (HSDM con Freundlich de exponente < 1).

## 0.3.1 — 2026-11-22

- Corrección: el modelo HSDM de columna podía abortar con "Film/surface equilibrium root
  did not converge" cuando la isoterma de Freundlich tiene exponente menor que 1. Cerca de
  c = 0 la pendiente dq*/dc no está acotada y la tolerancia en el residuo no era alcanzable
  aunque la raíz ya estuviera determinada. Ahora la raíz, siempre acotada por una función
  monótona, se acepta también cuando el intervalo de bisección se cierra a precisión de
  máquina. Los resultados de casos que ya convergían no cambian.
- Pruebas de regresión con exponentes 0,3–0,6 frente a una raíz independiente y una columna
  HSDM con exponente 0,43.

## 0.3.0 — SorbFlow, 2026-11-21

- Primera publicación en PyPI: `pip install sorbflow`. Publicación automática por
  *trusted publishing* al publicar una release de GitHub (`.github/workflows/publish.yml`).
- Licencia **Apache-2.0** (`LICENSE`, `NOTICE`); titular K. A. Sanchez Hernandez.
- Autores: K. A. Sanchez Hernandez, D. E. Rodriguez Saiz, D. X. Cabrera Obando y
  G. J. Romo Cadena; metadatos de cita en `CITATION.cff`.
- Documentación: modelos y ecuaciones (MathJax), motores de cálculo, comparación con
  otras herramientas, galería de figuras generadas por `scripts/make_figures.py` y
  diagrama de arquitectura.
- Distribución fuente reducida a código, pruebas, ejemplos, scripts y documentación.

## 0.3.0.dev0 — SorbFlow, 2026-11-20

- **Nuevo nombre: SorbFlow** (antes PyFAST). Distribución, paquete importable y
  comando pasan a `sorbflow`; la interfaz local se inicia con `python -m sorbflow.web`.
  Cambio incompatible de importación: sustituir `import pyfast` por `import sorbflow`.
- Resultados JSON con `result_schema_version: 2` y el campo `result_kind:
  numerical_simulation`; metadatos Parquet con prefijo `sorbflow.`.
- Documentación reorganizada como herramienta general: capacidades, configuraciones,
  rendimiento, galería de ejemplos, preguntas frecuentes y referencia de API generada.
- Read the Docs y CI reforzados: dependencias de documentación fijadas, construcción
  estricta, caché, cancelación de ejecuciones obsoletas e instalación del wheel construido.
- La evidencia congelada (`audit/`, protocolos, captura de reproducción) conserva el
  nombre anterior como registro histórico.

## Cambios locales sin publicar — 2026-11-19

- E01-B: referencia ADE continua finita independiente, Pe2/10, promedios de celda,
  refinamiento y criterios fijados previamente; 16 integraciones, 138 criterios satisfechos.
- Perfiles gaussianos experimentales de sigma conocida con nuisance reoptimizados,
  multiinicio y presupuesto; objetivo batch K/k compatible con múltiples condiciones.
- Rechazo de booleanos mezclados con números antes de la coerción de NumPy.
- Preparación técnica de registro con inventario SHA y campos de derechos pendientes;
  no se realiza registro ni se determina autoría.

- Integración del dossier EnvSoft y catálogo separado de las seis fuentes externas.
- E01-A: protocolo congelado en e60dba9 y ejecución de 40 integraciones, 219 criterios
  satisfechos; evidencia sintética conservada. E01 general sigue parcial.
- GUI local opcional `python -m pyfast.web`, con batch/columna, configuraciones SI,
  resultados trazables y límites de ejecución; no añade otro solver.
- Documentación navegable, comprobación de enlaces, control local de calidad con
  hashes/entorno/logs e instrucciones para workers y commits.
- Diseño E02-A propuesto; E04 continúa bloqueado por metadatos. Sin publicación
  en GitHub, cambios de licencia ni redistribución de FAST/datasets externos.

## 0.2.0.dev0 — prototipo científico, 2026-11-18

- Motor independiente batch LDF y columna LDF/HSDM, sin invocar FAST.
- Isotermas con derivadas, mezclas genéricas, matrices FV dispersas y controles de masa/estado.
- Ajuste inicial, diagnóstico local SVD, Monte Carlo, sensibilidad y NSGA-II opcional.
- Hidráulica, costos parciales explícitos y envolvente DXF verificada por lector independiente.
- CSV experimental con unidades y hash; JSON/CSV/Parquet de resultados y CLI.
- Ejemplos sintéticos integrados y diseño robusto preliminar con malla de comprobación.
- Referencias analíticas/matriciales, refinamiento y regresión para cancelación en película casi nula.
- Propuesta Open Core Apache-2.0, con titularidad y publicación aún pendientes.

No establece validación experimental, identificabilidad global, frente robusto convergido,
diseño mecánico, STEP ni interfaz web.

## 0.1.0.dev0 — fundación, 2026-11-18

Auditoría de solo lectura FAST, cinco documentos técnicos, unidades SI, esquemas
tipados, trazabilidad y empaquetado. El ZIP original permanece sin cambios.

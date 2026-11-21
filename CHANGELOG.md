# Registro de cambios

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

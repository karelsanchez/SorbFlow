# Registro de cambios

## Cambios locales sin publicar — 2026-11-19

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

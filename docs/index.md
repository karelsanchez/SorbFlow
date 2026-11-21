# Documentación de SorbFlow

SorbFlow es una herramienta en Python para modelar, simular, calibrar y diseñar
procesos de adsorción en fase acuosa, en reactores batch y columnas de lecho fijo.
Combina isotermas lineal, Langmuir y Freundlich con cinéticas LDF y HSDM
intercambiables, unidades seguras, calibración, incertidumbre, diseño hidráulico y
optimización multiobjetivo, con resultados trazables. Sus
[benchmarks ejecutados](benchmark_results.md) documentan la verificación numérica,
la inferencia sintética y el diseño bajo incertidumbre.

## Recorrido recomendado

El [sitio navegable y su publicación](documentation_site.md) se construyen desde
estos documentos. Los [tutoriales funcionales](tutorials.md) conectan unidades,
simulaciones, trazabilidad y evaluación de resultados.

1. [Primeros pasos](getting_started.md): entorno, casos de ejemplo y CLI.
2. [Preparación de datos](data_preparation.md): unidades, procedencia y mezclas.
   [Revisión E04 integrada](e04_integration.md): selección del caso de columna.
3. [Estado científico](scientific_status.md): funciones disponibles y evidencia.
4. [Desarrollo y comprobaciones](developer_workflow.md): pruebas y trazabilidad.
5. [Interfaz web local](web_interface.md): mismo motor, acceso desde el navegador.
6. [Diseño del estudio inverso E02-A](inverse_study_plan.md).
7. [Perfiles con sigma conocida](profile_likelihood.md) y
   [objetivo batch compartido](batch_objective.md): calibración avanzada, con estudio
   de cobertura en los benchmarks ejecutados. [Ejemplo completo](profile_batch_example.md).
8. [Preparación técnica de registro](../REGISTRATION_PREPARATION/README.md):
   inventario y campos de revisión.

## Referencias del proyecto

- [API pública](../API_REFERENCE.md): contratos, funciones y unidades.
- [Equipo y contribuciones declaradas](../CONTRIBUTORS.md).
- [Arquitectura](../ARCHITECTURE.md) y [notas de implementación](../IMPLEMENTATION_NOTES.md).
- [Modelo matemático](../MODEL_SPECIFICATION.md): balances y condiciones de frontera.
- [Plan de verificación](../VALIDATION_PLAN.md) y [evidencia numérica](../NUMERICAL_VERIFICATION.md).
- [Hoja de ruta](../DEVELOPMENT_ROADMAP.md), [licencias](../IP_LICENSE_AUDIT.md) y [antecedentes](../RELATED_WORK.md).
- [Plan del artículo EnvSoft](../PAPER_ENVSOFT/MANUSCRIPT_PLAN.md) y
  [protocolo confirmatorio](../PAPER_ENVSOFT/BENCHMARK_PROTOCOL.md).
- [Registro de experimentos](../PAPER_ENVSOFT/EXPERIMENT_REGISTRY.csv) y
  [disponibilidad de datos candidatos](../benchmarks/data_catalog/DATASET_READINESS.md).
- [Subprotocolo E01-A](../PAPER_ENVSOFT/E01_SUBPROTOCOL.md),
  [ejecución](../benchmarks/e01/README.md) y
  [evidencia conservada](../audit/e01_a_20261119/summary.json).
- [Subprotocolo E01-B](../PAPER_ENVSOFT/E01B_SUBPROTOCOL.md) y
  [referencia continua a Pe finito](../benchmarks/e01b/README.md).

Las materias primas y el azul de metileno del estudio inicial son una aplicación,
no constantes del motor. Especies, materiales y recetas de N componentes son datos
configurables: cada sistema se describe con sus propios parámetros.

## Capacidades de alto rendimiento

- [Integración en streaming](streaming_integration.md): 956,7 MB frente a 1.632,9 MB
  de memoria privada con curva de salida idéntica, y controles sobre todos los pasos
  aceptados de columnas LDF.
- [Jacobiano analítico](analytic_jacobian.md): columna LDF Langmuir/lineal con BDF o
  Radau, 2,2 veces más rápido en un caso de 620 celdas.
- [Operadores de observación](observation_operators.md): retardo, ventanas y promedio
  a partir de masa acumulada, con historia explícita.

| Módulo | Función |
|---|---|
| `sorbflow.simulate` | Batch LDF y columna LDF/HSDM |
| `sorbflow.fit` | Ajuste de isotermas y tasa batch LDF; diagnósticos locales |
| `sorbflow.uncertainty` | Monte Carlo reproducible y sensibilidad local |
| `sorbflow.optimize` | NSGA-II multiobjetivo (extra `optimize`) |
| `sorbflow.design` | Hidráulica, costo de operación y envolvente DXF |
| `sorbflow.validate` | Verificación del balance de masa de cada resultado |
| `sorbflow.io` | CSV con unidades y exportación JSON/CSV/Parquet |
| `sorbflow.web` | Interfaz web local sobre el mismo motor |

Hoja de ruta: multicomponente, efectos térmicos, alimentación variable, CAD/STEP y
adaptadores de interoperabilidad. SorbFlow resuelve todos sus modelos con su propio
motor; no requiere otros programas.

# Documentación de PyFAST

PyFAST es un prototipo Python para adsorción acuosa y diseño de columnas. Sus
verificaciones numéricas seleccionadas no constituyen validación experimental.
El estado confirmatorio es **E01 parcial** y **E04 BLOCKED_METADATA**, con **0 curvas
listas** para validación física independiente.

## Recorrido recomendado

1. [Primeros pasos](getting_started.md): entorno, casos sintéticos y CLI.
2. [Preparación de datos](data_preparation.md): unidades, procedencia y mezclas.
   [Revisión E04 integrada](e04_integration.md): salvedades y candidato condicionado.
3. [Estado científico](scientific_status.md): implementación, evidencia y pendientes.
4. [Desarrollo y comprobaciones](developer_workflow.md): pruebas y trazabilidad.
5. [Interfaz web local opcional](web_interface.md): mismo núcleo, acceso desde navegador.
6. [Diseño del estudio inverso E02-A](inverse_study_plan.md): propuesta aún no ejecutada.
7. [Perfiles con sigma conocida](profile_likelihood.md) y
   [objetivo batch compartido](batch_objective.md): API experimental, no estudio de cobertura.
   [Ejemplo sintético](profile_batch_example.md).
8. [Preparación técnica de registro](../REGISTRATION_PREPARATION/README.md):
   inventario y campos pendientes de revisión humana.

## Referencias del proyecto

- [API pública](../API_REFERENCE.md): contratos, funciones y unidades.
- [Arquitectura](../ARCHITECTURE.md) y [notas de implementación](../IMPLEMENTATION_NOTES.md).
- [Modelo matemático](../MODEL_SPECIFICATION.md): balances y condiciones de frontera.
- [Plan de validación](../VALIDATION_PLAN.md) y [evidencia numérica seleccionada](../NUMERICAL_VERIFICATION.md).
- [Roadmap](../DEVELOPMENT_ROADMAP.md), [licencias](../IP_LICENSE_AUDIT.md) y [antecedentes](../RELATED_WORK.md).
- [Plan del artículo EnvSoft](../PAPER_ENVSOFT/MANUSCRIPT_PLAN.md) y
  [protocolo confirmatorio](../PAPER_ENVSOFT/BENCHMARK_PROTOCOL.md).
- [Registro de experimentos](../PAPER_ENVSOFT/EXPERIMENT_REGISTRY.csv) y
  [disponibilidad de datos candidatos](../benchmarks/data_catalog/DATASET_READINESS.md).
- [Subprotocolo E01-A](../PAPER_ENVSOFT/E01_SUBPROTOCOL.md),
  [ejecución y límites](../benchmarks/e01/README.md) y
  [evidencia conservada](../audit/e01_a_20261119/summary.json).
- [Subprotocolo E01-B](../PAPER_ENVSOFT/E01B_SUBPROTOCOL.md) y
  [referencia continua a Pe finito](../benchmarks/e01b/README.md).

Las materias primas y el azul de metileno del estudio inicial son una aplicación,
no constantes del motor. Especies, materiales y recetas de N componentes son datos
configurables; otro contaminante requiere parámetros y supuestos químicos adecuados.

## Superficies públicas

- [Jacobiano analítico opcional](analytic_jacobian.md): columna LDF Langmuir/lineal,
  BDF/Radau y límites de la mejora computacional.

- [Operadores experimentales de observación](observation_operators.md): retardo,
  ventanas y promedio a partir de masa acumulada, con historia explícita.

| Módulo | Disponible en el prototipo |
|---|---|
| `pyfast.simulate` | Batch LDF y columna LDF/HSDM |
| `pyfast.fit` | Ajuste de isotermas y tasa batch LDF; diagnósticos locales |
| `pyfast.uncertainty` | Monte Carlo reproducible y sensibilidad local |
| `pyfast.optimize` | NSGA-II mediante dependencia opcional |
| `pyfast.design` | Hidráulica, costo parcial y envolvente DXF |
| `pyfast.validate` | Comprobación numérica del balance de masa |
| `pyfast.io` | CSV experimental explícito y exportación JSON/CSV/Parquet opcional |
| `pyfast.web` | Entrada web local opcional; no amplía la evidencia científica |

Los modelos multicomponente/térmicos, STEP/CAD mecánico, adaptador FAST y validación
experimental siguen pendientes. No se requiere FAST para resolver los modelos propios.

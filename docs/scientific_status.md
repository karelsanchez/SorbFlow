# Estado científico y alcance

[Inicio](index.md) · [Datos](data_preparation.md) · [Desarrollo](developer_workflow.md)

## Estado de los experimentos confirmatorios

La fuente de estados es el [registro de experimentos](../PAPER_ENVSOFT/EXPERIMENT_REGISTRY.csv),
junto con el [protocolo](../PAPER_ENVSOFT/BENCHMARK_PROTOCOL.md).

| Experimento | Estado registrado | Interpretación |
|---|---|---|
| E01 | PARTIAL_REFERENCE_ONLY | Referencias seleccionadas; verificación completa pendiente |
| E02 | PLANNED | Estudio confirmatorio inverso/incertidumbre pendiente |
| E03 | PLANNED | Estudio confirmatorio de decisiones robustas pendiente |
| E04 | BLOCKED_METADATA | Validación física bloqueada; 0 curvas listas |
| E05 | PLANNED | Evaluación confirmatoria adicional según protocolo pendiente |

Un resultado de smoke, la cobertura de tests o una figura sintética no cambia estos
estados a PASSED. El prototipo no está validado experimentalmente y no certifica
un diseño industrial. La [evidencia numérica seleccionada](../NUMERICAL_VERIFICATION.md)
describe casos concretos y sus límites, no una garantía para todo parámetro.

El subestudio [E01-A](../benchmarks/e01/README.md) sí pasó su alcance predefinido:
40 integraciones y 219 criterios, sin fallos. El protocolo se fijó antes de correrlo
en `e60dba9`, declarando conocimiento de pilotos anteriores. Batch lineal, trazador
Dax=0, esfera con superficie prescrita y matriz LDF discreta no cubren todo E01.
La [evidencia JSON](../audit/e01_a_20261119/summary.json) conserva esos límites.

E01-B añadió una referencia continua finita con entrada Danckwerts y salida de
gradiente cero, Pe=2/10 y refinamiento axial. Sus 138 criterios pasaron en 16
integraciones. El protocolo se fijó en `3155b72`; la comparación usa promedios de
celda de la referencia, separados de valores puntuales. No cubre adsorción HSDM
acoplada ni todos los regímenes. [Alcance](../benchmarks/e01b/README.md).

## Qué está implementado

Actualización técnica 2026-11-20: se importaron ocho curvas candidatas extraídas
de una figura y se prepararon 379 puntos visibles con indicadores de calidad.
Los operadores de observación están implementados. Las campañas numéricas E04
no han establecido la puerta de malla para el lecho largo y tasa superior;
no se ha calibrado ni evaluado el conjunto retenido. El estado formal histórico
BLOCKED_METADATA del registro no debe interpretarse como ausencia actual de
archivos candidatos ni como validación de estos. El
[Jacobiano analítico opcional](analytic_jacobian.md) mejora una parte del cálculo,
sin resolver por sí solo ese bloqueo científico.

| Entrada pública | Implementación actual | Límite principal |
|---|---|---|
| `pyfast.equilibrium` | Langmuir, Freundlich normalizado, lineal y derivadas | Parámetros a una temperatura; singularidad de Freundlich explícita |
| `pyfast.simulate` | Batch LDF; columna LDF/HSDM con película y dispersión | Una especie, tamaño de partícula y lecho uniforme; entrada/flujo constantes |
| `pyfast.fit` | Isotermas y tasa LDF batch; SVD/covarianza local | No identifica película y difusión por ajustar una sola tasa |
| `pyfast.uncertainty` | Muestreo con semilla, cuantiles y sensibilidad local | No demuestra cobertura ni discrepancia de modelo por sí solo |
| `pyfast.optimize` | NSGA-II opcional, restricciones y reevaluación | Un frente preliminar no demuestra convergencia u óptimo global |
| `pyfast.design` | Ergun, EBCT, masa, potencia, costo parcial y DXF | No es cálculo mecánico ni costo completo de ciclo de vida |
| `pyfast.validate` | Balance numérico en resultados | No es validación física externa |
| `pyfast.io` | CSV explícito, JSON/CSV y Parquet opcional | No limpia observaciones; Parquet temporal no conserva todos los perfiles |

La [interfaz web local](web_interface.md) es una entrada opcional al mismo núcleo,
no un modelo nuevo. Los balances, IC/BC y bases físicas están en la
[especificación matemática](../MODEL_SPECIFICATION.md).

## Pendientes explícitos

- Completar E01: casos suaves/manufacturados, límites, regímenes rígidos y refinamientos
  que resuelvan los indicadores utilizados en cada decisión.
- Estudio de identificabilidad global, cobertura, censura y calibración multiexperimento.
- Los [perfiles con sigma conocida](profile_likelihood.md) y el objetivo batch K/k
  ya existen como API experimental; su estudio de cobertura/identificabilidad E02
  sigue pendiente. Una malla aceptada no es un intervalo continuo.
- Cobertura predictiva y separación de error numérico, paramétrico, de observación y modelo.
- Estudios de semillas/escenarios/convergencia de Pareto y diseño robusto.
- Validación experimental independiente con unidades, procedencia y condiciones completas.
- Modelos multicomponente/térmicos, condiciones variables y CAD/STEP mecánico avanzado.
- Adaptador FAST externo compatible con licencia y contrato de archivos; no se ejecuta
  ni redistribuye FAST como parte del solver propio.

La extensión a N materiales y a otras especies es un contrato configurable, no una
declaración de universalidad química. El plan de artículo se mantiene en
[PAPER_ENVSOFT](../PAPER_ENVSOFT/MANUSCRIPT_PLAN.md); no se afirma novedad ni superioridad
por integrar algoritmos existentes.

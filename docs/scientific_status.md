# Estado científico y alcance

[Inicio](index.md) · [Datos](data_preparation.md) · [Desarrollo](developer_workflow.md)

## Estado de los experimentos confirmatorios

El [registro de experimentos](../PAPER_ENVSOFT/EXPERIMENT_REGISTRY.csv) conserva
el plan general inicial, que no está ejecutado íntegramente. Los
[benchmarks ejecutados y sus enmiendas](benchmark_results.md) describen la
evidencia actual, sin convertir subestudios en validación de todo ese plan.

| Experimento | Estado registrado | Interpretación |
|---|---|---|
| E01 | PASSED_SCOPED_SUPPLEMENT | Referencias seleccionadas y 29 casos adicionales; dominio general no agotado |
| E02 | COMPLETED_ANALYTIC_COVERAGE | 3.000 datasets y 6.000 perfiles; predictor batch analítico, sin ODE |
| E03 | PASSED_SCOPED_FIXED_DESIGN_REFINEMENT | Comparación sintética acotada; 200 pares refinados resueltos |
| E04 | COMPLETED_CASE_POOR_FIT | C-A/C-B ejecutados; C-B con convergencia local y discrepancias |
| E05 | PLANNED | Evaluación confirmatoria adicional según protocolo pendiente |

Un resultado de smoke, la cobertura de tests o una figura sintética no cambia estos
estados a PASSED. El prototipo no está validado experimentalmente y no certifica
un diseño industrial. La [evidencia numérica seleccionada](../NUMERICAL_VERIFICATION.md)
describe casos concretos y sus límites, no una garantía para todo parámetro.
La generación de nuevos ensayos de laboratorio no es requisito de publicación
de la librería con el alcance de sus benchmarks reproducibles.

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
aportan controles de malla en casos seleccionados: la continuación Q3 del
prototipo y la nueva ejecución Q1 del núcleo en streaming pasan en 3720–7440
celdas para la tasa superior del lecho largo. Son máximos muestreados en casos
declarados, no cotas continuas ni verificación de toda la caja de parámetros.
Posteriormente, la [campaña C-A](../audit/e04_ca_20261120/summary.json) ajustó una
tasa LDF global con equilibrio batch fijo: 82 solves, candidato numéricamente
estable, SSE=9.4663 y RMSE=0.22744 en C/C0 para 183 puntos de calibración.
La evaluación registrada tras congelar el candidato no reajustó parámetros.
El ajuste es deficiente entre condiciones; esto no establece identificabilidad
ni valida el comportamiento ambiental. Las condiciones retenidas ya han sido
evaluadas para C-A: decisiones posteriores informadas por sus resultados deben
declarar esa exposición y no presentarlas como un test nuevo intacto.
La [campaña exploratoria C-B](../audit/e04_cb_20261120/summary.json) permitió
ajustar también q_max, manteniendo una tasa común y afinidad fija: 216 solves
completos, k=7.70119e-6 s^-1, q_max=0.1540245 kg/kg, SSE=9.26359 y
RMSE=0.224991. La disminución descriptiva del SSE fue 2.14 % respecto a C-A;
persisten discrepancias por condición. Los controles de malla del candidato
y la evaluación posterior a congelación pasaron. Ambos refinamientos alcanzaron
su tope de evaluaciones sin declarar convergencia: el resultado es el mejor
candidato examinado, sin certificar un mínimo local o global. No demuestra
identificabilidad, adecuación experimental ni significación estadística de la
mejora. La evaluación reutiliza condiciones ya expuestas en C-A.
La continuación posterior sí alcanzó convergencia local, con SSE=9.25617,
k=7.78219e-6 s^-1 y q_max=0.152827 kg/kg, añadiendo 48 solves completos.
Los controles numéricos pasaron, pero persiste el ajuste deficiente.
El estado formal histórico
BLOCKED_METADATA del registro no debe interpretarse como ausencia actual de
archivos candidatos ni como validación de estos. El
[Jacobiano analítico opcional](analytic_jacobian.md) y la
[integración en streaming](streaming_integration.md) mejoran el coste de cálculo;
su verificación no sustituye la evaluación de adecuación del modelo ni la
validación física pendientes.

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
- Extender la evidencia a identificabilidad global, censura y calibración multiexperimento.
- Los [perfiles con sigma conocida](profile_likelihood.md) y el objetivo batch K/k
  tienen evidencia acotada de inclusión marginal bajo predictor analítico;
  cobertura predictiva de columnas e identificabilidad global siguen pendientes.
  Una malla aceptada no es un intervalo continuo.
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

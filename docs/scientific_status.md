# Estado científico y funciones disponibles

[Inicio](index.md) · [Datos](data_preparation.md) · [Desarrollo](developer_workflow.md)

SorbFlow 0.3.0.dev0 ofrece simulación batch y de columna, calibración,
incertidumbre, optimización y diseño sobre un motor propio con balance de masa
verificado en cada resultado. Esta página resume qué está disponible y qué
evidencia respalda cada parte.

## Estudios ejecutados

El [registro de experimentos](../PAPER_ENVSOFT/EXPERIMENT_REGISTRY.csv) conserva los
estados formales del plan inicial del artículo; los resultados actuales y sus
enmiendas están en [benchmarks ejecutados](benchmark_results.md).

| Estudio | Estado | Resultado |
|---|---|---|
| E01 | PASSED_SCOPED_SUPPLEMENT | Verificación numérica: E01-A 219 criterios, E01-B 138 criterios y suplemento de 29 casos y 148 criterios, todos aprobados |
| E02 | COMPLETED_ANALYTIC_PROFILE_COVERAGE | 3.000 datasets y 6.000 perfiles completos con predictor batch analítico |
| E03 | PASSED_SCOPED_FIXED_DESIGN_REFINEMENT | Diseños robustos con 0 incumplimientos en 40 escenarios; 200 pares refinados resueltos |
| E04 | COMPLETED_CASE_POOR_FIT | Calibración de columna C-A/C-B con datos publicados; convergencia local en C-B |
| E05 | PLANNED | Evaluación confirmatoria adicional del artículo |

Los estados describen el alcance de cada estudio: E01 cubre las familias de
referencia definidas en sus protocolos, E02 la inferencia de perfiles con predictor
analítico y E03 una comparación sintética con presupuesto fijado.
La [evidencia numérica](../NUMERICAL_VERIFICATION.md) detalla los casos concretos.

### E01: verificación numérica

[E01-A](../benchmarks/e01/README.md) aprobó 219 criterios en 40 integraciones:
batch lineal, trazador con Dax=0, esfera con superficie prescrita y matriz LDF
discreta. El protocolo se fijó en `e60dba9` antes de correr
([evidencia](../audit/e01_a_20261119/summary.json)).
[E01-B](../benchmarks/e01b/README.md) aprobó 138 criterios en 16 integraciones
frente a una referencia continua con entrada Danckwerts, Pe=2/10 y refinamiento
axial (protocolo `3155b72`). El suplemento de 2026-11-20 añadió 29 casos y 148
criterios: batch Langmuir, HSDM lineal acoplado con película y comparación BDF/Radau.

### E04: caso de columna con datos publicados

Se importaron ocho curvas candidatas extraídas de una figura publicada, con 379
puntos visibles e indicadores de calidad, y se implementaron los operadores de
observación. Los controles de malla pasan en 3720–7440 celdas para la tasa superior
del lecho largo.

- [C-A](../audit/e04_ca_20261120/summary.json): tasa LDF global con equilibrio batch
  fijo; 82 solves, SSE=9.4663 y RMSE=0.22744 en C/C0 para 183 puntos.
- [C-B](../audit/e04_cb_20261120/summary.json): tasa común y q_max ajustados; la
  continuación alcanzó convergencia local con k=7.78219e-6 s^-1, q_max=0.152827 kg/kg
  y SSE=9.25617 (mejora de 2,22 % frente a C-A; la primera campaña C-B había
  registrado 2,14 %), 48 solves adicionales y controles numéricos aprobados.

El caso muestra el flujo completo dato → operador de observación → calibración →
control numérico. Las diferencias por condición indican dónde un modelo más
completo del sistema estudiado puede mejorar el ajuste. Las condiciones de
evaluación ya se habían usado en C-A, lo que se declara en los informes.

## Funciones disponibles

| Entrada pública | Implementación | Configuración |
|---|---|---|
| `sorbflow.equilibrium` | Langmuir, Freundlich normalizado, lineal y derivadas | Parámetros a la temperatura de operación; derivada de Freundlich en cero informada explícitamente |
| `sorbflow.simulate` | Batch LDF; columna LDF/HSDM con película y dispersión | Un soluto, partículas esféricas, lecho uniforme, caudal y alimentación especificados |
| `sorbflow.fit` | Isotermas y tasa LDF batch; SVD y covarianza local | Ajuste de una tasa global o de parámetros de isoterma |
| `sorbflow.uncertainty` | Muestreo con semilla, cuantiles y sensibilidad local | Distribuciones definidas por el usuario |
| `sorbflow.optimize` | NSGA-II con restricciones y reevaluación | Objetivos y escenarios del usuario |
| `sorbflow.design` | Ergun, EBCT, masa, potencia, costo y DXF | Envolvente de proceso del lecho |
| `sorbflow.validate` | Balance de masa de cada resultado | Tolerancias del integrador |
| `sorbflow.io` | CSV con unidades, JSON/CSV y Parquet | Parquet guarda la serie temporal; JSON, los perfiles completos |

Rendimiento: el [Jacobiano analítico](analytic_jacobian.md) fue 2,2 veces más rápido
en una columna de 620 celdas y la [integración en streaming](streaming_integration.md)
redujo la memoria privada de 1.632,9 MB a 956,7 MB con la misma curva de salida.
La [interfaz web local](web_interface.md) usa el mismo motor. Balances, condiciones
iniciales y de frontera están en la [especificación matemática](../MODEL_SPECIFICATION.md).

## Buenas prácticas

- Comparar al menos dos mallas y tolerancias en los indicadores que se usarán para
  decidir (tiempo de ruptura, capacidad útil, factibilidad).
- Usar parámetros obtenidos a la temperatura y en la base de masa de operación.
- Partir los datos por ensayo completo cuando se calibren y evalúen predicciones.
- Los [perfiles con sigma conocida](profile_likelihood.md) se evalúan sobre una malla
  de parámetros; la cobertura de E02 se estudió con predictor analítico batch.

## Hoja de ruta

- Ampliar E01 con soluciones manufacturadas no lineales y mapas Pe/Da/Bi.
- Identificabilidad global, observaciones censuradas y calibración multiexperimento.
- Cobertura predictiva de columnas y separación de errores numérico, paramétrico,
  de observación y de modelo.
- Estudios de semillas, escenarios y convergencia de Pareto para diseño robusto.
- Evaluación con más conjuntos de datos experimentales independientes.
- Modelos multicomponente y térmicos, alimentación variable y CAD/STEP.
- Adaptadores de interoperabilidad compatibles con la licencia de cada programa.

La extensión a N materiales y otras especies es un contrato configurable. El plan
del artículo está en [PAPER_ENVSOFT](../PAPER_ENVSOFT/MANUSCRIPT_PLAN.md).

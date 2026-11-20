# Protocolo de cobertura E02-A: propuesta `DRAFT_NOT_FROZEN`

> **Estado: DRAFT_NOT_FROZEN.** Ninguna cifra de este documento es un protocolo
> aprobado. No se ejecutó piloto, cobertura ni ajuste alguno. Antes de cualquier
> ejecución, Codex debe revisar, congelar y hashear este protocolo, el código del
> driver, las raíces de semillas y los criterios. Todas las cifras son **techos o
> parámetros de diseño**, no tiempos, tasas ni resultados observados.

## 1. Objetivo y estimandos

Para cada escenario s, parámetro j ∈ {K, k} y nivel nominal 0.95, el estimando es la
**probabilidad de inclusión puntual de la verdad**:

    p_sj = P( delta_j(theta_j,true) <= chi2_{1,0.95} )

donde `delta_j(a) = chi2_profile_j(a) - chi2_baseline` con sigma conocida. Se
estudian cuatro cosas separadas, que no se fusionan:

| Eje | Qué mide | Fuente |
|---|---|---|
| Inclusión de la verdad | delta en la verdad, evaluado directamente | §4.1 |
| Convergencia | fracción de inicios que alcanzan el mínimo; estados | §4.3 |
| Cierre del perfil | si existen cruces a ambos lados, cerrados por los datos | §4.2 |
| Amplitud | distancia entre cruces refinados (solo si el perfil está cerrado por los datos) | §4.2 |

La cobertura **no** se calcula por pertenencia de la verdad a `accepted_grid`.

## 2. Modelo, generador y supuestos (DRAFT_NOT_FROZEN)

- Batch lineal LDF, q0 = 0, c0 = 0.01 kg/m³, V = 1e-3 m³, T = 298.15 K fija.
  Dos experimentos independientes con m = 0.002 y 0.004 kg, es decir β = 2 y
  4 kg/m³. θ = (K [m³/kg], k [1/s]).
- Ruido gaussiano independiente con **sigma conocida** σ = 1e-4 kg/m³ (rama A).
  La rama B (escala estimada) queda fuera de alcance; si se añade, necesita su
  propio LR = n log(RSS_w(a)/RSS_w,min), no este protocolo.
- **Generador independiente**: la forma cerrada
  `c(t) = c_eq + (c0 - c_eq) exp(-k(1+βK)t)`, con `c_eq = c0/(1+βK)`, va en el
  driver sin importar `pyfast.simulate`. Una comprobación previa congelada mide
  el error predictor-vs-forma-cerrada en las 12 observaciones. El criterio
  candidato, del plan, es < 0.1 σ, también con tolerancias endurecidas.
- **Ruido firmado sin recorte.** La API rechaza concentraciones negativas
  (`schemas.py:436`). Un dataset con c < 0 se registra como
  `GENERATION_REJECTED`, **cuenta en M** como inconcluso y nunca se vuelve a
  muestrear. Antes de congelar, cada escenario declara P(alguna c < 0), calculada
  analíticamente con la forma cerrada.

## 3. Escenarios (DRAFT_NOT_FROZEN)

| Id | Rol | Verdad (K, k) | Tiempos [s] | Límites K / k | Observación |
|---|---|---|---|---|---|
| S1 | Interior informativo (primario) | (0.5, 0.02) | 0, 10, 30, 60, 120, 300 | [0.1, 2] / [0.005, 0.08] | Como el demo, pero con datasets nuevos |
| S2 | Información limitada (primario) | (0.5, 0.02) | 0, 2, 4, 6, 8, 10 | igual | Ventana temprana: domina el producto βkKc0 (plan §3) |
| S3 | Casi frontera (diagnóstico) | K = K_lo·exp(d·SE_logK), d ∈ {1, 2} | como S1 | K_lo = 0.1 | SE_logK de la información de Fisher esperada en la verdad, calculada y congelada antes de correr |
| S4a | En frontera, parámetro de interés (diagnóstico) | K = K_lo = 0.1 | como S1 | igual | Asintótica no estándar (Chernoff 1954): resultado solo descriptivo |
| S4b | En frontera, nuisance (diagnóstico) | k = k_lo = 0.005, perfil de K | como S1 | igual | Comprueba que se marcan `bound_limited` y F02 |

Con n = 12 observaciones por dataset (6 × 2 experimentos), los p_sj de S3 y S4
**no** tienen un umbral de aprobación salvo que se calibre por separado (§6).

## 4. Algoritmo por dataset (DRAFT_NOT_FROZEN)

### 4.1 Inclusión puntual (estimando primario)

Para cada j hay una llamada `profile_gaussian_known_sigma(..., parameter=j,
grid=[theta_j,true])`. La verdad está dentro de los límites por construcción;
en S4 coincide con un límite, cosa que la API permite. Configuración:

- 20 inicios por Latin hypercube en el cubo log-físico, tomados de su propio
  flujo de semillas (§5). Cada llamada repite el baseline, así que se compara
  `baseline_chi2` entre las llamadas de K y de k. Si difieren en más de 1e-6 +
  1e-8·χ², el dataset es `INCONSISTENT_ACROSS_CALLS`, es decir, inconcluso.
- `max_nfev = 100` por intento y `max_callback_calls = 3000` por llamada. El techo
  se apoya en el demo: los intentos baseline usaron 35 y 40 callbacks y los de
  perfil entre 21 y 27 (`report.json profile.*.trials[*].callback_calls`). Con 40
  intentos por llamada eso da unos 1300, así que 3000 deja margen. No es una
  predicción de coste.
- **Clasificación** (por dataset y parámetro):
  - `HIT`: status `COMPLETE`, sin `baseline_inconsistent`, sin la condición F01
    (ningún χ² registrado por debajo del baseline menos la tolerancia), sin
    inconsistencia entre llamadas, y delta(verdad) ≤ cutoff.
  - `MISS`: las mismas condiciones, con delta(verdad) > cutoff.
  - `INCONCLUSIVE`: cualquier otro caso (`BASELINE_INCONSISTENT`,
    `BUDGET_EXHAUSTED`, `BASELINE_FAILED`, `INCOMPLETE`, `GENERATION_REJECTED`,
    F01, inconsistencia entre llamadas, excepción del driver).

### 4.2 Cierre y amplitud (estudio secundario, con presupuesto separado)

Va en un subconjunto preespecificado, los primeros M_cl = 200 datasets de cada
escenario en orden de réplica, que no se eligen por resultado:

1. Malla gruesa de 21 puntos log-equiespaciados en [lower, upper], con los
   extremos ajustados exactamente a los límites (por F04).
2. Por cada par adyacente aceptado/rechazado, bisección en log θ_j con
   reoptimización completa en cada punto nuevo (llamada con `grid=[punto]`), hasta
   que el semiancho relativo del corchete sea < 2 % (plan §7).
3. Clasificación del extremo: `CLOSED_BY_DATA` (el punto que rechaza no tiene
   nuisance en límite), `NUISANCE_BOUND` (rechazo con nuisance en límite, como en
   el caso C1), `BOUND_LIMITED`, `GRID_TRUNCATED` o `INCONCLUSIVE`.
4. La amplitud relativa (sup − inf)/θ_true se informa **solo** para perfiles
   cerrados por los datos en ambos lados, con su denominador explícito.
5. Si el perfil es multimodal, se informa como tal; no se rellenan huecos.
   Cualquier discrepancia entre la inclusión de §4.1 y la pertenencia al conjunto
   refinado se registra.
6. Techos: 5 inicios, `max_callback_calls = 4000` por llamada.

### 4.3 Diagnósticos de convergencia

Para cada llamada se registran la fracción de inicios del baseline con χ² ≤
χ²_best + 1e-4 (candidato del plan), los estados de todos los intentos,
`bound_parameters` y `active_mask` si se añade (F02). La convergencia se informa
aparte y no se convierte en cobertura.

## 5. Semillas e independencia (DRAFT_NOT_FROZEN)

- Hay tres raíces de entropía, una por fase: `PILOT`, `CALIBRATION` y
  `CONFIRMATION`. Se generan con un CSPRNG **en el momento de congelar** y se
  registran en el manifiesto hasheado; no se eligen antes.
- `SeedSequence(root_phase).spawn(n_scenarios)`, luego `.spawn(M_s)` por
  escenario y `.spawn(2)` por dataset, que da `[data_stream, starts_stream]`. Se
  registra el `spawn_key` completo de cada dataset (lo que corrige F16).
- Los inicios son independientes de los datos. Los datasets del piloto, la
  calibración y la confirmación son disjuntos por construcción: ningún dataset
  ni flujo se reutiliza entre fases.
- El registro de cada fase se precrea con una fila por dataset planificado antes
  de ejecutar. Ninguna fila se borra, y un fallo de ejecución queda registrado.

(Fuente de la API `SeedSequence`: documentación oficial de NumPy, no consultada
en esta sesión, **PENDING**.)

## 6. Tamaño M por precisión binomial (DRAFT_NOT_FROZEN)

Semiancho del intervalo de Wilson al 95 % evaluado en p = 0.95 (cálculo de diseño
del oráculo, `aux_oracle/oracle_results.json → wilson_design`):

| M | 50 | 100 | 500 | 1000 | 1825 | 2000 |
|---|---|---|---|---|---|---|
| semiancho | 0.066 | 0.045 | 0.0193 | 0.0136 | 0.0100 | 0.0096 |

M necesario para un semiancho objetivo: 0.02 → 469, 0.015 → 824, 0.0135 → 1014,
0.01 → 1838.

Propuesta:

| Fase | Escenarios | M por escenario | Semiancho objetivo | Datasets |
|---|---|---|---|---|
| Piloto (solo operativo: fallos, presupuesto; **sin inferencia de cobertura**) | S1, S2, S3(d=1), S4a | 50 | 0.066 (informativo) | 200 |
| Calibración de umbrales (opcional; si no se hace, S3/S4 quedan `NOT_TESTED` como cobertura calibrada) | S3(d=1), S4a | 1000 | — | 2000 |
| Confirmación primaria | S1, S2 | 1000 | ≈ 0.0136 | 2000 |
| Confirmación diagnóstica | S3(d=1), S3(d=2), S4a, S4b | 500 | ≈ 0.0193 | 2000 |

**Total planificado:** 4200 datasets sin calibración y 6200 con ella. Cambiar M
o los escenarios después del piloto exige una enmienda registrada antes de
confirmar.

## 7. Presupuesto máximo (techos de diseño, DRAFT_NOT_FROZEN)

Una llamada al callback equivale a 2 solves físicos, uno por experimento, como
se verifica en el demo: `physical_solves = 2 × callback_calls`.

| Concepto | Techo |
|---|---|
| §4.1 por dataset: 2 llamadas × 3000 callbacks × 2 solves | 12 000 solves |
| Piloto: 200 × 12 000 | 2.4·10⁶ solves |
| Calibración (opcional): 2000 × 12 000 | 2.4·10⁷ solves |
| Confirmación: 4000 × 12 000 | 4.8·10⁷ solves |
| §4.2 cierre: 6 escenarios de confirmación × 200 × 2 parámetros × (1 + ~2×8 bisecciones) llamadas × 4000 × 2 | ≤ 3.3·10⁸ solves (techo laxo; el piloto debe acotarlo mediante una enmienda) |

`physical_solves` se toma por llamada, antes y después (F10). Agotar un techo da
`INCONCLUSIVE`, conserva la evidencia y **nunca** reintenta con un techo mayor. Si
más del 5 % de un escenario resulta `BUDGET_EXHAUSTED`, ese escenario se declara
`INCOMPLETE`.

## 8. Denominadores y métricas informadas

Para cada escenario y parámetro, con M = número de datasets **planificados**:

- `hits`, `misses`, `inconclusive` (desglosado por causa), que suman M.
- **Cota inferior incondicional**: L = hits/M. Es la tasa operativa conservadora,
  porque trata los inconclusos como no-cobertura.
- **Cota superior incondicional**: U = (hits + inconclusive)/M.
- **Condicionada a resultado concluyente**: hits/(hits + misses), siempre
  rotulada «condicionada», con su propio denominador.
- Un intervalo de Wilson para cada una de las tres. Clopper-Pearson solo como
  sensibilidad, preespecificada.
- Además, sesgo y RMSE de θ̂ (solo en baselines concluyentes, con su denominador),
  fracción de convergencia, límites alcanzados, costos (callbacks y solves) y, en
  §4.2, el cierre por categoría y la amplitud con su denominador.

## 9. Criterios falsables previos (candidatos, DRAFT_NOT_FROZEN)

Solo se aplican a la **confirmación**, nunca al piloto:

1. **Comprobación numérica previa**: el error del predictor es < 0.1 σ. Si falla,
   se suspende la inferencia del escenario.
2. **S1 y S2, para cada parámetro**:
   - *Compatible con el nominal* si el intervalo de Wilson de la cobertura
     condicionada contiene 0.95 **y** inconclusive/M ≤ 0.02.
   - *Subcobertura demostrada* si la cota superior de Wilson de U es < 0.95.
   - *Sobrecobertura demostrada* si la cota inferior de Wilson de L es > 0.95.
   - Criterio operativo del plan: la cota inferior de Wilson de L es ≥ 0.92.
   - Cualquier otro resultado se informa como *indeterminado*, sin redondear.
3. **S3 y S4**: solo descriptivos. No se declara cobertura nominal con χ²(1).
   Cualquier umbral calibrado sale de la fase de calibración, con datasets
   disjuntos de los de confirmación.
4. Los resultados negativos o indeterminados se publican igual que los positivos.
   No se relajan umbrales después de ver los datos.

## 10. Prerrequisitos antes de ejecutar (para Codex)

- [ ] Resolver o decidir F01 (χ² de intentos fallidos por debajo del baseline) y
      F02/F04 (detección de límites). Sin eso, la clasificación de §4.1 depende
      del driver.
- [ ] Correr los casos A–C y ADV1–ADV4 de `ANALYTIC_REFERENCE_CASES.json` contra
      la implementación y registrar PASS, FAIL o NOT_EXERCISED.
- [ ] Congelar: este protocolo, el código del driver y del generador, el hash del
      commit de PyFAST, las versiones de NumPy/SciPy, las raíces de entropía, el
      esquema del registro y los criterios. Hashear el manifiesto.
- [ ] Verificar las fuentes que quedaron PENDING (Self & Liang 1987, Wilson 1927,
      documentación de NumPy `SeedSequence`).

Este documento no autoriza ejecución, publicación, cambios de licencia ni
afirmaciones de E02 completo, cobertura nominal demostrada o validación
experimental.

# Revisión estadística independiente de E02

Revisión hecha por Claude el 2026-11-19, sin importar ni ejecutar PyFAST.
Todas las cifras rotuladas *oráculo* provienen de `aux_oracle/oracle.py`, un
script propio que usa solo NumPy y SciPy. Ninguna es un resultado de PyFAST.

## 0. Decisión acotada

**ACEPTAR con correcciones menores** la pieza `profile_gaussian_known_sigma` +
`LinearBatchObjective` como **componente experimental de ingeniería** para perfiles
gaussianos con σ diagonal conocida sobre una malla explícita. La likelihood, el
estadístico, la reoptimización de nuisance, la conservación de intentos y los
contadores son correctos para el contrato declarado. No encontré ningún fallo P0
ni P1.

**Corregir antes de congelar el estudio de cobertura:**
- **F01 (P2, BUG).** La detección de baseline inconsistente ignora los χ²
  alcanzados por intentos fallidos.
- **F02 (P2, PENDING).** La detección de nuisance en límite es frágil.
- **F03 (P2, DOC_GAP).** `edge_status` no distingue un rechazo causado por un
  límite de nuisance.
- **F04 (P3, BUG).** Un punto de la grid situado en el límite se compara con
  igualdad exacta.

**Mantener PENDIENTE:** E02 completo, cobertura, intervalos continuos,
identificabilidad y validación experimental. Ningún entregable de esta carpeta
autoriza publicación, cambios de licencia ni esas afirmaciones.

## 1. Alcance, insumos e independencia

| Insumo | Estado |
|---|---|
| `PyFAST/src/pyfast/calibration/profile.py` | leído; SHA-256 `bc2e7e6c…2158` = `specification.json → source_sha256` |
| `PyFAST/src/pyfast/calibration/batch_objective.py` | leído; `83942833…b4fa` = manifiesto del demo |
| `PyFAST/docs/profile_likelihood.md`, `PyFAST/docs/inverse_study_plan.md` | leídos |
| `runs/profile_batch_demo_20261119_release/{specification,data_0,data_1,report}.json` | leídos; hashes en `aux_oracle/oracle_results.json` |

Ningún insumo falta. **Dependencias leídas** (solo lectura, imprescindibles para
F07, F10, F11 y F16): `src/pyfast/schemas.py` (`Observations`, l. 411-444),
`src/pyfast/_arrays.py` (`real_array`, l. 22-32) y
`examples/profile_batch.py` (l. 30-99). Sus hashes también coinciden con el
manifiesto del demo. No ejecuté ni importé ninguna de ellas.

**Desviación de ruta.** El encargo pide `aux/oracle.py`, pero `AUX` es un nombre
de dispositivo reservado en Windows y la carpeta no es utilizable con las
herramientas nativas. El oráculo está en `aux_oracle/` (`oracle.py`,
`oracle_results.json`, `build_cases.py`). Corre con `python -I oracle.py` bajo
Python 3.7.0, NumPy 1.19.5 y SciPy 1.7.3, un entorno distinto del demo
(3.11.2 / 2.4.6 / 1.17.1). Sus 37 comprobaciones internas pasan.

## 2. Revisión obligatoria

### 2.1 Likelihood

- **Lo que admite el callback** (`profile.py:21`, `142-152`): cualquier vector
  real de longitud fija. El χ² se calcula como `r·r` (l. 148) y se exige que sea
  finito (l. 149-150; `real_array` rechaza NaN e infinitos).
- **Lo que construye el builder batch** (`batch_objective.py:113-116`):
  `r_i = (h_i − y_i)/σ_i` con σ **diagonal**. Valida que σ exista
  (l. 35-36) y que sea > 0, finita y de la misma longitud que las observaciones
  (`schemas.py:435-436, 443`). No admite covarianza general, y no debe
  atribuírsele (F07).
- Con una Σ fija conocida, el usuario podría pasar al perfil `r = L⁻¹(h − y)`.
  El caso B3 del oráculo verifica `rᵀr = (h−y)ᵀΣ⁻¹(h−y)` (1.97167 en ambos
  lados) y que ignorar la correlación cambia delta: en β = 0.08 da 7.66 con σ
  diagonal y 6.12 con GLS. Si Σ depende de θ, aparece el término log det Σ(θ) y
  el objetivo deja de ser un blanqueo fijo; queda fuera de la API, como dice
  `profile_likelihood.md:27-28`.
- **Λ frente a su estadístico.** Λ(a) = L_perfil(a)/L_max = exp(−Δ/2) ∈ (0, 1].
  `delta_chi2 = χ²_perfil − χ²_baseline = −2 log Λ` es exacta con σ fija, porque
  la constante −½ log|2πΣ| no depende de θ. Sin embargo, es relativa al
  **mejor mínimo convergente encontrado** en el dominio **acotado**. La
  documentación (`profile_likelihood.md:55-56`) omite esa calificación (F05).

### 2.2 Rama de ruido

El código implementa solo la rama A, σ conocida. `inverse_study_plan.md:88-92,
129-133` separa correctamente la rama B, `n log(RSS_w(a)/RSS_w,min)` con escala
común estimada por MLE, y prohíbe sustituirla por RSS/(n−p). El demo usa
σ = 1e-4 kg/m³ fija (`specification.json → known_sigma_kg_m3`,
`data_*.json → sigma_kg_m3`). No hay mezcla de ramas (F08: CONTRACT_OK).

### 2.3 Regularidad y grid

- La positividad y las coordenadas logarítmicas son correctas: los límites
  cumplen 0 < lower < upper (`profile.py:40-41`). Un cero no es representable y
  la documentación lo dice (`profile_likelihood.md:38`).
- El corte `chi2.ppf(confidence, 1)` (l. 252) es asintótico y solo vale en el
  interior regular. Con la verdad en la frontera, el límite no es χ²(1)
  (Chernoff 1954, metadatos verificados; mezclas de Self & Liang 1987, PENDING).
  La documentación lo declara (`profile_likelihood.md:61-64`; F14).
- Que `accepted_grid` no es un intervalo está bien declarado (l. 73;
  `profile_likelihood.md:66-73`; `report.json →
  continuous_confidence_interval_estimated: false`).
- **Cresta (caso C1).** Con y = ab + ε, a ∈ [0.5, 4] y b ∈ [0.8, 3], el perfil
  es exactamente plano (Δ = 0) en a ∈ [2/3, 2.5]. Cada rechazo de la grid ocurre
  donde b̂(a) = clip(ȳ/a, 0.8, 3) toca un límite. La aceptación
  `[0.65 … 2.6]` y los bordes REJECTED/REJECTED parecen un perfil cerrado, pero
  ese cierre lo producen los límites de b, no la información sobre a. Con
  límites amplios de b, toda la grid sale con Δ = 0. El buen ajuste no identifica
  a y b por separado, porque la likelihood depende solo de ab. → **F03**.
- **Detección de límites.** Para los nuisance se usa una tolerancia de 1e-7 en
  log (l. 119-122). trf mantiene iteraciones estrictamente factibles (SciPy,
  S1), por lo que un nuisance anclado puede quedar sin marcar (**F02**, por
  verificar con B2 y C1). Para el parámetro perfilado se usa igualdad exacta
  (l. 258, 270), y una grid generada con `logspace` puede fallar (**F04**).

### 2.4 Optimización

- En cada punto se reoptimizan todos los nuisance desde todos los inicios, con el
  objetivo fijado (l. 243-245). Los intentos fallidos se conservan (l. 170-178).
  El delta no se recorta (l. 256). Con baseline inconsistente, `accepted` pasa a
  None (l. 257), los bordes a UNAVAILABLE (l. 266-267) y el estado tiene
  prioridad (l. 272). → **F06: CONTRACT_OK**.
- **F01 (P2, BUG).** `_best` (l. 181-185) y la comprobación de inconsistencia
  (l. 247-251) consideran solo intentos con `success=True`. Pero un intento
  `ERROR`, `OPTIMIZER_FAILED` o `BUDGET_EXHAUSTED` registra un χ² que se evaluó
  de verdad en un θ factible (`last_chi2` o `fitted.fun`). Si ese valor queda por
  debajo de baseline − tolerancia, el baseline no es el mínimo y debería
  señalarse. El caso **ADV4** lo reproduce de forma determinista: el código
  actual devolvería INCOMPLETE con `baseline_inconsistent=False` aunque haya
  registrado χ² = 0 frente a un baseline de 0.0399.
- **API frente a plan (F13).** El plan pide continuación, arranques en caliente y
  actualización del baseline (`inverse_study_plan.md:122-127`). La API no los
  ofrece y lo documenta (`profile_likelihood.md:42-43, 57-59`). Son
  ampliaciones propuestas, no parte del contrato actual.

### 2.5 Presupuestos

| Contador | Qué cuenta | Base |
|---|---|---|
| `max_nfev` / `nfev` de SciPy | evaluaciones por intento, **sin** las del Jacobiano numérico | S1 (SciPy 1.18.0): «does not include the function calls used for numerical Jacobian approximation» |
| `callback_calls` | todas las invocaciones reales, incluidas las de diferencias finitas y las que lanzan excepción | `profile.py:104-110`: el límite se comprueba antes y se incrementa antes de invocar |
| `physical_solves` | llamadas a `simulate_batch` intentadas (se incrementa antes del solve) | `batch_objective.py:109-112` |

En el demo: `report.json → physical_solves = 426 = 2 × profile.callback_calls
(213)`, y la suma de `trials[*].callback_calls` es 213 (*oráculo*). La relación
1 callback = 2 solves vale solo para este builder con dos experimentos y sin
fallos, y no debe extrapolarse. Hay lagunas documentales (**F10**): sin baseline,
los puntos de la grid quedan con `trials=()`; `budget_exhausted` es False si se
consume exactamente el techo; el contador de solves es acumulativo por instancia;
y un «solve» no incluye las evaluaciones internas de la EDO.

### 2.6 Demo (contraste sin recalibrar)

Todo lo de esta subsección lo calculó el *oráculo* evaluando la forma cerrada en
los parámetros **reportados**, sin reajustar:

- **Unidades**: SI (m³/kg, 1/s, kg/m³). La verdad es K = 0.5 y k = 0.02
  (`data_*.json → truth_parameters`), con β = 2 y 4 kg/m³ según `config_json`.
- **Ruido**: z en la verdad para las 12 observaciones, con |z| máximo de 1.66 y
  signos mixtos; no hay recorte. `min(c)/σ = 31.9`, por lo que la probabilidad
  de concentraciones negativas es despreciable aquí (F11 aplica al estudio
  futuro).
- **Discrepancia numérica**: |χ²_forma cerrada − χ²_reportado| ≤ 4.3e-6, que
  equivale a menos de 1e-6 σ por residual, muy por debajo de 0.1 σ. Aun así es
  del mismo orden que `baseline_tolerance = 1e-6` (**F12**).
- **Coherencia**: χ²(verdad) = 11.29 ≥ χ²_perfil(K = 0.5) = 11.124. El corte
  recalculado (3.841458820694124) y los deltas recalculados coinciden exactamente
  con el reporte.
- **Semillas**: ambos `data_*.json → seed` valen 20261119, porque comparten un
  único flujo secuencial (`profile_batch.py:39, 51`). El ruido es independiente,
  pero data_1 no se puede regenerar por separado (**F16**).

**El demo permite concluir** que la cadena funciona de principio a fin con el
código auditado (los hashes coinciden), que los contadores son coherentes y que
el error numérico es despreciable frente a σ en este diseño. **No permite
concluir** nada sobre cobertura, intervalos, identificabilidad global, la
calidad de la grid (tres puntos, con la verdad K = 0.5 justo en un nodo) ni
validación experimental. Es una sola realización. → F15.

### 2.7 Cobertura futura

Está en `COVERAGE_PROTOCOL_PROPOSAL.md` (DRAFT_NOT_FROZEN). La propuesta usa
inclusión puntual de la verdad evaluando el perfil en θ_true, no pertenencia a
la grid. Mantiene fases disjuntas con raíces de `SeedSequence` y `spawn_key`
registrados, y separa los flujos de datos e inicios. Todos los datasets
planificados entran en M, y los inconclusos se desglosan. Propone las cotas
hits/M y (hits+inconclusos)/M, y una cobertura condicionada rotulada como tal.
M se justifica por el semiancho de Wilson (M = 1000 da ±0.0136). Fija techos de
presupuesto y criterios falsables previos.

## 3. Referencias analíticas

`ANALYTIC_REFERENCE_CASES.json` contiene 10 casos, cada valor con su procedencia
(`analytic_derivation`, `own_oracle` o `proposed`):

- **A1** media interior.
- **A2** media con proyección sobre el límite: Δ = n[(μ−μ̂)² − (μ̃−μ̂)²]/σ². Los
  valores correctos son 0 en μ = 2.3 y 3.52 en μ = 2.5. Las fórmulas interiores
  se incluyen como contraste erróneo: con μ̂ sin restringir darían 0.98 y 4.5, y
  centradas en μ̃ darían 0 y 1.28.
- **B1** regresión con nuisance interior.
- **B2** nuisance α acotado, con baseline restringido explícito y confirmado por
  BVLS.
- **B3** Σ AR(1) fija.
- **C1** cresta por producto.
- **ADV1** baseline en un mínimo local; se espera BASELINE_INCONSISTENT.
- **ADV2** presupuesto agotado en el baseline, con `callback_calls = 3`.
- **ADV3** presupuesto agotado a mitad del perfil, en dos fases para no adivinar
  conteos.
- **ADV4** intento fallido por debajo del baseline (F01).

Tolerancias:
- Internas del oráculo: 1e-9 en χ².
- Propuestas frente a PyFAST: 1e-6 + 1e-8·|valor|, justificadas por
  `ftol = 1e-10` (l. 158) y el `baseline_tolerance` por defecto.
- Las decisiones de aceptación deben coincidir exactamente, porque todos los
  puntos están a ≥ 0.05 del corte. Ningún conjunto de puntos aceptados se
  denomina CI.

Los estados esperados de PyFAST son **propuestos a partir de la lectura del
código**. No se ejecutaron.

## 4. Fuentes

| Id | Fuente | Estado | Qué respalda |
|---|---|---|---|
| S1 | SciPy `least_squares`, página estable v1.18.0 (https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html): `max_nfev`, `nfev`, `active_mask`, `status`, Notes de trf | VERIFICADA para 1.18.0; la página 1.17.1 dio 404 | semántica de nfev, factibilidad estricta, active_mask |
| S2 | Wilks (1938), doi:10.1214/aoms/1177732360 | metadatos verificados (Crossref) | ley χ² asintótica de −2 log Λ en el interior regular |
| S3 | Chernoff (1954), doi:10.1214/aoms/1177728725 | metadatos verificados | LR no χ² con el parámetro en la frontera |
| S4 | Self & Liang (1987), doi:10.1080/01621459.1987.10478472 | **PENDING** (429, sin reintento) | mezclas χ̄² con frontera o nuisance |
| S5 | Venzon & Moolgavkar (1988), doi:10.2307/2347496 | **PENDING** | extremos de intervalos de perfil por búsqueda de raíces |
| S6 | Raue et al. (2009), doi:10.1093/bioinformatics/btp358 | **PENDING** | perfiles planos y no identificabilidad |
| S7 | Wilson (1927), doi:10.1080/01621459.1927.10502953 | **PENDING** (solo cita secundaria en S8) | intervalo score |
| S8 | Brown, Cai & DasGupta (2001), doi:10.1214/ss/1009213286 | metadatos verificados | preferencia por Wilson frente a Wald |
| S9 | Clopper & Pearson (1934), doi:10.1093/biomet/26.4.404 | metadatos verificados | intervalo exacto, como sensibilidad |

«Metadatos verificados» significa que el registro bibliográfico se comprobó
contra Crossref. El texto completo no se releyó en esta sesión.

## 5. Decisiones concretas para Codex

| Hallazgo | Decisión |
|---|---|
| F06, F07, F08, F09, F14, F15 | **ACEPTAR** como contrato actual |
| F01 | **CORREGIR**: usar el mínimo de todos los χ² registrados para la inconsistencia, o añadir un diagnóstico; probar con ADV4 |
| F04 | **CORREGIR**: tolerancia o ajuste exacto de la grid a los límites |
| F03 | **CORREGIR o DOCUMENTAR**: estado de borde para rechazos con nuisance en límite; probar con C1 |
| F02 | **PENDIENTE**: ejecutar B2 y C1; registrar `active_mask` y la distancia a los límites |
| F05, F10, F11, F12, F13, F16 | **DOCUMENTAR** antes de congelar E02 |
| Casos A–C y ADV1–ADV4 | **EJECUTAR** contra PyFAST (fuera de esta revisión) y registrar PASS, FAIL o NOT_EXERCISED |
| Protocolo | **MANTENER DRAFT_NOT_FROZEN** hasta revisión, congelación y hash por parte de Codex |
| Fuentes S4–S7 | **PENDIENTE** de verificación |
| E02 completo, cobertura nominal, intervalos, validación | **PENDIENTE**: no hay evidencia que los sustente |

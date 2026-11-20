# Encargo independiente para Claude: revisión estadística E02

Actúa como especialista en inferencia estadística, problemas inversos y software
científico. Audita la pieza E02 implementada y propone referencias analíticas
independientes. No desarrolles algoritmos de producción ni ejecutes el estudio de
cobertura. Entrega hallazgos verificables, sin inventar resultados.

## Directorio y permisos de trabajo

Base: `C:\Users\Karel\Documents\Codex\2026-11-18\empaqueta-x20`.
Lee únicamente los insumos necesarios. Escribe tus entregables exclusivamente en
`outputs/CLAUDE_E02_REVIEW/`. No edites `PyFAST/`, fuentes, tests, documentación,
`.git`, datos ni corridas originales. No publiques, subas archivos ni contactes a
terceros. No importes ni ejecutes PyFAST, sus ejemplos o sus tests: esta revisión
debe ser independiente de su kernel. Puedes ejecutar un oráculo propio pequeño,
sin importar PyFAST y sin escribir fuera del directorio de entregables.

## Insumos locales, solo lectura

- `PyFAST/src/pyfast/calibration/profile.py`
- `PyFAST/src/pyfast/calibration/batch_objective.py`
- `PyFAST/docs/profile_likelihood.md`
- `PyFAST/docs/inverse_study_plan.md`
- `PyFAST/runs/profile_batch_demo_20261119_release/`: `specification.json`,
  `data_0.json`, `data_1.json`, `report.json`.

Si un insumo falta, registra `PENDING`; no lo sustituyas por cifras supuestas.
El demo es evidencia sintética de ingeniería: no es E02 confirmatorio ni prueba
de cobertura o identificabilidad global. Puedes leer dependencias locales solo
si son imprescindibles para explicar un hallazgo y debes enumerarlas.

## Revisión obligatoria

1. **Likelihood.** Comprueba sigma conocida, positiva y fija; residuales
   estandarizados; objetivo chi²; y significado exacto de
   `delta_chi2 = chi2_profile - chi2_baseline = -2 log Lambda`.
   Distingue Lambda (cociente de likelihoods) de su estadístico transformado.
   Con covarianza fija conocida Sigma, el blanqueo correcto puede ser
   r=L^(-1)(h-y), Sigma=LL^T: r^T r=(h-y)^T Sigma^(-1)(h-y).
   Determina qué soporta realmente el callback y qué valida el builder batch;
   no atribuyas covarianza general al builder si solo admite sigma diagonal.
   Si Sigma depende de parámetros, el log-determinante deja de ser constante:
   no tratarlo como un simple blanqueo fijo.
2. **Rama de ruido.** No mezcles sigma conocida con sigma estimada. Para la
   primera no corresponde n*log(RSS_profile/RSS_min); para una escala común
   desconocida perfilada por MLE esa expresión pertenece a otro modelo.
   Comprueba que documentación, demo y código no intercambian ambas ramas ni
   presentan varianza residual insesgada como sustituto de la likelihood.
3. **Regularidad y grid.** Revisa positividad/log-coordenadas, límites físicos,
   nuisance en frontera, crestas, identificación débil y cortes asintóticos
   chi²(1). Una grid finita, un perfil abierto o `accepted_grid` no son un
   intervalo continuo ni prueba de identificabilidad global. Un parámetro cero
   no está representado por coordenadas logarítmicas estrictamente positivas.
4. **Optimización.** Verifica reoptimización de todos los nuisance en cada punto,
   varios inicios, conservación de intentos fallidos y consistencia del baseline.
   Si un perfil mejora significativamente el baseline, el delta negativo es una
   señal de baseline inconsistente: no recortarlo ni convertirlo en aceptación
   válida. Distingue contrato de la API actual de ampliaciones propuestas.
5. **Presupuestos.** Separa `nfev`, llamadas reales al callback (incluidas
   diferencias finitas/excepciones) y solves físicos internos. Revisa los
   contadores del builder batch, límites agotados, fallos y reuso de resultados.
   No uses llamadas al callback como coste físico equivalente sin evidencia.
6. **Demo.** Contrasta especificación, datos y reporte sin recalibrarlos. Revisa
   unidades, verdad sintética, ruido firmado sin recorte y discrepancia numérica
   frente al ruido. Enumera lo que el demo permite concluir y lo que no.
7. **Cobertura futura.** Propón independencia de realizaciones Monte Carlo,
   generador de datos, inicios del optimizador y calibración de umbrales. Evita
   compartir datasets entre piloto, elección de umbrales y evaluación final.
   Todos los intentos planificados deben permanecer en el denominador y en el
   registro: informa éxitos, fallos e inconclusiones. Una cobertura condicionada
   a convergencia debe rotularse como tal, con su propio denominador; no presentarla
   como cobertura incondicional. Puedes proponer límites hits/M y
   (hits+inconclusos)/M, además de una tasa operacional conservadora explícita.

## Referencias analíticas propias: no reutilizar el kernel auditado

Define al menos estas tres familias con datos pequeños y resultados derivados
independientemente. Se permiten NumPy/SciPy generales, no PyFAST ni transcripción
de sus funciones. Distingue cantidades calculadas por tu oráculo de resultados
de PyFAST, que aquí no ejecutarás.

- **Media gaussiana con sigma conocida:** media interior positiva; minimizador
  y perfil exactos, delta=n*(mu-muhat)^2/sigma². Añade una variante con límites
  que requiera proyección del estimador sobre el dominio; deriva nuevamente el
  baseline restringido y no apliques la fórmula interior sin comprobarla.
- **Regresión lineal con nuisance:** y=alpha+beta*x+error, sigma conocida y
  diseño de rango completo. Deriva alpha_hat(beta), mínimo y perfil de beta;
  para óptimos interiores delta=Sxx*(beta-betahat)^2/sigma². Elige límites
  positivos compatibles con la API y añade un nuisance limitado, con solución
  restringida explícita. Incluye un caso de covarianza fija correlacionada como
  contraste algebraico del blanqueo, sin afirmar soporte del builder batch.
- **Cresta por producto:** y_i=a*b+error, a,b>0 con límites finitos. Solo el
  producto está identificado. Perfil restringido mediante
  b_hat(a)=clip(mean(y)/a, b_lower, b_upper); calcula el mínimo global factible.
  Explica cómo los límites pueden cerrar artificialmente una aceptación y por
  qué un buen ajuste no identifica a y b por separado.

Incluye hipótesis, unidades/escala, datos, parámetros/límites/grid, fórmulas,
valores esperados y tolerancias justificadas. No llames CI a puntos aceptados.
Añade casos adversos de baseline inconsistente y presupuesto agotado como
contratos esperados, sin fingir que ejecutaste la implementación auditada.

## Propuesta de Monte Carlo: exclusivamente DRAFT

Propón escenarios, verdades interiores/frontera o casi frontera, tamaños de
muestra, sigma conocida, grids, inicios, presupuesto de callbacks/solves, semillas
y métricas. Justifica M mediante precisión binomial (por ejemplo semiancho Wilson
objetivo), no por conveniencia. Enumera número total de datasets y presupuesto
máximo; separa piloto y eventual confirmación. Marca todos los valores propuestos
como `DRAFT_NOT_FROZEN`, nunca como protocolo aprobado.

La verdad generalmente no pertenece a una grid arbitraria: define una evaluación
del perfil en la verdad para estudiar inclusión/rechazo puntual, o especifica un
algoritmo posterior de inversión con cruces refinados. No calcules cobertura de
un supuesto intervalo mediante pertenencia exacta a una lista de grid. Distingue
inclusión de la verdad, cierre del perfil, amplitud de intervalo y convergencia.

**No ejecutes cobertura ni un piloto estadístico. Codex debe revisar, congelar y
hashear primero el protocolo, código, semillas y criterios.** No inventes tasas,
potencia, intervalos, tiempos, superioridad ni validación científica general.

## Entregables

1. `E02_STATISTICAL_REVIEW.md`: decisión acotada, fallos concretos, contratos
   correctos, evidencia actual y trabajo futuro. Cita ruta/función/línea para
   hallazgos de código y claves JSON para el demo.
2. `ANALYTIC_REFERENCE_CASES.json`: referencias independientes con fórmulas,
   entradas, valores esperados, tolerancias, límites de aplicabilidad y procedencia
   de cada valor (`analytic_derivation`, `own_oracle`, `proposed`).
3. `COVERAGE_PROTOCOL_PROPOSAL.md`: diseño DRAFT con precisión, semillas,
   presupuestos, denominadores, fallos y criterios falsables antes de ejecución.
4. `E02_FINDINGS.json`: lista estructurada. Por hallazgo: `id`, `severity`
   (`P0/P1/P2/P3`), `disposition` (`BUG/CONTRACT_OK/DOC_GAP/PENDING`), `file`,
   `function`, `lines`, `claim`, `expected`, `actual`, `evidence`,
   `recommended_action`, `primary_sources`, `verification_limits`.
5. Opcional: `aux/oracle.py`, original y autocontenido, con sus resultados
   claramente rotulados como cálculos del oráculo, sin importar PyFAST.

Prioriza problemas materiales; no fuerces un BUG donde solo hay una limitación
declarada. Sustenta afirmaciones metodológicas con fuentes primarias verificables
(artículos originales, libros originales o documentación oficial); cita sección,
DOI/URL y explica qué respalda cada fuente. No inventes citas ni presentes una
fuente no consultada como verificada. Si no puedes verificarla, marca `PENDING`.
No se requiere ninguna consulta a LAPSE ni nuevos reintentos de errores 429.

Concluye con decisiones concretas para Codex: aceptar, corregir o mantener
pendiente. Ningún entregable autoriza publicación, cambios de licencia ni claims
de E02 completo, cobertura nominal demostrada o validación experimental.

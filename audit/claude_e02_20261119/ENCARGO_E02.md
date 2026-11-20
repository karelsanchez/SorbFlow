\# Encargo independiente para Claude: revisión estadística E02



Actúa como especialista en inferencia estadística, problemas inversos y software

científico. Audita la pieza E02 implementada y propone referencias analíticas

independientes. No desarrolles algoritmos de producción ni ejecutes el estudio de

cobertura. Entrega hallazgos verificables, sin inventar resultados.



\## Directorio y permisos de trabajo



Base: `C:\\Users\\Karel\\Documents\\Codex\\2026-11-18\\empaqueta-x20`.

Lee únicamente los insumos necesarios. Escribe tus entregables exclusivamente en

`outputs/CLAUDE\_E02\_REVIEW/`. No edites `PyFAST/`, fuentes, tests, documentación,

`.git`, datos ni corridas originales. No publiques, subas archivos ni contactes a

terceros. No importes ni ejecutes PyFAST, sus ejemplos o sus tests: esta revisión

debe ser independiente de su kernel. Puedes ejecutar un oráculo propio pequeño,

sin importar PyFAST y sin escribir fuera del directorio de entregables.



\## Insumos locales, solo lectura



\- `PyFAST/src/pyfast/calibration/profile.py`

\- `PyFAST/src/pyfast/calibration/batch\_objective.py`

\- `PyFAST/docs/profile\_likelihood.md`

\- `PyFAST/docs/inverse\_study\_plan.md`

\- `PyFAST/runs/profile\_batch\_demo\_20261119\_release/`: `specification.json`,

&#x20; `data\_0.json`, `data\_1.json`, `report.json`.



Si un insumo falta, registra `PENDING`; no lo sustituyas por cifras supuestas.

El demo es evidencia sintética de ingeniería: no es E02 confirmatorio ni prueba

de cobertura o identificabilidad global. Puedes leer dependencias locales solo

si son imprescindibles para explicar un hallazgo y debes enumerarlas.



\## Revisión obligatoria



1\. \*\*Likelihood.\*\* Comprueba sigma conocida, positiva y fija; residuales

&#x20;  estandarizados; objetivo chi²; y significado exacto de

&#x20;  `delta\_chi2 = chi2\_profile - chi2\_baseline = -2 log Lambda`.

&#x20;  Distingue Lambda (cociente de likelihoods) de su estadístico transformado.

&#x20;  Con covarianza fija conocida Sigma, el blanqueo correcto puede ser

&#x20;  r=L^(-1)(h-y), Sigma=LL^T: r^T r=(h-y)^T Sigma^(-1)(h-y).

&#x20;  Determina qué soporta realmente el callback y qué valida el builder batch;

&#x20;  no atribuyas covarianza general al builder si solo admite sigma diagonal.

&#x20;  Si Sigma depende de parámetros, el log-determinante deja de ser constante:

&#x20;  no tratarlo como un simple blanqueo fijo.

2\. \*\*Rama de ruido.\*\* No mezcles sigma conocida con sigma estimada. Para la

&#x20;  primera no corresponde n\*log(RSS\_profile/RSS\_min); para una escala común

&#x20;  desconocida perfilada por MLE esa expresión pertenece a otro modelo.

&#x20;  Comprueba que documentación, demo y código no intercambian ambas ramas ni

&#x20;  presentan varianza residual insesgada como sustituto de la likelihood.

3\. \*\*Regularidad y grid.\*\* Revisa positividad/log-coordenadas, límites físicos,

&#x20;  nuisance en frontera, crestas, identificación débil y cortes asintóticos

&#x20;  chi²(1). Una grid finita, un perfil abierto o `accepted\_grid` no son un

&#x20;  intervalo continuo ni prueba de identificabilidad global. Un parámetro cero

&#x20;  no está representado por coordenadas logarítmicas estrictamente positivas.

4\. \*\*Optimización.\*\* Verifica reoptimización de todos los nuisance en cada punto,

&#x20;  varios inicios, conservación de intentos fallidos y consistencia del baseline.

&#x20;  Si un perfil mejora significativamente el baseline, el delta negativo es una

&#x20;  señal de baseline inconsistente: no recortarlo ni convertirlo en aceptación

&#x20;  válida. Distingue contrato de la API actual de ampliaciones propuestas.

5\. \*\*Presupuestos.\*\* Separa `nfev`, llamadas reales al callback (incluidas

&#x20;  diferencias finitas/excepciones) y solves físicos internos. Revisa los

&#x20;  contadores del builder batch, límites agotados, fallos y reuso de resultados.

&#x20;  No uses llamadas al callback como coste físico equivalente sin evidencia.

6\. \*\*Demo.\*\* Contrasta especificación, datos y reporte sin recalibrarlos. Revisa

&#x20;  unidades, verdad sintética, ruido firmado sin recorte y discrepancia numérica

&#x20;  frente al ruido. Enumera lo que el demo permite concluir y lo que no.

7\. \*\*Cobertura futura.\*\* Propón independencia de realizaciones Monte Carlo,

&#x20;  generador de datos, inicios del optimizador y calibración de umbrales. Evita

&#x20;  compartir datasets entre piloto, elección de umbrales y evaluación final.

&#x20;  Todos los intentos planificados deben permanecer en el denominador y en el

&#x20;  registro: informa éxitos, fallos e inconclusiones. Una cobertura condicionada

&#x20;  a convergencia debe rotularse como tal, con su propio denominador; no presentarla

&#x20;  como cobertura incondicional. Puedes proponer límites hits/M y

&#x20;  (hits+inconclusos)/M, además de una tasa operacional conservadora explícita.



\## Referencias analíticas propias: no reutilizar el kernel auditado



Define al menos estas tres familias con datos pequeños y resultados derivados

independientemente. Se permiten NumPy/SciPy generales, no PyFAST ni transcripción

de sus funciones. Distingue cantidades calculadas por tu oráculo de resultados

de PyFAST, que aquí no ejecutarás.



\- \*\*Media gaussiana con sigma conocida:\*\* media interior positiva; minimizador

&#x20; y perfil exactos, delta=n\*(mu-muhat)^2/sigma². Añade una variante con límites

&#x20; que requiera proyección del estimador sobre el dominio; deriva nuevamente el

&#x20; baseline restringido y no apliques la fórmula interior sin comprobarla.

\- \*\*Regresión lineal con nuisance:\*\* y=alpha+beta\*x+error, sigma conocida y

&#x20; diseño de rango completo. Deriva alpha\_hat(beta), mínimo y perfil de beta;

&#x20; para óptimos interiores delta=Sxx\*(beta-betahat)^2/sigma². Elige límites

&#x20; positivos compatibles con la API y añade un nuisance limitado, con solución

&#x20; restringida explícita. Incluye un caso de covarianza fija correlacionada como

&#x20; contraste algebraico del blanqueo, sin afirmar soporte del builder batch.

\- \*\*Cresta por producto:\*\* y\_i=a\*b+error, a,b>0 con límites finitos. Solo el

&#x20; producto está identificado. Perfil restringido mediante

&#x20; b\_hat(a)=clip(mean(y)/a, b\_lower, b\_upper); calcula el mínimo global factible.

&#x20; Explica cómo los límites pueden cerrar artificialmente una aceptación y por

&#x20; qué un buen ajuste no identifica a y b por separado.



Incluye hipótesis, unidades/escala, datos, parámetros/límites/grid, fórmulas,

valores esperados y tolerancias justificadas. No llames CI a puntos aceptados.

Añade casos adversos de baseline inconsistente y presupuesto agotado como

contratos esperados, sin fingir que ejecutaste la implementación auditada.



\## Propuesta de Monte Carlo: exclusivamente DRAFT



Propón escenarios, verdades interiores/frontera o casi frontera, tamaños de

muestra, sigma conocida, grids, inicios, presupuesto de callbacks/solves, semillas

y métricas. Justifica M mediante precisión binomial (por ejemplo semiancho Wilson

objetivo), no por conveniencia. Enumera número total de datasets y presupuesto

máximo; separa piloto y eventual confirmación. Marca todos los valores propuestos

como `DRAFT\_NOT\_FROZEN`, nunca como protocolo aprobado.



La verdad generalmente no pertenece a una grid arbitraria: define una evaluación

del perfil en la verdad para estudiar inclusión/rechazo puntual, o especifica un

algoritmo posterior de inversión con cruces refinados. No calcules cobertura de

un supuesto intervalo mediante pertenencia exacta a una lista de grid. Distingue

inclusión de la verdad, cierre del perfil, amplitud de intervalo y convergencia.



\*\*No ejecutes cobertura ni un piloto estadístico. Codex debe revisar, congelar y

hashear primero el protocolo, código, semillas y criterios.\*\* No inventes tasas,

potencia, intervalos, tiempos, superioridad ni validación científica general.



\## Entregables



1\. `E02\_STATISTICAL\_REVIEW.md`: decisión acotada, fallos concretos, contratos

&#x20;  correctos, evidencia actual y trabajo futuro. Cita ruta/función/línea para

&#x20;  hallazgos de código y claves JSON para el demo.

2\. `ANALYTIC\_REFERENCE\_CASES.json`: referencias independientes con fórmulas,

&#x20;  entradas, valores esperados, tolerancias, límites de aplicabilidad y procedencia

&#x20;  de cada valor (`analytic\_derivation`, `own\_oracle`, `proposed`).

3\. `COVERAGE\_PROTOCOL\_PROPOSAL.md`: diseño DRAFT con precisión, semillas,

&#x20;  presupuestos, denominadores, fallos y criterios falsables antes de ejecución.

4\. `E02\_FINDINGS.json`: lista estructurada. Por hallazgo: `id`, `severity`

&#x20;  (`P0/P1/P2/P3`), `disposition` (`BUG/CONTRACT\_OK/DOC\_GAP/PENDING`), `file`,

&#x20;  `function`, `lines`, `claim`, `expected`, `actual`, `evidence`,

&#x20;  `recommended\_action`, `primary\_sources`, `verification\_limits`.

5\. Opcional: `aux/oracle.py`, original y autocontenido, con sus resultados

&#x20;  claramente rotulados como cálculos del oráculo, sin importar PyFAST.



Prioriza problemas materiales; no fuerces un BUG donde solo hay una limitación

declarada. Sustenta afirmaciones metodológicas con fuentes primarias verificables

(artículos originales, libros originales o documentación oficial); cita sección,

DOI/URL y explica qué respalda cada fuente. No inventes citas ni presentes una

fuente no consultada como verificada. Si no puedes verificarla, marca `PENDING`.

No se requiere ninguna consulta a LAPSE ni nuevos reintentos de errores 429.



Concluye con decisiones concretas para Codex: aceptar, corregir o mantener

pendiente. Ningún entregable autoriza publicación, cambios de licencia ni claims

de E02 completo, cobertura nominal demostrada o validación experimental.




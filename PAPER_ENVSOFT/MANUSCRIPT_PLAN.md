# Plan del manuscrito metodológico SorbFlow

Versión del protocolo: 0.1, 2026-11-18 (America/Bogota). Estado: propuesta de estudio,
no manuscrito con resultados completos ni prerregistro público. Revista objetivo:
**Environmental Modelling & Software (Elsevier)**. No se ha sometido ningún artículo.

## Pregunta y contribución candidata

Título provisional:
*SorbFlow: An open and reproducible framework for physics-based simulation, uncertainty
quantification, and robust multi-objective design of fixed-bed adsorption systems*.

Hipótesis central H: bajo presupuestos de información y cómputo comparables, un flujo
que incorpore identificabilidad, incertidumbre paramétrica/de entradas y restricciones
físicas puede reducir incumplimiento fuera de muestra y hacer auditables las decisiones
de diseño de columnas acuosas respecto a calibración puntual y optimización determinista.
H no está demostrada. El efecto puede ser nulo o negativo, y la robustez puede tener
un costo de capacidad, material o energía que debe cuantificarse.

No se reivindican como nuevos Langmuir, Freundlich, LDF, HSDM, volúmenes finitos,
BDF/Radau, perfiles de likelihood, Monte Carlo, NSGA-II, restricciones probabilísticas,
programación en Python ni la mera integración de módulos. El aporte candidato es una
metodología **especificada, contrastable y reproducible** que conecte decisiones de
identificabilidad y error numérico con confiabilidad de diseño bajo incertidumbre.
La matriz de antecedentes y las posibles refutaciones están en NOVELTY_MATRIX.md.

## Encaje editorial y límites de la revisión

El [alcance oficial accesible de Elsevier](https://shop.elsevier.com/journals/environmental-modelling-and-software/1364-8152)
incluye cuestiones generales de modelación, evaluación y decisión ambiental. La
elección de revista es una estrategia del proyecto, no una garantía de aceptación.
La [guía específica de autores](https://www.sciencedirect.com/journal/environmental-modelling-and-software/publish/guide-for-authors)
no pudo consultarse íntegramente (HTTP 403); no se atribuyen límites de palabras,
número de figuras, requisitos de código ni cargos no verificados. Revalidarlos antes
de la sumisión. Las políticas generales Elsevier no se confunden con requisitos
particulares de esta revista.

## Arquitectura exigida por la pregunta científica

| Cambio respecto a 0.2 | Razón científica | Estado |
|---|---|---|
| Separar problema físico, observación/likelihood e inferencia | Evitar que ruido, censura o corrección empírica se incorporen al transporte sin declarar | Diseño; ajuste actual es limitado |
| Contrato de dominio validado y bandera de extrapolación | Evitar optimización de regiones sin apoyo experimental | Pendiente |
| Error numérico y clasificación de restricciones | Un balance cerrado no garantiza precisión del flujo o del umbral | Parcial; falta control de decisión |
| Experimento versionado con particiones y semillas jerárquicas | Separar ajuste, selección, escenarios de búsqueda y validación | Pendiente |
| Perfiles/multi-inicio y decisión de parametrización | Identificabilidad local por SVD no basta | Pendiente |
| Riesgo, escenarios comunes y validación probabilística independiente | Tres escenarios de búsqueda no son una garantía de confiabilidad | Pendiente; solo ejemplo preliminar |
| Cola persistente de tareas y caché por contenido | Reanudación verificable, trazabilidad de fallos y presupuesto real | Pendiente |
| Registro afirmación→experimento→artefacto | Impedir que una funcionalidad se presente como evidencia de superioridad | Este dossier |
| Caso de estudio en paquete de datos separado | Mantener generalidad y evitar dependencia de cuatro materiales | Contrato definido |

No se reservan en una edición comercial las funciones, scripts, configuraciones o
datos autorizados indispensables para reconstruir los resultados del artículo.
CAD empresarial, gestión de proyectos y automatización documental pueden estar
separados. La licencia abierta definitiva exige resolver titularidad.

## Cuatro experimentos y un experimento de ejecución

| ID | Pregunta principal | Comparador/resultado requerido | Estado hoy |
|---|---|---|---|
| E01 | ¿Resuelve correctamente las ecuaciones dentro del dominio declarado? | Analíticas/manufacturadas, refinamiento, masa, límites y FAST solo autorizado | Referencias seleccionadas ejecutadas; protocolo completo pendiente |
| E02 | ¿Cuándo y con qué datos son identificables los parámetros? | Verdades sintéticas, multi-inicio, perfiles, cobertura y recuperación | Recuperación simple/SVD ejecutadas; estudio completo pendiente |
| E03 | ¿La metodología robusta mejora decisiones fuera de muestra? | Convencional, determinista, robusta y ablaciones a igual presupuesto | No ejecutado; demo de 3 escenarios no lo sustituye |
| E04 | ¿Se transfiere a ensayos ambientales independientes? | Columnas de los cuatro materiales y, si es posible, otro sistema | Datos autorizados no aportados; no ejecutado |
| E05 | ¿Se reconstruyen y escalan ejecuciones sin cambiar conclusiones? | Serial/paralelo, fallos, reanudación y entorno externo | Pruebas de paquete locales; estudio distribuido pendiente |

E01–E05 tienen criterios y estados separados. Un resultado positivo en una capa
no se transfiere a otra por analogía. Las comparaciones externas documentarán
si se ejecutó realmente el software o solo se revisó su documentación.

## Estructura propuesta del artículo

1. Introducción: decisión ambiental y brecha verificable; antecedentes y alcance.
2. Formulación física y modelo de observación: hipótesis, unidades, incertidumbres,
   identificación de dominio y cantidades de decisión.
3. Metodología integrada: verificación numérica, calibración identificable,
   propagación, riesgo y diseño robusto con evaluación fuera de muestra.
4. Arquitectura reproducible: contratos, artefactos, paralelismo/reanudación,
   separación del caso de aplicación y disponibilidad científica.
5. Protocolo comparativo E01–E05, presupuestos y análisis estadístico predefinidos.
6. Resultados reales, con tablas/figuras generadas desde registros; también fallos.
7. Discusión: cuándo aporta valor, costo de robustez, límites químicos y de datos,
   sesgos de modelo y amenazas a validez interna/externa.
8. Conclusiones limitadas a hipótesis examinadas; disponibilidad, contribuciones,
   financiación, intereses y declaraciones editoriales aplicables verificadas.

No redactar resultados esperados como resultados observados. Una demostración
sintética se identifica como tal incluso cuando produce figuras terminadas.

## Figuras y tablas previstas, aún sin resultados completos

| Artefacto | Experimento | Contenido y condición de inclusión |
|---|---|---|
| F01 | Diseño | Flujo causal información→inferencia→escenarios→diseño→prueba independiente |
| F02 / T02 | E01 | Error vs malla/tolerancia, masa y regímenes; no solo curvas superpuestas |
| F03 / T03 | E02 | Perfiles, recuperación/cobertura y relación con diseño experimental |
| F04 / T04 | E03 | Pareto fuera de muestra, incumplimiento con intervalos, costo de robustez |
| F05 / T05 | E05 | Tiempo, eficiencia, memoria, fallos/reanudación y reconstrucción |
| F06 / T06 | E04 | Validación externa con incertidumbre y datos retenidos |
| T01 | Antecedentes | Novedad candidata vs integración/aplicación, fuentes y alcance revisado |

Cada celda de resultados tendrá run_id, commit, dataset/scenario hash y script.
Las figuras actuales en examples son demostraciones y no rellenan automáticamente
las tablas E02–E05 del artículo. Si E04 no puede completarse, declarar la limitación
y reevaluar el alcance del manuscrito en lugar de inventar una aplicación validada.

## Regla de avance y separación de publicaciones

Congelar protocolo, escenarios, métricas y presupuestos antes de ejecutar el estudio
confirmatorio. Pilotos se etiquetan y no se reutilizan como test independiente.
El artículo metodológico evalúa generalización, mecanismos y límites del framework;
el artículo experimental estudia adsorbentes/mezclas específicos. Si comparten datos,
declarar procedencia, reutilización y relación de preguntas, sin duplicar resultados
como contribuciones independientes. La revisión externa de método y derechos se
registra antes de una release pública y de cualquier sumisión.

# Matriz de novedad, antecedentes y afirmaciones refutables

Versión 0.1, consulta 2026-11-18. Revisión documental dirigida, **no revisión
sistemática exhaustiva**. No se midió desempeño de competidores ni se incorporó su
código. La ausencia de una función en las páginas consultadas no prueba su inexistencia.
La documentación consultada puede diferir de la release exacta de un artículo.

## 1. Tres tipos de aporte que no deben confundirse

**Método candidato:** regla definida que modifica cómo se formula/acepta una decisión
al incorporar información de identificabilidad, incertidumbre y error numérico;
requiere comparación causal/ablaciones y revisión de prioridad. **Integración:**
contratos, API, trazabilidad y acoplamiento de métodos conocidos; su valor debe medirse,
sin denominarlo un algoritmo nuevo. **Aplicación:** evidencia ambiental sobre adsorbentes,
mezclas y columnas específicas; no prueba generalización del framework por sí sola.

LDF/HSDM, Langmuir/Freundlich, Ergun, FV, BDF/Radau, SVD/perfiles, Monte Carlo,
NSGA-II, cuantiles/CVaR y restricciones probabilísticas son métodos establecidos.
Python, una GUI, paralelismo o CAD tampoco constituyen novedad científica automática.

## 2. Antecedentes primarios y comparabilidad

| Antecedente / fuente primaria | Alcance documentado pertinente | Implicación y límite de comparación |
|---|---|---|
| [SWAT-UQ](https://doi.org/10.1016/j.envsoft.2026.106935), [docs](https://swat-uq.readthedocs.io/en/latest/) | Integra SWAT/UQPyL para calibración, incertidumbre y optimización; colas distribuidas, scripts y GUI | Integración/UQ/paralelo ya tienen antecedentes. Dominio hidrológico: no es referencia de exactitud de adsorción acuosa |
| [Optienv WRHGroup](https://wrhgroup.github.io/optienv/introduction.html), [arquitectura](https://wrhgroup.github.io/optienv/modules.html) | Adaptación de simuladores por CSV/JSON, NSGA-II/III, semillas, historiales, checkpoints y análisis de frentes/HV | La interoperabilidad y reanudación tampoco son nuevas. Para compararlo, usar el mismo evaluador físico y presupuesto |
| [UQPyL](https://www.uqpyl.com/en/user-guide), [repositorio](https://github.com/smasky/UQPyL) | Interfaz común para muestreo, sensibilidad, inferencia, calibración, sustitutos y optimización | Unificar módulos no demuestra prioridad; comparar composición y decisiones, no solo lista de funciones |
| [EMA Workbench, artículo](https://doi.org/10.1016/j.envsoft.2017.06.054) | Framework de modelación exploratoria, descubrimiento de escenarios y decisión robusta multiobjetivo | El enfoque robusto ambiental general ya existe; el aporte acuoso debe formularse y evaluarse específicamente |
| [OpenMORDM](https://www.scrim.psu.edu/resources/openmordm/) | Diseño robusto, estados inciertos, vulnerabilidades y trade-offs | Ni la robustez por escenarios ni la evaluación de vulnerabilidades son novedosas por sí mismas |
| [pysorb](https://pypi.org/project/pysorb/) | Ajuste de isotermas, mezclas, difusión y ruptura | No alegar primera biblioteca Python de adsorción; confirmar formulación/unidades antes de comparar motores |
| [RUPTURA](https://iraspa.org/ruptura/) | Ruptura para gases, equilibrio de mezclas y ajuste de isotermas | Motor abierto relevante; una ecuación de gas no es intercambiable sin más con la formulación acuosa |
| [pyAPEP](https://sebygaa.github.io/pyAPEP/build/html/index.html) | Ajuste y simulación de procesos PSA | Antecedente de software de procesos; restringir comparaciones a hipótesis compatibles |
| [pyDAC](https://github.com/process-intensification-lab/pyDAC) | Simulación de adsorción/captura de CO2 y NSGA-II | Optimización multiobjetivo acoplada a adsorción ya está documentada; dominio/ciclos diferentes |
| [FAST adsorción](https://www.fast-software.de/), [licencia/FAQ](https://www.fast-software.de/faq.html) | HSDM/LDF para ruptura acuosa; distribución con restricciones NC/ND declaradas | Antecedente cercano; comparación condicionada a permisos, versión y contrato I/O. No es un oráculo de verdad |

Identidad de SWAT-UQ resuelta por [ficha editorial](https://www.sciencedirect.com/science/article/pii/S1364815226000824),
repositorio y documentación vinculados. En sus tutoriales, FAST de sensibilidad significa
**Fourier Amplitude Sensitivity Test**, distinto del FAST de adsorción.

Optienv se refiere a WRHGroup, identificado por enlaces editor–repositorio–docs, no
a proyectos homónimos. Su [artículo asociado por DOI](https://doi.org/10.1016/j.envsoft.2026.107216)
figura asignado a un fascículo de enero de 2027. Esa fecha es futura respecto a esta
consulta; la fecha online exacta no se verificó y no se afirma que enero de 2027 ya
ocurrió. El análisis funcional se sustenta en documentación de software accesible.
No se asigna un método XAI concreto no verificado al artículo por analogía.

Este conjunto es punto de partida. Ampliar una búsqueda reproducible con términos
adsorption/fixed-bed/water, identifiability, uncertainty, robust optimization/chance
constraints y numerical error; registrar consulta, fecha, inclusión/exclusión y
versiones. Buscar antecedentes de cada regla metodológica específica, no solo nombres
de paquetes. Revisar trabajos posteriores al corte antes de someter y documentar cambios.

## 3. Regla operacional candidata a contrastar

1. Verificar ecuaciones/dominio y error numérico antes de aceptar un resultado físico.
2. Ajustar múltiples inicios y perfilar parámetros y cantidades de decisión relevantes.
3. Si theta no es identificable pero la cantidad de decisión sí está determinada,
   no rechazar automáticamente el diseño: propagar las dependencias y evaluar su riesgo.
4. Si la decisión queda indeterminada, aplicar una acción predefinida: reparametrizar,
   elegir información adicional bajo presupuesto o declarar INCONCLUSIVE. No fijar
   parámetros arbitrariamente para producir intervalos estrechos.
5. Construir escenarios compatibles con datos/supuestos y mantenerlos comunes en la búsqueda.
6. Si el signo de una restricción cambia con malla/tolerancia, refinar o declarar
   posible fallo/no resuelto; no certificar factibilidad por conservación de masa sola.
7. Seleccionar candidatos antes del test y medir riesgo/costo fuera de muestra con
   incertidumbre y control de multiplicidad.

La regla deberá fijar disparadores/acciones/márgenes antes de E02/E03. Todavía no es
un método nuevo demostrado: sus componentes pueden tener antecedentes equivalentes.
Su valor se examina con ablaciones, mismos datos y presupuesto total, incluidos
perfiles, refinamientos, escenarios, reintentos y experimentos adicionales.

## 4. Registro C01–C08

| ID / tipo | Afirmación candidata, acotada | Estado de evidencia actual | Experimento y comparador | Qué la apoya / refuta o limita |
|---|---|---|---|---|
| C01 · habilitante | El motor aproxima las ecuaciones declaradas dentro de tolerancias en regímenes examinados | Referencias numéricas seleccionadas, no validación universal | E01: analíticas/MMS, matrices independientes, refinamientos y límites | Apoya error/masa/orden y decisiones estables; limita un flujo errado pese a masa cerrada, régimen fallido o clasificación de malla cambiante |
| C02 · integración | Nuevos materiales/contaminantes/mezclas se instancian por datos/modelos públicos, sin ramas específicas en el core | IDs/recetas configurables; no generalización química demostrada | E04/E05: paquete de caso nuevo y flujo manual equivalente | Apoya reconstrucción por contratos; refuta necesitar parches por identidad o leyes de mezcla ocultas |
| C03 · metodología candidata | Diagnóstico de identificabilidad conduce a acciones útiles para inferencias/decisiones bajo información limitada | SVD y recuperación simples; perfiles/globalidad pendientes | E02: verdades identificables/no identificables, multi-inicio/perfiles; ablación sin diagnóstico | Apoya detección correcta y mejora de cobertura/decisión o no-resolución honesta; limita beneficio solo por datos extra o rechazo innecesario de QoI identificable |
| C04 · metodología/integración | La propagación de incertidumbre declarada produce predicciones/intervalos calibrados y útiles en el dominio | MC y aproximación local, sin estudio de cobertura completo | E02/E04: datasets repetidos y ensayos retenidos; baseline plug-in/local | Apoya cobertura y anchura útil; refuta subcobertura, intervalos inútiles o fuentes relevantes omitidas |
| C05 · hipótesis central | A igual información/cómputo, la metodología robusta reduce incumplimiento fuera de muestra y explicita su costo | Demo de 3 escenarios/11 candidatos, no evidencia confirmatoria | E03: convencional, determinista, robusto y ablaciones, múltiples semillas y test independiente | Apoya efecto mínimo predefinido con IC y costo aceptable; limita/refuta efecto adverso o beneficio mínimo excluido con precisión suficiente; IC que cruza cero es inconcluso, no refutación automática; limitar ventaja que desaparece al igualar presupuestos |
| C06 · mecanismo candidato | Controlar error numérico en restricciones reduce falsos factibles cerca de la frontera | Refinamiento seleccionado; política de decisión general pendiente | E01/E03: regla gruesa vs margen/refinamiento; referencia fina independiente | Apoya menor falso cumplimiento con costo/rechazos útiles; refuta margen insuficiente o regla que rechaza toda solución útil |
| C07 · reproducibilidad/ingeniería | Artefactos y ejecución permiten reconstrucción y recuperación/paralelo sin alterar conclusiones indebidamente | Paquete local; arnés SMOKE separado; sin estudio distribuido | E05: instalación externa, serial/paralelo, corrupción/interrupciones/reanudación | Apoya integridad/equivalencia y recursos medidos; refuta pérdidas, duplicados, dependencia del orden o speedup no medido |
| C08 · aplicación/transferencia | El framework predice ensayos ambientales retenidos y genera cantidades de diseño dentro de un dominio declarado | Sin datos experimentales autorizados aportados; DXF de envolvente no prueba predicción | E04: ensayos completos retenidos, parámetros/mapping congelados y modelo de observación | Apoya errores/cobertura acordes a incertidumbre; refuta reajuste con test, extrapolación no declarada o fallos químicos/hidráulicos |

Ninguna fila está marcada como superioridad demostrada. C01 puede recibir apoyo
parcial sin cerrar C03–C08; un resultado negativo también puede delimitar una
contribución científica útil. Una API funcional no sustituye el experimento de la fila.

## 5. Comparaciones admisibles y no admisibles

Para motores de adsorción, igualar formulación, condiciones iniciales/frontera,
propiedades, unidades y precisión; si no puede hacerse, declarar no comparabilidad.
Para SWAT-UQ/Optienv u otros orquestadores, usar el mismo evaluador acuoso cuando
sus interfaces y licencias lo permitan. No comparar error hidrológico con error HSDM
ni atribuir al orquestador el error del modelo externo.

Para desempeño, misma familia de hardware, presupuesto de solves físicos y conjunto
de tareas; contar costo de incertidumbre y adquisición de información. El hipervolumen
requiere objetivos/normalización/referencia comunes. Un frente Pareto no es un posterior.
Escenarios de búsqueda, validación física y test de confiabilidad son particiones distintas.

## 6. Formulaciones de novedad permitidas antes de resultados

Usar: «se propone y evaluará», «hipótesis de valor», «contribución candidata», «evidencia
parcial en referencias seleccionadas». No usar como conclusión: «primero», «único»,
«más rápido», «más exacto», «más robusto», «identificabilidad global», «confiabilidad
95%», «validado industrialmente» o «universal para contaminantes». El título *open*
está condicionado a titularidad, licencia y disponibilidad efectiva.

Regla transversal de interpretación: si los intervalos no resuelven el efecto mínimo, el estado es INCONCLUSIVE. No usar ausencia de significación como prueba de equivalencia o refutación. Los claims se limitan cuando datos suficientemente informativos excluyen el beneficio propuesto o muestran perjuicio.

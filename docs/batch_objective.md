# Objetivo batch para perfiles con ruido conocido

Contrato experimental: `sorbflow.calibration.batch_objective.BatchExperiment` reúne
un `BatchConfig` lineal/LDF y una serie `Observations` con desviaciones estándar
conocidas, positivas, en kg/m³. No estima ni imputa esas desviaciones.

`LinearBatchObjective(experiments, options=...)` es un callback determinista para
optimización/perfiles. Recibe `[K, k_LDF]` positivos en m³/kg y s⁻¹, reemplaza ambos
parámetros en copias de las configuraciones y concatena `(c_pred-c_obs)/sigma`.
Cada evaluación usa el solver batch existente. No promedia ensayos ni modifica datos.
La malla de integración añade cero y el horizonte configurado cuando no están en los
tiempos observados; esos puntos no se convierten en observaciones ni residuales.
`code_revision=` identifica el commit en los resultados internos del solver;
el valor por defecto `uncommitted` no certifica una versión publicada.

Los experimentos deben compartir material, especie y temperatura para compartir
estos dos parámetros. Pueden variar masa, volumen, tiempos y estados iniciales
conocidos. Sus IDs son únicos; el usuario debe justificar independencia estadística:
IDs diferentes no la demuestran. Configuraciones no lineales se rechazan.

El contador `physical_solves` incluye cada intento de simulación, incluso si falla.
Es distinto del número de callbacks del perfil: un callback puede resolver varios
experimentos. No se cuentan comprobaciones de argumentos como solves. Los hashes
de configuración y observaciones identifican las entradas declaradas; no certifican
procedencia, exactitud de las observaciones o independencia.

El esquema `Observations` actual admite concentraciones no negativas y no incorpora
censura. No usar este objetivo para descartar valores negativos de un generador
Gaussiano ni para convertir LOQ/2 en observaciones exactas. Un estudio con ruido que
pueda cruzar cero necesita un esquema/likelihood apropiado; no recortar esos datos.

Refinar las tolerancias y comprobar su efecto sobre la likelihood antes de inferir
intervalos. La convergencia del ajuste y la identificabilidad se evalúan con los
diagnósticos del optimizador y los perfiles. El estudio E02 evaluó la cobertura de
este objetivo con 3.000 datasets sintéticos ([resultados](benchmark_results.md)).

[Perfiles de verosimilitud](profile_likelihood.md) ·
[Diseño E02-A](inverse_study_plan.md) · [Índice](index.md)

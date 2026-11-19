# Perfil gaussiano con sigma conocida: contrato experimental

Esta API implementa una pieza de [E02-A](inverse_study_plan.md), no su estudio
confirmatorio. No cambia el [ajuste local existente](../API_REFERENCE.md) ni prueba
identificabilidad global, cobertura nominal o validez experimental.

Importar desde `pyfast.calibration.profile`:

```python
from pyfast.calibration.profile import ProfileParameter, profile_gaussian_known_sigma

parameters = (ProfileParameter("K", "m^3/kg", 0.01, 10.0),)
result = profile_gaussian_known_sigma(
    lambda theta: [(theta[0] - 2.0) / 0.2],
    parameters, [[0.5], [4.0]], parameter="K", grid=[1.0, 2.0, 3.0],
    max_callback_calls=1000,
)
```

## Entradas y likelihood

`weighted_residual(theta)` recibe vector físico positivo de solo lectura y devuelve
un vector real 1D, no vacío, finito y de longitud constante. Debe ser determinista,
sin alterar el estado numérico entre evaluaciones: r_i=(h_i(theta)-y_i)/sigma_i,
donde sigma_i>0 es
**conocida** y fija. El callback incorpora datos, unidades coherentes y sigma;
la API no puede verificar su interpretación científica. No ofrece estimación de
sigma, censura, errores en variables ni correlación no blanqueada.

Cada `ProfileParameter(name, unit, lower, upper)` declara nombre único, unidad
reconocida y límites finitos con 0<lower<upper. La unidad se valida, pero **no se
convierten** valores: starts, bounds, grid y callback deben usar la misma unidad
declarada, preferentemente SI. No mezclar bases húmedas/secas.

`starts` es una matriz (n_inicios,n_parámetros), finita, positiva y dentro de límites;
`parameter` identifica un nombre; `grid` es 1D, finita, positiva, estrictamente
creciente y dentro de sus límites. Las posiciones son elegidas por el usuario.
Los parámetros estrictamente positivos no representan fronteras en cero.

El ajuste minimiza chi²=sum(r_i²) en coordenadas logarítmicas con límites explícitos
y varios inicios, usando SciPy `least_squares`. El baseline usa todos los inicios.
En cada punto se fija el parámetro objetivo y se reoptimizan **todos** los nuisance
desde los mismos inicios suministrados. No se sustituye un perfil por una sección.
Sin nuisance, cada punto requiere solamente evaluar sus residuales.

## Resultado y límites de interpretación

Dataclasses frozen y tuples conservan todos los intentos: inicio físico efectivo,
terminación, mensaje, parámetros/chi² disponibles, llamadas y parámetros próximos
a límites. Un intento fallido no participa como óptimo convergente; no se borra.
Los errores del callback/optimizador se registran por intento. Un retorno no 1D,
no finito o de longitud distinta también es un fallo. Errores de configuración
se rechazan antes de evaluar el callback.

`delta_chi2=chi2_profile-chi2_baseline` es −2 log Λ, el estadístico de razón de
verosimilitudes gaussiana con sigma conocida. No se recorta a cero. Si mejora el baseline más que
`baseline_tolerance` (tolerancia absoluta en chi²), el estado es
`BASELINE_INCONSISTENT`: conservar evidencia y volver a ajustar fuera de esta
llamada; no sustituir silenciosamente el baseline ni emitir aceptación.

`cutoff=chi2.ppf(confidence,1)` usa aproximación asintótica de un parámetro bajo
regularidad e interioridad. No es garantía de cobertura con poca información,
fronteras o no identificabilidad; tales casos requieren el estudio independiente
del [protocolo](../PAPER_ENVSOFT/BENCHMARK_PROTOCOL.md).

`accepted_grid` contiene únicamente valores calculados con delta<=cutoff y
baseline consistente. No es un intervalo continuo: no interpola cruces, rellena
huecos, extrapola ni declara identificabilidad porque existan puntos rechazados.
`edge_status` informa cada extremo como REJECTED, GRID_TRUNCATED (aceptado pero
grid acaba antes del límite físico), BOUND_LIMITED (aceptado en límite físico) o
UNAVAILABLE (fallo/baseline inconsistente). Límites de nuisance se registran además
en cada intento/punto. Una cresta puede ocupar toda la grid sin producir un CI
cerrado. Un perfil sin aceptación también requiere revisar resolución y mínimo.

Estados globales: COMPLETE significa evaluaciones de la grid completas, nunca
verificación global; INCOMPLETE indica puntos sin éxito; BASELINE_FAILED no tiene
mínimo baseline convergente; BUDGET_EXHAUSTED preserva resultados parciales;
BASELINE_INCONSISTENT tiene prioridad cuando se detecta mejor mínimo significativo.
`accepted_grid` puede ser parcial: siempre inspeccionar estado y todos los puntos.

## Presupuesto y evidencia

`max_callback_calls` limita globalmente llamadas **reales** al callback, incluidas
las de Jacobianos numéricos y las que lanzan excepciones. El contador se incrementa
al invocar el callback; tras agotar el techo no vuelve a invocarlo. Intentos que
no pudieron comenzar quedan registrados. `max_nfev` es otro límite por intento de
SciPy y no equivale al contador real. Ninguno cuenta solves físicos internos: un
callback puede realizar cero, uno o varios; el evaluador debe instrumentarlos.

Las pruebas analíticas controlan mínimos, nuisance y fallos. No son todavía el
estudio E02-A de cobertura, ni una validación experimental. No se ejecuta FAST.

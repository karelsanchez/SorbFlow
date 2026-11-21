# API pública — prototipo 0.2

Python >=3.11, unidades SI y masa seca. Se conservan las API de datos de 0.1;
`Linear` se añade como variante del esquema v1. Un lector antiguo no entenderá esa
variante nueva; los archivos antiguos siguen siendo legibles. No hay migración implícita.

## Datos y unidades

Desde `sorbflow`: `quantity`, `to_si`, `UnitError`, `Species`, `Bed`, `Operation`,
`Langmuir`, `Freundlich`, `Linear`, `LDF`, `HSDM`, `SimulationConfig`, `BatchConfig`,
`Observations`, `RunManifest`, `BlendComponent`, `AdsorbentBlend`.
Constructores SI validan rangos/tipos; dataclasses congeladas. Las fábricas dimensionales
`Bed.from_quantities` y `Operation.from_quantities` convierten Pint a SI.
Configuraciones soportan `to_json`, `from_json`, `sha256`; claves duplicadas o desconocidas
se rechazan. Blend tiene `to_json` y N componentes de fracción másica seca positiva,
suma uno y nombres distintos, sin ley de mezcla implícita.

## Equilibrio

`sorbflow.equilibrium.isotherm_from_parameters(parameters)` construye un `Isotherm`.
`loading(c)` devuelve kg/kg y `derivative(c)` devuelve m³/kg conservando la forma
del array de entrada. c se expresa en kg/m³, no puede ser negativo, NaN o infinito.
Langmuir, Freundlich normalizado y lineal implementan el protocolo. Freundlich con
exponente<1 informa derivada singular en c=0; no la regulariza.
Temperatura fija: parámetros deben corresponder a la temperatura del ensayo.

## Simulación

`sorbflow.simulate.batch(BatchConfig, time_s=None, options=None, code_revision='uncommitted')`
resuelve dos estados LDF en batch cerrado.
`sorbflow.simulate.column(SimulationConfig, ...)` selecciona LDF o HSDM de forma explícita.
HSDM agrega difusión radial esférica y película; no incluye agua intrapartícula.

`SolverOptions` en `sorbflow.solvers`: BDF/Radau, rtol, tolerancias absolutas separadas
de c, q y masa, tolerancia relativa/escala de masa, max_step_s, axial_cells y radial_cells.
`time_s` es una malla de observación estrictamente creciente desde 0 hasta duración;
no prescribe los pasos internos. Por defecto son 201 observaciones.
Fallos de integración, estados no finitos, negatividad superior a diez atol o balance
fuera de tolerancia generan `SimulationError`, sin reparar ni recortar los resultados.

`SimulationResult`: arrays de c y carga media con forma (tiempo, celda axial), inventario
y masas acumuladas, centros z, diagnósticos en pasos internos y salidas, configuración,
opciones, `numerical_sha256` y manifiesto con versiones/UUID/UTC/revisión. Batch tiene
una celda. HSDM agrega `radial_loading_kg_kg` (tiempo, axial, radial) y `r_m`.
`outlet_concentration_kg_m3` es última celda FV o líquido batch. Arrays son snapshots
de solo lectura. `to_json` conserva datos/unidades; ningún resultado afirma validación
experimental. La revisión Git se aporta explícitamente; el valor por defecto indica
estado no congelado. La huella numérica incluye configuración, opciones, tipo y tiempos;
las versiones se guardan en el manifiesto.

`sorbflow.io.export_result(result, nueva_carpeta)` escribe JSON, CSV de salida/balance
y huellas de archivos. Rechaza carpetas existentes. La CLI `python -m sorbflow` acepta
`batch|column`, configuración JSON y `--output`; opciones `--cells`, `--radial-cells`,
`--method`, `--rtol`, `--samples`, `--code-revision`.

## Ajuste inverso

`sorbflow.fit.isotherm(c, q, initial, std_loading_kg_kg=None, max_nfev=1000)` estima
parámetros positivos con least_squares en log-coordenadas. Freundlich conserva c_ref.
`sorbflow.fit.batch_rate(config, observations, max_nfev=100)` estima solo k_LDF.
Condiciones, equilibrio, identidad de especie y tiempos deben ser coherentes.
No admite datos censurados ni errores en las concentraciones de equilibrio.

`FitResult` contiene parámetros, predicciones/residuales, SVD, rango/condición y
covarianza local en log-parámetros (None si rango/condición no son adecuados).
`locally_identifiable` no establece identificabilidad global. Con sigma conocida
se usa su modelo de error; sin ella se estima varianza residual con grados de libertad.
Un optimizador no convergente produce FitError, no un resultado exitoso.

## Incertidumbre y sensibilidad

`sorbflow.uncertainty.monte_carlo(evaluate, sampler, n_samples, seed, model_id, probabilities)`
usa Generator local y registra muestras SI, salidas, media, desviación, error estándar
de la media y cuantiles. El sampler recibe (Generator,n) y devuelve matriz (n,p);
evaluate recibe un vector p y devuelve escalar/vector. Un fallo aborta con índice,
sin condicionar sobre casos sobrevivientes. El usuario preserva código del muestreador,
correlaciones e identidad del modelo. Cuantiles de propagación no son automáticamente
intervalos de credibilidad o confianza con cobertura demostrada.
`local_sensitivity(evaluate, point_si, steps_si)` calcula Jacobiano central;
pasos por parámetro explícitos, sin cambios de frontera automáticos.

## Diseño y multiobjetivo

`sorbflow.design.hydraulics(bed, flow_m3_s, fluid_density_kg_m3, viscosity_pa_s, pump_efficiency)`
devuelve EBCT, residencia líquida, masa seca, pérdida Ergun, potencia y Re de partícula.
Se excluyen soporte, pared, forma no esférica, hinchamiento y ensuciamiento.
`cost_estimate(design, CostBasis(...), service_time_s)` suma adsorbente y electricidad
con precios, moneda/año declarados; no es costo de ciclo de vida.
`export_dxf(bed,path)` crea envolvente cilíndrica de proceso en metros, sin sobrescribir.
No calcula estructura, espesor ni accesorios; STEP requiere un adaptador posterior.

`sorbflow.optimize.nsga2(evaluate, lower_bounds_si, upper_bounds_si, objective_units,
variable_units, problem_id, seed, n_constraints=0, population_size=80, generations=100)`
usa el extra optativo pymoo. Evaluate devuelve `Evaluation(objectives, constraints)`;
todos los objetivos se minimizan y las restricciones normalizadas satisfacen g<=0.
Las unidades son metadatos explícitos del evaluador: no se convierten precios ni
funciones objetivo automáticamente. Se reevalúa cada punto final, se exige repetibilidad
y factibilidad y se registra la especificación/versiones. Para diseño robusto usar
escenarios congelados comunes entre candidatos. El usuario debe demostrar convergencia,
reevaluar en malla fina y ampliar escenarios antes de aceptar un diseño industrial.

`sorbflow.validate.mass_balance(result)` recalcula el cierre en tiempos exportados;
los diagnósticos del solver incluyen también pasos internos. No es validación física.

## CSV experimental y Parquet opcional

`sorbflow.io.load_breakthrough_csv(path, experiment_id, species_name, time_column, concentration_column, time_unit, concentration_unit, std_column=None, std_unit=None, delimiter=",")` exige argumentos nombrados y unidades. Devuelve Observations en SI con SHA-256 de bytes originales, BOM opcional y errores por fila/columna. Rechaza cabeceras repetidas, registros vacíos, censura no declarada y tiempos no ordenados; no limpia ni modifica el original. Columnas de metadatos adicionales quedan intactas en el CSV fuente y no se incluyen en Observations.

`export_parquet(result, destination)` usa el extra `[parquet]` (PyArrow), con importación perezosa. Guarda tabla temporal de salida y balance, unidades por campo y metadatos de configuración/opciones/manifiesto/diagnósticos/huella. No guarda perfiles completos: para ellos usar JSON. Rechaza sobrescritura mediante apertura exclusiva; un fallo I/O durante escritura puede dejar un archivo parcial nuevo.

## Interfaz local opcional

`python -m sorbflow.web --host 127.0.0.1 --port 8765 --output runs/gui` inicia un
servidor local que invoca los mismos esquemas y simuladores. No requiere extras
de interfaz. El contrato HTTP es interno de este prototipo, no una API remota
estable. Flujo, límites y descargas: [guía de la GUI](docs/web_interface.md).

## Calibración experimental con sigma conocida

`sorbflow.calibration.profile.profile_gaussian_known_sigma` conserva multiinicios,
reoptimización de nuisance, fallos y presupuestos reales de callback. Su salida
es evidencia sobre una malla de parámetros positivos: no un intervalo continuo
ni una prueba de identificabilidad global. [Contrato](docs/profile_likelihood.md).

`sorbflow.calibration.batch_objective.LinearBatchObjective` conecta esa interfaz con
varios batches lineales/LDF y sigma declarada conocida. Comparte K/k entre ensayos
compatibles y cuenta intentos físicos de simulación. No sustituye la API existente
`batch_rate` ni implementa una likelihood censurada. [Contrato](docs/batch_objective.md).

# PyFAST — arquitectura propuesta

Fecha: 2026-11-18. Estado: fundación 0.1.0.dev0; ningún solver implementado ni validado.

## Alcance y procedencia

Implementación independiente del balance de adsorción, sin derivar código de FAST.
El ZIP local de FAST 2.1 beta solo contiene ejecutables y ayuda gráfica; no permite
auditar su discretización, integradores ni optimización. Véase IP_LICENSE_AUDIT.md.
Los cinco documentos de diseño preceden a la implementación de unidades y esquemas.

## Decisiones

1. Python >=3.11, distribución con layout `src`, `pyproject.toml`, wheel/sdist,
   anotaciones, `py.typed`, dataclasses congeladas y pytest. Sin estado global de ejecución.
2. Pint convierte magnitudes escalares al ingresar; los esquemas almacenan floats SI.
   El núcleo numérico futuro operará sobre arrays SI y recibirá parámetros explícitos.
   No habrá conversiones silenciosas de concentración molar a másica ni de base húmeda a seca.
3. Dominio inicial: una especie acuosa, lecho uniforme, operación isotérmica, flujo
   positivo constante, adsorción reversible, densidades en base seca. Extensiones
   multicomponente y térmicas requieren nuevas versiones del contrato.
4. Solver propio significa balances, flujos, discretización, Jacobiano y diagnósticos
   desarrollados aquí. Se reutilizarán integradores públicos de SciPy, no se escribirá
   un integrador rígido desde cero. No se dependerá de FAST para resolver el modelo.
5. Ninguna dependencia del core importa ejecutables, plugins comerciales ni interfaces gráficas.
6. La API pública documentada se mantiene durante la serie 0.1; cambios incompatibles
   requieren versión menor, migración y advertencia. La estabilidad 1.0 es un hito posterior.

## Módulos y dirección de dependencias

| Módulo | Responsabilidad | Estado inicial |
|---|---|---|
| `units` | Validación dimensional, escalares finitos, conversiones SI | Implementado |
| `schemas` | Especie, material, geometría, operación, observaciones, manifiestos | Implementado |
| `equilibrium` | Langmuir, Freundlich normalizado y protocolos de extensión | Reservado |
| `kinetics` | LDF efectiva, HSDM con película | Reservado |
| `reactors` | Columna 1D; batch conservativo para referencias | Reservado |
| `solvers` | Volúmenes finitos, integración, eventos, diagnósticos | Reservado |
| `calibration` | Likelihood, errores, límites, perfiles e identificabilidad | Reservado |
| `uncertainty` | Muestreo con semillas, propagación, sensibilidad | Reservado |
| `optimization` | Restricciones, objetivos y Pareto | Reservado |
| `io` | Formatos versionados, resultados y trazabilidad | Reservado |
| `adapters` | Interoperabilidad externa optativa y aislada | Reservado |

`units <- schemas <- modelos <- reactores <- solvers <- workflows`.
`io` y adaptadores dependen de contratos públicos; el núcleo nunca depende de ellos.
No se ofrecen funciones `simulate` ficticias en esta entrega.

## Contratos científicos futuros

Isotherm: `loading(c, temperature)` y derivada con unidades declaradas y dominio.
Kinetics: fuente de masa sólida, estados adicionales y parámetros validados.
Reactor: geometría, inventarios, flujos de frontera y condiciones iniciales.
Solver: problema discretizado + configuración -> resultado con estado de terminación,
balances acumulados, tolerancias, malla y diagnósticos; fallos no producen resultados exitosos.
Calibration: datos con incertidumbre y límites de detección, priors y parámetros
transformados; `fit` no equivale a validación externa.
Optimization: cada objetivo incluye unidades, dirección y tratamiento explícito de fallos;
soluciones no factibles nunca se promueven a Pareto válido.

## Datos y trazabilidad

Los esquemas iniciales usan nombres con sufijo SI (`length_m`, `flow_m3_s`, etc.).
Las fábricas `from_quantities` exigen magnitudes Pint dimensionales. El constructor
directo es una ruta SI explícita y valida rangos; rechaza bool, NaN e infinito.
Se fijan schema_version=1, modelos mediante uniones discriminadas, observaciones
inmutables y horas con zona. Un manifiesto registra UUID, commit, huellas SHA-256,
versiones y semilla. La serialización canónica produce huellas independientes del
orden de claves. La huella de configuración debe excluir UUID y fecha si se desea
comparar configuraciones; el manifiesto completo identifica una ejecución concreta.
El manifiesto inicial es un contrato manual: todavía no captura el entorno automáticamente.

Futuros resultados: configuración normalizada, datos originales referenciados por
hash, arrays con dimensiones y unidades, logs, revisión Git, entorno bloqueado,
algoritmos y criterios de parada. Guardar interrupciones y semillas por trabajador.
No versionar datos experimentales privados ni resultados voluminosos en el paquete.

## FAST opcional y propiedad intelectual

Un adaptador futuro aceptará una instalación aportada por el usuario, validará versión,
licencia y contrato de archivos, trabajará en un directorio temporal propio y no tocará
simulaciones existentes. No se distribuyen binarios ni ayuda FAST. Sin especificación
documentada de I/O ni autorización compatible, el adaptador queda sin implementar.
Comparar contra FAST será una prueba de compatibilidad, nunca la única validación.

Propuesta de core BSD-3-Clause sujeta a aprobación del titular; no se atribuye ni concede
una licencia sin esa decisión. Componentes comerciales en repositorios y distribuciones
separados, conectados por contratos públicos. Los derechos sobre datos se controlan aparte.

## Calidad y distribución

CI propuesta: Linux/Windows, Python 3.11–3.13; pytest, cobertura, Ruff, mypy,
construcción e instalación aislada de wheel y sdist. Solo la ejecución local 3.11
puede darse por verificada hoy. Sin publicación automática ni credenciales.
Nombre de distribución provisional `pyfast-adsorption`; import `pyfast`.
Disponibilidad en PyPI y posibles marcas pendientes; no afirmar reserva del nombre.

Dependencia runtime inicial: Pint. Desarrollo: pytest, pytest-cov, Ruff, mypy,
build y setuptools. NumPy/SciPy se incorporarán al iniciar solver; optimización y UQ
como extras después de revisar sus licencias, mantenimiento y necesidad científica.
Rangos en pyproject para instalación; snapshot exacto del entorno para reproducibilidad local.

Referencias técnicas: [Pint](https://pint.readthedocs.io/en/stable/getting/tutorial.html),
[integración SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html),
[empaquetado](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).

# SorbFlow

**SorbFlow (antes PyFAST)** es una herramienta en Python para modelar, simular,
calibrar y diseñar procesos de adsorción en fase acuosa, en reactores batch y en
columnas de lecho fijo. Versión actual: **0.3.0.dev0**.

- **Equilibrio**: isotermas lineal, Langmuir y Freundlich, con derivadas analíticas.
- **Cinética y transporte**: LDF y difusión superficial homogénea (HSDM) con película,
  dispersión axial y condiciones de Danckwerts, intercambiables desde la configuración.
- **Calibración e incertidumbre**: ajuste de isotermas y constantes cinéticas,
  diagnósticos SVD, perfiles de verosimilitud, objetivos multiensayo, Monte Carlo
  con semilla y sensibilidad local.
- **Diseño**: EBCT, pérdida de carga de Ergun, potencia, costo de operación,
  envolvente DXF y optimización multiobjetivo NSGA-II con restricciones.
- **Trazabilidad**: cada resultado guarda configuración, unidades, versiones,
  revisión del código, balance de masa y huellas SHA-256.
- **Tres formas de uso** sobre el mismo motor: API Python, comando `sorbflow` e
  interfaz web local.

## Una herramienta general

- **Cualquier especie y adsorbente**: contaminantes, materiales y recetas son datos
  de configuración, no código. Sirve para colorantes, metales, compuestos orgánicos u
  otros solutos con los parámetros de cada sistema.
- **Mezclas de N componentes** con fracciones de masa seca (`AdsorbentBlend`); sus
  propiedades se ajustan a los datos de la receta, sin promedios implícitos.
- **Unidades seguras**: entradas con unidades (mg/L, min, cm, g…) convertidas a SI de
  forma explícita, con base seca y velocidad superficial/intersticial diferenciadas.
- **Control numérico completo**: celdas axiales y radiales, BDF o Radau, tolerancias,
  instantes de salida, Jacobiano analítico y modo streaming.

Configuración física actual: un soluto en solución acuosa, temperatura de operación
definida por el usuario, partículas esféricas, lecho cilíndrico y caudal y
alimentación especificados. Las ampliaciones están en la [hoja de ruta](#hoja-de-ruta).

## Rendimiento medido

| Capacidad | Resultado |
|---|---|
| Jacobiano analítico (columna LDF, 620 celdas) | 7,77 s frente a 17,09 s: **2,2 veces más rápido** |
| Modo streaming | 956,7 MB frente a 1.632,9 MB de memoria privada, curva de salida idéntica |
| Alta resolución | 7.440 celdas y 4.767 instantes de salida en ≤262,4 s |
| Calidad | 585 pruebas automatizadas; CI en Windows y Linux con Python 3.11–3.13 |

Detalle y evidencia en [benchmarks ejecutados](docs/benchmark_results.md),
[Jacobiano analítico](docs/analytic_jacobian.md) e
[integración en streaming](docs/streaming_integration.md).

## Instalación

Python 3.11 o superior. Desde la raíz del repositorio:

```powershell
python -m pip install .                          # núcleo
python -m pip install ".[optimize,parquet]"      # NSGA-II y Parquet
python -m pip install -e ".[dev,optimize,parquet]"   # desarrollo
sorbflow --help
```

En la estación de trabajo de este proyecto, usar `.venv\Scripts\python.exe` (el
`python` global es 3.7). La figura de `examples/scientific_demo.py` usa matplotlib,
instalado con el extra `optimize`.

## Primeros pasos

```powershell
sorbflow batch  examples/batch_ldf.json   --output runs/primer_batch
sorbflow column examples/column_ldf.json  --output runs/columna --cells 100 --method BDF
sorbflow column examples/column_hsdm.json --output runs/hsdm --cells 40 --radial-cells 12
python -m sorbflow.web --output runs/gui      # interfaz local (o INICIAR_GUI.cmd)
python examples/run_ldf.py --output runs/mi_columna
python examples/robust_column_design.py --output runs/diseno
```

Cada ejecución crea una carpeta nueva con `result.json`, `timeseries.csv` y
`files.sha256.json`. `examples/configuration.py` muestra cómo generar configuraciones.

```python
from sorbflow.simulate import batch, column
from sorbflow.fit import isotherm, batch_rate
from sorbflow.uncertainty import monte_carlo, local_sensitivity
from sorbflow.optimize import nsga2, Evaluation
from sorbflow.design import hydraulics, cost_estimate, export_dxf
from sorbflow.validate import mass_balance
from sorbflow.io import export_result, export_parquet, load_breakthrough_csv
```

La [documentación funcional](docs/index.md) reúne primeros pasos, tutoriales,
preparación de datos, la [interfaz local](docs/web_interface.md), la API
([API_REFERENCE.md](API_REFERENCE.md)) y la formulación
([MODEL_SPECIFICATION.md](MODEL_SPECIFICATION.md)). La calibración avanzada incluye
[perfiles gaussianos](docs/profile_likelihood.md), un
[objetivo batch compartido](docs/batch_objective.md) y un
[ejemplo completo](docs/profile_batch_example.md).

## Verificación y calidad

- [E01-A](benchmarks/e01/README.md): 219 criterios en 40 integraciones frente a
  referencias analíticas; [E01-B](benchmarks/e01b/README.md): 138 criterios frente a
  una solución continua de advección–dispersión; suplemento E01: 29 casos y 148
  criterios. Todos aprobados, con protocolos fijados antes de ejecutar.
- E02: 3.000 conjuntos sintéticos y 6.000 perfiles de verosimilitud completos.
- E03: diseño robusto con 0 incumplimientos en 40 escenarios independientes.
- E04: calibración de columna con datos publicados y convergencia local.

```powershell
python scripts/project_checks.py --output runs/control_nuevo
python -m pytest --cov=sorbflow --cov-report=term-missing --cov-fail-under=90
python -m ruff check .
python -m mypy
python -m build
```

Estado completo de los estudios en [estado científico](docs/scientific_status.md).

## Hoja de ruta

Sistemas multicomponente, efectos térmicos, alimentación variable en el tiempo,
incertidumbre con discrepancia de modelo, exportación CAD/STEP y adaptadores de
interoperabilidad. Etapas y criterios en DEVELOPMENT_ROADMAP.md.

## Documentos de diseño

- ARCHITECTURE.md, MODEL_SPECIFICATION.md e IMPLEMENTATION_NOTES.md: contratos y ecuaciones.
- VALIDATION_PLAN.md y NUMERICAL_VERIFICATION.md: plan y evidencia de verificación.
- IP_LICENSE_AUDIT.md y RELATED_WORK.md: derechos, dependencias y antecedentes.
- PAPER_ENVSOFT: objetivo editorial (Environmental Modelling & Software), hipótesis,
  experimentos E01–E05 y reproducibilidad. Reproducción rápida:
  `python PAPER_ENVSOFT/reproduce_smoke.py --output runs/paper_smoke --jobs 2`.
- [Inventario técnico](REGISTRATION_PREPARATION/README.md) para la revisión de derechos.

## Licencia y distribución

Licencia en definición: `LicenseRef-Proprietary` hasta que el titular confirme la
licencia de publicación (se propone Apache-2.0 para el núcleo). SorbFlow es un
desarrollo independiente: no incluye código, ejecutables ni recursos de otros
programas de adsorción, incluido FAST. NSGA-II usa el extra opcional pymoo
(Apache-2.0), que incorpora moocore (LGPL). No publicado aún en PyPI.

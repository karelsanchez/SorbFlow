# PyFAST

Prototipo científico **0.2.0.dev0** para adsorción acuosa: equilibrio, simulación
batch LDF y columna LDF/HSDM, ajuste inverso inicial, incertidumbre, sensibilidad,
optimización multiobjetivo opcional e hidráulica con exportación DXF de proceso.
**Tiene verificaciones numéricas seleccionadas; no tiene validación experimental.**

Materiales, biocarbones, contaminantes y recetas son configurables. No se limita a
cuatro materias primas ni al azul de metileno. Las mezclas son datos de preparación:
sus propiedades deben medirse/ajustarse, no se promedian automáticamente.
El dominio actual es una especie, un tamaño de partícula, temperatura fija,
caudal/entrada constantes y columna cilíndrica uniforme.

## Instalación y ejemplo

Python >=3.11. En este equipo usar el Python del entorno local: el `python` global
es 3.7 y el launcher `py` selecciona 2.7. Desde `D:\PyFAST`:

```powershell
& .\.venv\Scripts\python.exe -m pip install -e '.[dev,optimize]'
& .\.venv\Scripts\python.exe examples\run_ldf.py --output D:\PyFAST\runs\mi_columna
& .\.venv\Scripts\python.exe examples\scientific_demo.py --output D:\PyFAST\runs\demo
& .\.venv\Scripts\python.exe examples\robust_column_design.py --output D:\PyFAST\runs\diseno
```

Las carpetas de resultados deben ser nuevas. El entorno ya contiene las dependencias.
En una instalación nueva basta `pip install .`; `[parquet]` añade PyArrow; `[optimize]` añade pymoo y sus
dependencias, `[dev]` añade herramientas de desarrollo. La figura del ejemplo
científico usa matplotlib, disponible también como dependencia de pymoo.

## API

```python
from pyfast.simulate import batch, column
from pyfast.fit import isotherm, batch_rate
from pyfast.uncertainty import monte_carlo, local_sensitivity
from pyfast.optimize import nsga2, Evaluation
from pyfast.design import hydraulics, cost_estimate, export_dxf
from pyfast.validate import mass_balance
from pyfast.io import export_result, export_parquet, load_breakthrough_csv
```

Las configuraciones tipadas usan SI y base seca. `quantity`/`to_si` convierten
entradas dimensionales; resultados contienen perfiles, unidades, balance, opciones,
huellas y versiones. JSON preserva los campos completos; CSV y Parquet opcional contienen la serie
de salida y masa acumulada. DXF contiene únicamente la envolvente de proceso,
no un plano de fabricación. CLI para simulaciones:

```powershell
& .\.venv\Scripts\python.exe -m pyfast column configuracion.json --output runs\caso --cells 100 --radial-cells 20 --method BDF
```

`examples/configuration.py` muestra cómo generar JSON. `SimulationConfig` selecciona
LDF o HSDM por el contrato cinético; no invoca FAST. API detallada en API_REFERENCE.md.

## Calidad y evidencia

```powershell
& .\.venv\Scripts\python.exe -m pytest --cov=pyfast --cov-report=term-missing --cov-fail-under=90
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m mypy
& .\.venv\Scripts\python.exe -m build
```

Referencias analíticas: batch lineal, transporte FV equivalente a cadena de tanques,
frente de trazador y difusión esférica. También hay conservación, refinamiento,
comparación BDF/Radau, recuperación sintética y pruebas de UQ/NSGA-II. No sustituyen
campaña experimental, perfiles de likelihood ni barrido exhaustivo de estabilidad.
La matriz CI propuesta requiere ejecutarse en un remoto.

## Diseño y límites

- ARCHITECTURE.md, MODEL_SPECIFICATION.md y IMPLEMENTATION_NOTES.md: contratos y ecuaciones.
- VALIDATION_PLAN.md y NUMERICAL_VERIFICATION.md: evidencia y pruebas aún pendientes.
- DEVELOPMENT_ROADMAP.md: etapas y criterios de aceptación.
- IP_LICENSE_AUDIT.md y RELATED_WORK.md: derechos, dependencias y antecedentes.
- AUDIT_REPORT.md: auditoría histórica de FAST y fundación 0.1.

Pendientes: validación experimental, identificabilidad global/perfiles, modelos
multicomponente/térmicos y entradas variables, UQ con discrepancia de modelo,
convergencia de diseño robusto, interfaz web y adaptador STEP/CAD avanzado.
FAST externo permanece sin integrar; el ZIP original está intacto.

## Licencia y distribución

Open Core propuesto: núcleo científico Apache-2.0 y componentes comerciales en
distribución independiente. La titularidad universitaria y la concesión definitiva
están pendientes; LICENSE.md y `LicenseRef-Proprietary` no afirman una licencia abierta
aún no otorgada. NSGA-II es extra opcional: pymoo Apache-2.0 incorpora moocore LGPL,
con obligaciones propias que deben revisarse para redistribución. No se incluyen
binarios FAST ni wheels de terceros. No se ha publicado en PyPI; el nombre es provisional.

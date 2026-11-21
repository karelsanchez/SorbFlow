# Tutoriales funcionales

[Inicio](index.md) · [API](../API_REFERENCE.md) · [Unidades](data_preparation.md)

Ejecutar desde el checkout, con el entorno activo. Los ejemplos utilizan datos
sintéticos; el material y la especie se suministran como configuración.

## 1. Unidades y equilibrio

```python
from sorbflow import Langmuir, quantity, to_si

c = to_si(quantity(100, "mg/L"), "kg/m^3")
model = Langmuir(qmax_kg_kg=0.01, affinity_m3_kg=10)
```

`c` vale 0,1 kg/m³. La afinidad debe corresponder a esa base de concentración.
Los parámetros anteriores solo ilustran la construcción del modelo.

## 2. Primer batch con trazabilidad

```python
from pathlib import Path
from sorbflow import BatchConfig
from sorbflow.simulate import batch
from sorbflow.io import export_result
from sorbflow.validate import mass_balance

config = BatchConfig.from_json(Path("examples/batch_ldf.json").read_text())
result = batch(config)
assert mass_balance(result).passed
export_result(result, Path("runs/tutorial_batch"))
```

La carpeta de salida debe ser nueva. Los archivos exportados conservan la
configuración, los resultados y el balance de masa, de modo que cada simulación
puede reproducirse y auditarse.

## 3. Columna LDF con memoria reducida

```python
from pathlib import Path
from sorbflow import SimulationConfig
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions

config = SimulationConfig.from_json(Path("examples/column_ldf.json").read_text())
options = SolverOptions(axial_cells=40, history="streaming", jacobian="analytic")
result = column(config, options=options)
```

La malla de 40 celdas es un ejemplo, no una recomendación universal. Antes de
usar indicadores o decidir factibilidad se comparan mallas y tolerancias.
El [Jacobiano analítico](analytic_jacobian.md) y el modo
[streaming](streaming_integration.md) documentan modelos compatibles.

## 4. Columna HSDM mediante CLI

```powershell
python -m sorbflow column examples/column_hsdm.json --output runs/tutorial_hsdm --cells 20 --radial-cells 8
```

HSDM agrega difusión radial y película. Sus coeficientes no se obtienen
automáticamente de una constante LDF. Consulte la
[formulación y las condiciones de frontera](../MODEL_SPECIFICATION.md).

## 5. Ajuste, incertidumbre y diseño

- [Objetivo batch compartido](batch_objective.md): varios ensayos y contador de solves.
- [Perfiles gaussianos](profile_likelihood.md) y [ejemplo](profile_batch_example.md):
  sigma conocida, intentos fallidos, límites y diagnóstico de baseline.
- [Ejemplo de diseño robusto](../examples/robust_column_design.py): requiere el
  extra `optimize`; las distribuciones del ejemplo son supuestas.
- [Benchmarks](benchmark_results.md): resultados, protocolos y límites observados.

La función objetivo y sus restricciones deben reflejar el problema de diseño.
No sustituya incertidumbre experimental desconocida por un sigma inventado.

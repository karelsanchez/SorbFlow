# SorbFlow

**SorbFlow** es una herramienta en Python para modelar, simular, calibrar y diseñar
procesos de adsorción en fase acuosa, en reactores batch y en columnas de lecho fijo.

```bash
pip install sorbflow                 # núcleo
pip install "sorbflow[optimize]"     # + optimización multiobjetivo NSGA-II
pip install "sorbflow[parquet]"      # + exportación Parquet
```

## Qué hace

- **Equilibrio**: isotermas lineal, Langmuir y Freundlich, con derivadas analíticas.
- **Cinética y transporte**: fuerza impulsora lineal (LDF) y difusión superficial
  homogénea (HSDM) con resistencia de película, dispersión axial y condiciones de
  frontera de Danckwerts.
- **Motores numéricos**: volúmenes finitos conservativos en el eje del lecho y en el
  radio de la partícula, integradores rígidos BDF/Radau, Jacobiano analítico disperso
  y modo *streaming* de baja memoria.
- **Calibración e incertidumbre**: ajuste de isotermas y constantes cinéticas,
  diagnósticos SVD, perfiles de verosimilitud, objetivos multiensayo, Monte Carlo
  con semilla y sensibilidad local.
- **Diseño**: EBCT, pérdida de carga de Ergun, potencia de bombeo, costo de operación,
  envolvente DXF y optimización multiobjetivo con restricciones.
- **Trazabilidad**: cada resultado guarda configuración, unidades, versiones, revisión
  del código, balance de masa y huellas SHA-256.
- **Tres formas de uso** sobre el mismo motor: API Python, comando `sorbflow` e
  interfaz web local (`python -m sorbflow.web`).

Cualquier soluto, adsorbente o mezcla de N componentes se describe como datos de
configuración, con unidades SI explícitas.

## Uso rápido

```bash
sorbflow column column_ldf.json --output resultados --cells 100
```

```python
from pathlib import Path
from sorbflow import SimulationConfig
from sorbflow.simulate import column
from sorbflow.solvers import SolverOptions

config = SimulationConfig.from_json(Path("column_ldf.json").read_text())
result = column(config, options=SolverOptions(axial_cells=200, jacobian="analytic"))
print(result.outlet_concentration_kg_m3[-1])
```

Las configuraciones de ejemplo (`batch_ldf.json`, `column_ldf.json`,
`column_hsdm.json`) están en la carpeta `examples/` del repositorio.

## Modelo de columna (resumen)

```text
ε ∂c/∂t + ρ_b ∂q̄/∂t = −∂J/∂z,     J = u c − ε D_ax ∂c/∂z
LDF:   ∂q̄/∂t = k_LDF [q*(c) − q̄]
HSDM:  ∂q/∂t = D_s r⁻² ∂/∂r (r² ∂q/∂r),   ρ_p D_s ∂q/∂r|_R = k_f (c − c_s)
```

## Calidad

588 pruebas automatizadas; integración continua en Windows y Linux con Python 3.11,
3.12 y 3.13; verificación frente a soluciones de referencia; documentación construida
en modo estricto.

## Documentación, cita y licencia

- Documentación: https://sorbflow.readthedocs.io
- Autores: Karel Aldrin Sanchez Hernandez, David Esteban Rodriguez Saiz,
  Dayana Ximena Cabrera Obando y Gabriela Johana Romo Cadena.
- Cita: archivo `CITATION.cff` del repositorio.
- Licencia: Apache-2.0.

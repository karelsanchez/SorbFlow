# S2: parche propuesto para `axial_scheme="tvd"` en columnas HSDM

Estado: **no aplicado**. `src/sorbflow/reactors/hsdm.py` lo edita otra persona en
paralelo, así que el balance axial HSDM sigue con `upwind1`. Mientras tanto
`simulate_column` rechaza `HSDM + axial_scheme="tvd"` con `ValueError` (no hay
fallback silencioso). Atención: una llamada directa a `simulate_hsdm_column`
con `axial_scheme="tvd"` **no** está protegida hasta aplicar este parche.

El balance líquido axial de HSDM es idéntico al de LDF (mismos flujos de cara,
mismas fronteras, mismos estados de masa acumulada); solo cambia el término de
transferencia. Toda la lógica del esquema vive en
`sorbflow.reactors.column.AxialTransport`, por lo que el parche es mecánico.

## 1. Importaciones (`hsdm.py`)

```python
from .column import AxialTransport
```

`column.py` importa `hsdm` de forma diferida dentro de `simulate_column`, así
que esta importación a nivel de módulo no crea un ciclo.

## 2. Patrón de dispersión `_pattern(axial, radial)`

Añadir el argumento `scheme` y ensanchar el bloque líquido-líquido y la fila de
masa de salida:

```python
def _pattern(axial: int, radial: int, scheme: str = "upwind1") -> csc_matrix:
    lower = 1 if scheme == "upwind1" else 2          # TVD: c[i] depende de c[i-2]
    ...
    for i in range(axial):
        for j in range(max(0, i - lower), min(axial, i + 2)):
            rows.append(i); cols.append(j)
    ...
    outlet = [axial - 1] if scheme == "upwind1" else [axial - 2, axial - 1]
    rows.extend([states - 1] * len(outlet)); cols.extend(outlet)
```

## 3. Construcción del transporte (tras calcular `dz`, `velocity`, `eps`)

```python
transport = AxialTransport.from_config(config, n, settings.axial_scheme)
upwind = settings.axial_scheme == "upwind1"
```

## 4. `rhs`: sustituir el bloque `flux = np.empty(n + 1) ... flux[-1] = ...`

```python
flux = transport.face_flux(c)          # caras 0..N, incluye dispersión central
dc = (-np.diff(flux) / dz - specific_area * transfer) / eps
if upwind:   # expresiones históricas: trayectorias idénticas bit a bit
    rates = [op.flow_m3_s * op.inlet_concentration_kg_m3, op.flow_m3_s * c[-1]]
else:        # mismos flujos de cara que las celdas: conservación exacta
    rates = [area * flux[0], area * flux[n]]
return np.concatenate((dc, dq.ravel(), rates))
```

Para `upwind1`, `face_flux` reproduce literalmente
`velocity*c[:-1] - eps*D*np.diff(c)/dz` (verificado en
`tests/test_axial_scheme.py::test_upwind1_default_matches_historical_face_fluxes`).

## 5. Integración

```python
solution = integrate(rhs, initial, times, atol, settings,
                     _pattern(n, nr, settings.axial_scheme))
```

## 6. Retirar la guarda en `column.py`

Eliminar en `simulate_column` el bloque
`if settings.axial_scheme != "upwind1": raise ValueError(...)` de la rama HSDM.

## 7. Pruebas a añadir (`tests/test_hsdm.py`)

- Masa: `max_scaled_mass_residual < 1e-8` con `axial_scheme="tvd"`.
- Trazador HSDM con difusividad despreciable frente a LDF trazador, ambos
  `tvd`: deben coincidir como hoy en `test_uniform_equilibrium_column_and_hsdm_tracer`.
- No negatividad y ausencia de extremos nuevos en un frente escalón.
- `effluent_concentration(result)` ya acepta resultados HSDM (lee
  `axial_scheme` de `options_json`); no requiere cambios.

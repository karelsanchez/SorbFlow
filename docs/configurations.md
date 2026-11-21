# Configuraciones disponibles

Todo caso se describe con objetos tipados (o su JSON equivalente, `schema_version: 1`).
Los campos usan SI y su unidad forma parte del nombre. Las fábricas
`Bed.from_quantities` y `Operation.from_quantities` aceptan magnitudes con unidades
y las convierten. Plantillas listas: `examples/batch_ldf.json`,
`examples/column_ldf.json` y `examples/column_hsdm.json`.

## Especie y material

| Objeto | Campos |
|---|---|
| `Species` | `name`, `molar_mass_kg_mol` (opcional) |
| `BlendComponent` | `material_id`, `dry_mass_fraction` |
| `AdsorbentBlend` | `name`, `components` (N componentes; fracciones positivas que suman 1) |

## Equilibrio (`equilibrium`)

| `kind` | Objeto | Parámetros | Expresión |
|---|---|---|---|
| `linear` | `Linear` | `distribution_m3_kg` | q* = K c |
| `langmuir` | `Langmuir` | `qmax_kg_kg`, `affinity_m3_kg` | q* = q_max b c / (1 + b c) |
| `freundlich` | `Freundlich` | `q_ref_kg_kg`, `c_ref_kg_m3`, `exponent` | q* = q_ref (c / c_ref)^n |

## Cinética (`kinetics`)

| `kind` | Objeto | Parámetros | Uso |
|---|---|---|---|
| `ldf` | `LDF` | `rate_s_inv` | Resistencia global de transferencia; batch y columna |
| `hsdm` | `HSDM` | `surface_diffusivity_m2_s`, `film_coefficient_m_s` | Difusión radial en la partícula con película; columna con perfiles radiales |

## Columna (`SimulationConfig`)

| Bloque | Campos |
|---|---|
| `bed` (`Bed`) | `length_m`, `diameter_m`, `particle_diameter_m`, `porosity`, `particle_density_kg_m3`, `material`, `mass_basis` (`dry`) |
| `operation` (`Operation`) | `flow_m3_s`, `inlet_concentration_kg_m3`, `duration_s`, `temperature_k` (298,15), `axial_dispersion_m2_s` (0), `initial_concentration_kg_m3` (0), `initial_loading_kg_kg` (0) |
| Modelo | `species`, `equilibrium`, `kinetics` |

## Batch (`BatchConfig`)

`species`, `material`, `liquid_volume_m3`, `adsorbent_mass_kg`, `duration_s`,
`initial_concentration_kg_m3`, `initial_loading_kg_kg`, `equilibrium`, `kinetics`
(LDF), `temperature_k` (298,15).

## Opciones numéricas (`SolverOptions`)

| Opción | Valor por defecto | Descripción |
|---|---|---|
| `method` | `BDF` | Integrador rígido `BDF` o `Radau` |
| `rtol` | 1e-7 | Tolerancia relativa |
| `atol_concentration_kg_m3` | 1e-10 | Tolerancia absoluta de concentración |
| `atol_loading_kg_kg` | 1e-12 | Tolerancia absoluta de carga |
| `atol_mass_kg` | 1e-12 | Tolerancia absoluta de masas acumuladas |
| `mass_rtol`, `mass_reference_kg` | 1e-6, 1e-12 | Criterio del balance de masa |
| `max_step_s` | sin límite | Paso máximo del integrador |
| `axial_cells` | 100 | Celdas axiales |
| `radial_cells` | 20 | Celdas radiales (HSDM) |
| `jacobian` | `finite_difference` | `analytic`: Jacobiano exacto para columna LDF con isoterma Langmuir o lineal |
| `history` | `dense` | `streaming`: historia por pasos con menor memoria en columna LDF |

Los instantes de salida se pasan como `time_s` (por defecto, 201 puntos entre 0 y la
duración). Desde la terminal, las mismas opciones están disponibles como
`--method`, `--cells`, `--radial-cells`, `--samples`, `--rtol` y `--code-revision`.

## Combinaciones recomendadas

| Objetivo | Configuración |
|---|---|
| Exploración rápida | LDF, 40–100 celdas, BDF |
| Columna de alta resolución | LDF Langmuir/lineal, `jacobian="analytic"`, `history="streaming"` |
| Perfiles dentro de la partícula | HSDM con 10–20 celdas radiales |
| Comprobación de malla | Repetir con 2N celdas y comparar el indicador de diseño |

Véanse también [rendimiento](performance.md), [Jacobiano analítico](analytic_jacobian.md)
e [integración en streaming](streaming_integration.md).

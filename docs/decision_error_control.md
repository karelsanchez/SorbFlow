# Control del error numérico orientado a decisiones

Los códigos de columnas suelen informar curvas de ruptura, no el error de
discretización de las magnitudes con las que se diseña. El paquete
`sorbflow.verification` estima ese error directamente para las **magnitudes de
decisión** (tiempo de ruptura, volúmenes de lecho, capacidad útil, efluente a un
tiempo de servicio), refina la malla hasta una tolerancia declarada y clasifica
restricciones de diseño como `SATISFIED`, `VIOLATED` o `UNDETERMINED`.

Solo se usa la API pública: `sorbflow.simulate.column` con copias de
`SolverOptions` cuyo `axial_cells` (y `radial_cells` en HSDM) siguen una
secuencia geométrica. No se modifica ningún reactor.

## Magnitudes de decisión

Sea `R(t) = C_eff(t)/C_in` la razón de efluente muestreada en los tiempos
solicitados `t_0 = 0 < t_1 < … < t_M = duration_s` (por defecto 2001 puntos
uniformes). `C_eff` es la concentración en la cara de salida: la última celda en
el esquema `upwind1` (y en HSDM) y la reconstrucción limitada en `z = L` con
`axial_scheme="tvd"`.

| Clase | Clave | Definición | Unidades |
|---|---|---|---|
| `BreakthroughTime(fraction=x)` | `t_x_s` | primer `t` con `R(t) = x` | s |
| `BedVolumesAt(fraction=x)` | `bv_x` | `BV_x = Q t_x / V_lecho` | BV |
| `UsefulCapacity(fraction=x)` | `capacity_x_kg_kg` | `(M_in(t_x) − M_out(t_x)) / (ρ_b V_lecho)` | kg/kg |
| `EffluentAt(service_time_s=t_s)` | `c_out_at_<t_s>s_kg_m3` | `C_eff(t_s)` | kg/m³ |
| `ExceedanceTime(limit_kg_m3=C_lim)` | `t_exceed_<C_lim>kg_m3_s` | primer `t` con `C_eff(t) = C_lim` | s |

`M_in` y `M_out` son las masas acumuladas integradas por el propio
integrador (flujos de frontera), no una cuadratura posterior.

**Interpolación (consistente en todas las mallas).** Por defecto se usa el
interpolante cúbico de Hermite monótono (PCHIP, Fritsch–Carlson): reproduce las
muestras, no oscila entre ellas y es de tercer orden en datos suaves. El cruce
se localiza en el primer intervalo `[t_{k−1}, t_k]` con `R(t_{k−1}) < x ≤ R(t_k)`
y se resuelve con `brentq` sobre el segmento cúbico. `interpolation="linear"`
ofrece la alternativa lineal (la clave recibe el sufijo `_linear`). Como la misma
regla y la misma rejilla temporal se usan en todas las mallas, las diferencias
entre mallas miden la discretización espacial; el error de interpolación
temporal debe ser pequeño frente a la tolerancia (rejilla temporal densa,
`rtol` del integrador estricto, p. ej. `1e-8`).

**Censura explícita.** Si el evento no ocurre dentro del horizonte, el valor es
`None`, `censoring="right"` y `bound` contiene la magnitud evaluada en
`duration_s` (el valor exacto es mayor). Si ya ocurre en la primera muestra,
`censoring="left"`. Nunca se devuelve NaN ni se sustituye por el horizonte.

## Métodos

Mallas `h_1 < h_2 < h_3` (1 = la más fina, `h = L/N_axial`), razones
`r_21 = h_2/h_1`, `r_32 = h_3/h_2`, diferencias `ε_21 = φ_2 − φ_1`,
`ε_32 = φ_3 − φ_2`, `s = sign(ε_32/ε_21)`.

**Orden observado** (Roache 1998; Celik et al. 2008):

$$
p = \frac{1}{\ln r_{21}}\left[\ln\left|\frac{\varepsilon_{32}}{\varepsilon_{21}}\right|
 + \ln\frac{r_{21}^{p}-s}{r_{32}^{p}-s}\right],
\qquad p = \frac{\ln(\varepsilon_{32}/\varepsilon_{21})}{\ln r}\ \text{si } r_{21}=r_{32}=r .
$$

**Extrapolación de Richardson:**

$$
\varphi_{\text{ext}} = \varphi_1 + \frac{\varphi_1-\varphi_2}{r_{21}^{p}-1}.
$$

**Índice de convergencia de malla (GCI, Roache 1994):**

$$
\mathrm{GCI} = \frac{F_s\,|\varphi_1-\varphi_2|}{r_{21}^{p}-1},\qquad
F_s = 1.25\ (\ge 3\ \text{mallas}),\quad F_s = 3\ (2\ \text{mallas}, p = p_{\text{formal}}).
$$

Con tres o más mallas se usa `p = min(p_obs, p_formal)` (más conservador si la
secuencia aparenta superconvergencia). El orden formal es 1 para `upwind1`, 2
para `tvd`. La banda `φ_1 ± GCI` acota el error de la solución más fina y
contiene `φ_ext` porque `F_s ≥ 1`.

**Comportamiento no asintótico.** Se marca (`flags`) y se aplica la cota
conservadora `U = 3·max(|ε_21|, |ε_32|/r_32^{p_formal})`, sin extrapolar
(`φ_ext = φ_1`), cuando la secuencia es oscilatoria (`s < 0`), divergente
(`|ε_21| ≥ |ε_32|`) o `p_obs` cae fuera de la banda plausible (por defecto
`[0.5, p_formal + 1]`). Con cuatro o más mallas se marca `order_drift` si el
orden de los dos tripletes más finos difiere más de un 25 %.

**Refinamiento adaptativo.** `converge` resuelve `N_0, rN_0, r²N_0, …` y, desde
la tercera malla, estima cada magnitud con las tres más finas. Una magnitud
está `CONVERGED` si `U ≤ max(abs_tol, rel_tol·|φ_1|)`. Se detiene cuando todas
están `CONVERGED` o `CENSORED`, o al agotar `budget_solves` o `max_cells`.
Con `U ∝ h^p`, el número de resoluciones previsto es

$$
n_{\text{pred}} = n + \max_k \left\lceil \frac{\ln(U_k/\mathrm{tol}_k)}{p_k \ln r}\right\rceil ,
$$

que se registra en `predicted_solves`.

**Clasificación de restricciones.** Para `φ ≥ θ` (o `φ ≤ θ`) se compara la banda
`[φ_1 − U, φ_1 + U]` con el umbral: `SATISFIED` si toda la banda cumple,
`VIOLATED` si toda la banda incumple y `UNDETERMINED` en otro caso. Para
`UNDETERMINED` se recomienda la malla `N' = N_1 r^k ≥ N_1 (U/|φ_1 − θ|)^{1/p}`.
Una magnitud censurada se clasifica con su cota cuando es lógicamente decisiva
(p. ej. `t_10 > duration_s ≥ θ` ⇒ `SATISFIED`); en otro caso se recomienda
ampliar `duration_s`.

## Validación

La prueba `tests/test_verification.py` implementa una referencia independiente:
solución de Thomas/Anzelius para LDF lineal en flujo pistón,

$$
\frac{C}{C_{in}} = J(\xi, k\tau),\quad
J(x,y) = 1-\int_0^x e^{-y-s} I_0\!\left(2\sqrt{ys}\right)\,ds,\quad
\xi = \frac{k\rho_b K L}{v},\ \tau = t-\frac{\varepsilon L}{v},
$$

evaluada con `scipy.integrate.quad` y `scipy.special.ive`. Con la secuencia
25/50/100 celdas (upwind, `rtol=1e-8`) el GCI acota el error verdadero de
`t_10` y `t_50` en la malla más fina en los tres regímenes ensayados:

| ξ (NTU) | magnitud | error verdadero (s) | GCI (s) | GCI/error | p_obs |
|---|---|---|---|---|---|
| 4.7 | t_10 | 1.41 | 1.88 | 1.33 | 0.93 |
| 4.7 | t_50 | 0.222 | 0.297 | 1.34 | 1.11 |
| 18.8 | t_10 | 2.98 | 4.35 | 1.46 | 0.83 |
| 18.8 | t_50 | 0.240 | 0.356 | 1.48 | 1.19 |
| 94.2 | t_10 | 6.04 | 10.2 | 1.69 | 0.65 |
| 94.2 | t_50 | 0.305 | 0.469 | 1.54 | 1.09 |

Con 100/200/400 celdas la cobertura se mantiene (GCI/error 1.27–1.51) y el
valor extrapolado reduce el error entre 5 y 60 veces.

## Uso

```python
from sorbflow.solvers import SolverOptions
from sorbflow.verification import (BreakthroughTime, Constraint, EffluentAt,
                                   classify_report, converge)

service = EffluentAt(service_time_s=1400.0)
report = converge(
    config,                                   # SimulationConfig (LDF o HSDM)
    [BreakthroughTime(fraction=0.1), BreakthroughTime(fraction=0.5), service],
    rel_tol=0.01, abs_tol={service.key: 2e-5},
    max_cells=1600, budget_solves=7,
    options=SolverOptions(axial_cells=25, rtol=1e-8),
)
for q in report.quantities:
    print(q.key, q.value, q.extrapolated, q.error_bound, q.status)
decisions = classify_report(report, [
    Constraint(quantity_key="t_0.1_s", sense=">=", threshold=1400.0),
    Constraint(quantity_key=service.key, sense="<=", threshold=1e-3),
])
open("report.json", "w").write(report.to_json())   # incluye "fingerprint"
```

`report.to_json()` es JSON canónico (sin NaN/Infinity) con valores por malla,
`p`, valor extrapolado, cota, estado, resoluciones, tiempo de CPU, versión de
SorbFlow y un `RunManifest` (con las huellas `numerical_sha256` de cada malla en
`input_sha256`). `report.fingerprint` es el SHA-256 del contenido reproducible:
excluye tiempos de CPU, identificador y fecha, como `numerical_sha256`.

El ejemplo completo está en `examples/decision_error_control.py`. Funciones de
nivel inferior: `mesh_sequence` (secuencia fija), `estimate_quantities`
(estimación pura a partir de mallas ya resueltas), `richardson_estimate` y
`observed_order` (escalares), `extract` (magnitudes de un resultado).

## Limitaciones

- La cota es una estimación asintótica (GCI), no una cota rigurosa; fuera del
  régimen asintótico se usa una cota conservadora heurística.
- Solo se controla el error espacial. El error temporal (`rtol`) y el de
  interpolación de la rejilla de salida deben ser menores que la tolerancia;
  no se estiman.
- En HSDM, `refine="both"` refina axial y radial con la misma razón; el orden
  observado es el del error combinado.
- Frentes muy abruptos (ξ grande) con mallas gruesas dan `p_obs` bajos en
  `t_x` pequeños; el método lo detecta (banda) pero puede requerir muchas celdas.

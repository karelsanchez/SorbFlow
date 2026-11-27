# Reactor batch con HSDM

[Inicio](index.md) · [Modelos y ecuaciones](models.md)

El reactor batch cerrado y perfectamente mezclado admite, además de LDF, el modelo
de difusión superficial homogénea (HSDM) con resistencia externa de película. La
discretización radial es la misma que la de la columna HSDM
(`sorbflow.kinetics.sphere`: `SphereGrid`, `diffusion_rhs`, `film_flux`).

## Ecuaciones (SI, base seca)

$$V_L\,\frac{dc}{dt} = -m_s\,\frac{d\bar q}{dt},\qquad
\frac{\partial q}{\partial t} = \frac{D_s}{r^2}\frac{\partial}{\partial r}\!\left(r^2\frac{\partial q}{\partial r}\right)$$

$$\left.\frac{\partial q}{\partial r}\right|_{0}=0,\qquad
\rho_p D_s \left.\frac{\partial q}{\partial r}\right|_{R} = k_f\,(c-c_s),\qquad
q(R)=q^*(c_s),\qquad \bar q = \frac{3}{R^3}\int_0^R q\,r^2\,dr$$

con $R=d_p/2$. La masa $V_L c + m_s \bar q$ se conserva. El líquido de poro de la
partícula no se modela (hipótesis HSDM); hay una sola clase de tamaño, $T$ fija y
un único soluto. Como en el batch LDF no hay corrientes de entrada/salida: los
estados acumulados de masa (`inlet_mass_kg`, `outlet_mass_kg`) son cero y el
residuo es `inventory_kg - inventory_kg[0]`.

## Configuración: esquema batch v2

`BatchConfig` acepta `schema_version` 1 o 2.

- **v1** (sin cambios): solo LDF, sin campo `particle`. El JSON canónico, el
  `sha256` y la huella numérica de las configuraciones v1 existentes no cambian.
- **v2**: añade `particle` (siempre serializado; `null` permitido con LDF, que lo
  ignora) y el tipo de cinética `hsdm`. HSDM **exige** `particle`:

```python
from sorbflow import HSDM, BatchConfig, Freundlich, Species
from sorbflow.schemas import BatchParticle
from sorbflow.simulate import batch
from sorbflow.solvers import SolverOptions

config = BatchConfig(
    species=Species(name="soluto-sintetico"),
    material="adsorbente-sintetico",
    liquid_volume_m3=1e-3, adsorbent_mass_kg=2e-3, duration_s=36000,
    initial_concentration_kg_m3=0.01, initial_loading_kg_kg=0,
    equilibrium=Freundlich(q_ref_kg_kg=0.01, c_ref_kg_m3=0.01, exponent=0.43),
    kinetics=HSDM(surface_diffusivity_m2_s=1e-12, film_coefficient_m_s=1e-5),
    particle=BatchParticle(diameter_m=5e-4, density_kg_m3=1000),
    schema_version=2,
)
result = batch(config, options=SolverOptions(radial_cells=20))
result.radial_loading_kg_kg   # (tiempo, 1, celdas radiales), kg/kg seco
result.r_m                    # centros de las capas, m
result.loading_kg_kg          # media volumétrica q̄, (tiempo, 1)
```

`BatchParticle.density_kg_m3` es la densidad aparente de partícula en base seca
(misma convención que `Bed.particle_density_kg_m3`). Se necesita además del
diámetro porque fija el área externa por kg de adsorbente, $6/(\rho_p d_p)$.
Errores explícitos: HSDM sin `particle`; `particle` o HSDM con
`schema_version=1`; campos desconocidos; clave `particle` ausente en un JSON v2 o
presente en uno v1. Ejemplo sintético: [`examples/batch_hsdm.json`](../examples/batch_hsdm.json)
(`sorbflow batch examples/batch_hsdm.json --output <dir> --radial-cells 20`).

## Numérica

Estados: $c$ y las cargas de las `radial_cells` capas (con `radial_growth` de las
opciones si existe, como en la columna). La fuente del líquido es
$-(m_s/V_L)\sum_r w_r\,\dot q_r$, de modo que el inventario es un invariante lineal
exacto del lado derecho discreto. BDF/Radau lo preservan solo si la matriz de
iteración también lo hace, por eso el jacobiano (opción por defecto
`jacobian="finite_difference"`) se ensambla con esa estructura: bloque de difusión
lineal exacto, las dos derivadas parciales del flujo de película por diferencias
centradas de la solución escalar de película, y la fila del líquido como
$-(m_s/V_L)$ por la suma ponderada de las filas de las capas. Con el jacobiano
por diferencias de SciPy columna a columna la deriva era ~5e-9 (escalada) con las
tolerancias por defecto; con el estructurado es ~1e-15. `jacobian="analytic"` e
`history="streaming"` se rechazan con `ValueError`.

## Verificación (`tests/test_batch_hsdm.py`)

1. **Lineal, película despreciable** ($Bi=k_fR/(\rho_pK D_s)=5\times10^8$, $\alpha=V_L/(m_sK)=1$)
   frente a Crank (1975), *The Mathematics of Diffusion*, ec. 6.30, implementada en
   el test (raíces de $\tan q_n = 3q_n/(3+\alpha q_n^2)$ en $(n\pi, n\pi+\pi/2)$,
   4000 términos) con autocomprobaciones (ecuación de raíces, $\alpha\to\infty$ ⇒
   serie de baño infinito, límite de tiempos cortos $6\sqrt{\tau/\pi}(1+\alpha)/\alpha$).
   Error máximo en $M_t/M_\infty$ ($\tau=D_st/R^2\le0.5$, rtol 1e-10):

   | capas | máx. (todas, desde τ=0.005) | orden | máx. (τ ≥ 0.05) | orden |
   |---|---|---|---|---|
   | 10 | 3.65e-2 | – | 1.88e-4 | – |
   | 20 | 5.83e-3 | 2.65 | 4.88e-5 | 1.95 |
   | 40 | 1.35e-3 | 2.11 | 1.23e-5 | 1.99 |
   | 80 | 3.31e-4 | 2.02 | 3.09e-6 | 2.00 |
   | 160 | 8.25e-5 | 2.01 | 7.74e-7 | 2.00 |

   Orden observado ≈ 2 (160 capas: estudio fuera de la suite).
2. **Conservación**: residuo de masa escalado ≤ 2e-15 en todos los casos
   ensayados (lineal, Freundlich, Langmuir; BDF y Radau); el test exige < 1e-12.
3. **Freundlich n = 0.43 y Langmuir**, adsorción ($c_0=0.01$, $q_0=0$) y desorción
   ($c_0=0$, $q_0=0.004$), BDF y Radau: monotonía, $q\ge0$, y equilibrio final
   $V_Lc+m_sq^*(c)=$ masa inicial (rtol 1e-5) con perfil radial plano.
4. **Límites**:
   - $D_s$ muy grande ($10^{-6}$ m²/s): partícula uniforme, modelo de película con
     equilibrio en la superficie, $\dot{\bar q}=3k_f(c-c_s)/(\rho_pR)$. Lineal: igual
     a LDF con $k=3k_f/(\rho_pRK)$; Freundlich: igual a una EDO independiente.
     Diferencia < 1e-6·c0 (medida 1.9e-8·c0, lineal).
   - $k_f$ grande frente a LDF de Glueckauf $k=15D_s/R^2$, isoterma lineal
     (cualitativo): $\max|c_{HSDM}-c_{LDF}|/(c_0-c_{eq})$ = 0.24 (τ < 0.05),
     0.046 (0.05–0.2), 0.021 (0.2–0.5), 3.6e-4 (0.5–1), 3.5e-7 (1–2). LDF no
     reproduce el arranque en $\sqrt t$, pero converge al mismo equilibrio y a
     tiempos largos ambos decaen hacia él.

Esto es verificación numérica frente a soluciones analíticas y límites, no
validación experimental.

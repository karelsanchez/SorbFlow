# Esquemas de advección axial

La columna LDF admite dos discretizaciones de la advección axial, seleccionables
con `SolverOptions(axial_scheme=...)`:

| `axial_scheme` | Reconstrucción de cara | Orden (perfil suave) | Uso |
|---|---|---|---|
| `"upwind1"` (defecto) | `c_cara = c_aguas_arriba` | 1 | compatibilidad, mallas gruesas muy rápidas |
| `"tvd"` | MUSCL `c_i + s_i/2`, limitador van Albada | 2 | frentes empinados, precisión por celda |

```python
from sorbflow.solvers import SolverOptions
from sorbflow.reactors.column import effluent_concentration
options = SolverOptions(axial_scheme="tvd", axial_cells=100)
# result = sorbflow.simulate.column(config, options=options)
# c_salida = effluent_concentration(result)   # valor en la cara z = L
```

El valor por defecto sigue siendo `upwind1` y sus trayectorias son idénticas
bit a bit a las de versiones anteriores. El campo se serializa en
`options_json` y forma parte de la huella numérica, por lo que las huellas de
ejecuciones previas cambian aunque la trayectoria no lo haga.

## Formulación

Volúmenes finitos conservativos con caras `0..N`:

- **Entrada (cara 0):** flujo total de Danckwerts `v·c_in` (Dirichlet `c_in` si
  `D_ax = 0`). Igual en ambos esquemas.
- **Caras interiores:** `F = v·c_cara − ε·D_ax·(c_{i+1} − c_i)/dz`. La dispersión
  es siempre central; solo cambia `c_cara`.
- **Salida (cara N):** `F = v·c_cara`, flujo dispersivo nulo (Danckwerts).
- **Estados de masa acumulada:** `d(m_in)/dt = A·F_0`, `d(m_out)/dt = A·F_N`, con
  los mismos flujos de cara que actualizan las celdas: la conservación es exacta
  (residuo de masa al nivel de la tolerancia del integrador, < 1e-10 escalado en
  los casos de prueba).

Limitador (van Albada 1, forma simétrica), con `a` la diferencia aguas arriba y
`b` la aguas abajo de la celda `i`:

```
s(a, b) = ab(a+b)/(a²+b²)   si ab > 0;   0 en otro caso
```

Cumple `0 ≤ s/a ≤ (1+√2)/2` y `0 ≤ s/b ≤ (1+√2)/2`, de modo que el esquema
semidiscreto es LED (no crea extremos locales) y preserva la positividad. Es
diferenciable salvo en `ab = 0`.

Celdas fantasma:

- **Celda 0:** diferencia aguas arriba `2(c_0 − c_b)` respecto del valor de
  cara de Danckwerts `c_b = c_in + w(c_0 − c_in)`, `w = (2εD/dz)/(v + 2εD/dz)`
  (`c_b = c_in` en flujo pistón).
- **Cara de salida:** extrapolación lineal limitada `c_{N-1} + s(a, g)/2`, con
  `a = c_{N-1} − c_{N-2}` y `g = a` si `a ≥ 0`, `g = a·c⁺/(c⁺ − a)` si `a < 0`
  (`c⁺ = max(c_{N-1}, 0)`). Para perfiles resueltos equivale a
  `1.5c_{N-1} − 0.5c_{N-2}` (segundo orden); para perfiles decrecientes
  empinados el valor de cara nunca es negativo. La transición es C¹.

Se probó una variante suave de van Albada sin corte en `ab ≤ 0`: produce
concentraciones negativas (−2.7e-7 kg/m³ con 400 celdas) y fue descartada.

## Concentración de salida: celda frente a cara

`result.outlet_concentration_kg_m3` es el promedio de la última celda, centrado
en `z = L − dz/2`. Compararlo con una solución analítica en `z = L` añade un
error O(dz) **independiente del esquema**. `effluent_concentration(result)`
devuelve la concentración de la cara de salida (exactamente la que integra
`outlet_mass_kg`): para `upwind1` coincide con la última celda; para `tvd` es
la extrapolación de segundo orden a `z = L`.

## Jacobiano

- Diferencias finitas: patrón ensanchado (banda `i−2..i+1` en el bloque
  líquido, fila de masa de salida dependiente de `c[N−2]` y `c[N−1]`).
- Analítico (`jacobian="analytic"`, LDF con Langmuir/lineal): derivada exacta
  del limitador; ver `analytic_jacobian.md`. En el caso Klinkenberg reduce el
  tiempo de CPU un 15–20 % frente a diferencias finitas (100 celdas: 0.72 s
  frente a 0.88 s; 800 celdas: 8.1 s frente a 10.1 s), con resultados iguales.
- HSDM: las columnas HSDM usan los mismos flujos de cara (`AxialTransport`); con `"tvd"`
  las masas acumuladas de entrada y salida usan esos flujos y la conservación es exacta.

## Verificación: Klinkenberg/Thomas LDF, isoterma lineal, flujo pistón

Lecho de 0.1 m, ε = 0.4, ρ_b = 600 kg/m³, K = 1e-3 m³/kg, ξ = kρ_bKL/u = 20,
`c_in = 1`, 401 tiempos hasta 2.5 veces el tiempo estequiométrico. Solución
exacta `c/c0 = 1 − ∫₀^ξ e^{−τ−s} I₀(2√(τs)) ds` (cuadratura adaptativa). Con
ξ = 20 el salto inicial `e^{−ξ}` es 2e-9: el perfil es suave. BDF, tolerancias
por defecto (`rtol = 1e-7`, `atol_c = 1e-10`), Jacobiano por diferencias
finitas, CPU de proceso en un hilo. Error de `effluent_concentration` frente a
`c(L, t)`:

| celdas | upwind1 L2 | upwind1 L∞ | CPU s | tvd L2 | tvd L∞ | CPU s |
|---:|---:|---:|---:|---:|---:|---:|
| 25 | 4.25e-2 | 1.06e-1 | 0.19 | 3.09e-3 | 7.81e-3 | 0.42 |
| 50 | 2.43e-2 | 6.30e-2 | 0.23 | 7.10e-4 | 1.99e-3 | 0.55 |
| 100 | 1.32e-2 | 3.51e-2 | 0.31 | 1.70e-4 | 4.98e-4 | 0.88 |
| 200 | 6.93e-3 | 1.87e-2 | 0.50 | 4.41e-5 | 1.30e-4 | 1.58 |
| 400 | 3.55e-3 | 9.67e-3 | 0.66 | 1.29e-5 | 3.68e-5 | 3.39 |
| 800 | 1.80e-3 | 4.92e-3 | 1.00 | 4.33e-6 | 1.21e-5 | 10.1 |
| 1600 | 9.06e-4 | 2.48e-3 | 2.00 | 1.59e-6 | 4.48e-6 | 45.4 |
| 3200 | 4.54e-4 | 1.25e-3 | 6.45 | — | — | — |
| 6400 | 2.28e-4 | 6.25e-4 | 29.0 | — | — | — |

Orden observado (L∞): `upwind1` 0.75 → 1.00; `tvd` 1.98, 2.00, 1.94 hasta 200
celdas, y 1.8–1.4 en mallas finas, donde domina el error temporal de BDF con
`rtol = 1e-7` (error ~1e-5). El error de la última celda frente a `c(L)` es de
primer orden en ambos esquemas (tvd: 1.1e-2 con 100 celdas) por el
desplazamiento `dz/2` descrito arriba; frente a la solución exacta en el centro
de la celda, tvd vuelve a ser de segundo orden (4.7e-4 con 100 celdas).

**Celdas para L∞ ≤ 1e-3:** `upwind1` ≈ 4000 (3200 dan 1.25e-3; 6400 dan
6.25e-4 en 29 s); `tvd` ≈ 70 (100 celdas: 4.98e-4 en 0.88 s, o 0.72 s con
Jacobiano analítico). La relación coste/precisión mejora entre 10 y 30 veces.

Coste: con igual número de celdas `tvd` es 2–20 veces más caro, porque el
frente, menos difundido, exige pasos de tiempo más cortos (1993 frente a 699
pasos con 400 celdas). El número de pasos escala con `rtol` igual en ambos
esquemas (400 celdas tvd: 1118/1530/1993 pasos con rtol 1e-5/1e-6/1e-7, error
espacial sin cambios), así que el coste extra lo impone la precisión temporal
y no la falta de suavidad del limitador. Recomendación: `tvd` con 50–400
celdas; para mallas de miles de celdas `upwind1` es más barato por paso, pero
alcanzar la misma precisión exige ~50 veces más celdas.

## Positividad en mallas finas con flujo pistón

Guardia física: una concentración menor que `−10·atol_c` en cualquier estado
aceptado provoca `SimulationError`. Resultados con 3200 celdas, `D_ax = 0`,
caso Klinkenberg con `c_in = 0.01 kg/m³` (mínimo de `c` en estados aceptados):

| esquema | variante | min c (kg/m³) | / atol | pasos | CPU s |
|---|---|---:|---:|---:|---:|
| upwind1 | BDF, defecto | −6e-314 | ~0 | 1340 | 4.1 |
| upwind1 | `atol_c = rtol·c_in = 1e-9` | −6e-314 | ~0 | 1431 | 4.3 |
| upwind1 | `rtol = 1e-8` | −4e-314 | ~0 | 1444 | 4.5 |
| upwind1 | Radau | −2.8e-17 | 3e-7 | 658 | 4.3 |
| tvd | BDF, defecto | −3.4e-11 | 0.34 | 6012 | 104 |
| tvd | `atol_c = 1e-9` | −2.1e-10 | 0.21 | 8640 | 291 |

Frente autoafilado (Langmuir `qmax = 0.05`, `K_L = 1000 m³/kg`, `K_L·c_in = 10`,
`k = 0.05 s⁻¹`, 20000 s, frente dentro del lecho): `upwind1` con 3200 celdas da
min c = −1.9e-26 (atol 1e-10, 7253 pasos, 488 s) y −7.9e-312 (atol 1e-9, 372 s);
con 800 celdas `upwind1` −2.3e-32 y `tvd` −7.4e-25 (atol 1e-10) / −1.3e-22
(atol 1e-9). **Ninguna de estas configuraciones LDF reproduce el rechazo** de
16–43·atol observado en la comparación con psdm; esa comparación probablemente
usó otro modelo (HSDM, cuyo balance axial no se modificó aquí) u otras
tolerancias, y debe repetirse con el caso exacto.

Conclusiones:

1. El esquema semidiscreto (ambas opciones) es positivo; cualquier
   subimpulso procede de la integración temporal (BDF no preserva positividad).
   Su tamaño escala con `atol_c`, igual que el umbral de la guardia, así que la
   guardia relativa a `atol` es coherente.
2. `tvd` no elimina los subimpulsos temporales (los aumenta ligeramente al
   mantener el frente más empinado), pero permite alcanzar la misma precisión
   con 30–60 veces menos celdas, que es la forma efectiva de evitar las mallas
   de ≥3200 celdas donde aparece el rechazo.
3. `atol_c` por defecto (1e-10 kg/m³) es absoluto. Con `c_in` mucho mayor que
   1e-3 kg/m³ es muy estricto; con `c_in` ≲ 1e-8 kg/m³ (trazas) es demasiado
   laxo. No se cambia el valor por defecto (no es un error y cambiarlo
   alteraría resultados existentes); se recomienda fijar
   `atol_concentration_kg_m3 ≈ rtol · c_in` (o algo menor) cuando `c_in` se
   aleje de ~1e-3 kg/m³. Con esa escala la guardia (`10·atol`) sigue siendo
   10·rtol relativa a la concentración de entrada.

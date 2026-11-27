# Jacobiano analítico opcional

La columna LDF con isoterma Langmuir o lineal admite:

```python
from sorbflow.solvers import SolverOptions
options = SolverOptions(jacobian="analytic", method="BDF", axial_cells=100)
# result = sorbflow.simulate.column(config, options=options)
```

El valor por defecto sigue siendo `finite_difference`. Ambos caminos resuelven
las mismas ecuaciones de volúmenes finitos, con los mismos flujos, fronteras,
estados de masa y tolerancias. El camino analítico proporciona la matriz CSC
de derivadas al integrador; no cambia el orden espacial del transporte.

Se admite BDF y Radau. La extensión impar usada para estados internos de prueba
tiene pendiente q*'(abs(c)) para los modelos soportados, incluyendo c=0.
Freundlich, HSDM y batch rechazan explícitamente esta opción; no hay fallback
silencioso. Las diferencias finitas mantienen su soporte previo.

La selección se serializa en las opciones y participa de la huella numérica.
Al añadir este campo pueden cambiar las huellas respecto a versiones anteriores,
incluso si la trayectoria del camino por defecto permanece igual.

Las pruebas contrastan productos Jacobiano-vector y resultados de integración
con escalas físicas para concentración, carga y masa. La carga del trazador
nulo se comprueba con tolerancia absoluta, sin normalizar por ruido cercano a
cero. Desorción utiliza una escala de masa que incluye el inventario inicial.

En una columna LDF de 620 celdas la mediana bajó de 17,09 s con diferencias
finitas a 7,77 s con el Jacobiano analítico (2,2 veces más rápido); la ganancia
depende del caso, la plataforma y las tolerancias. La precisión espacial sigue
dependiendo de la malla elegida y se confirma comparando mallas.

## Esquema axial TVD (`axial_scheme="tvd"`)

Con `axial_scheme="tvd"` el Jacobiano analítico usa la **derivada exacta** del
limitador van Albada, `s(a,b) = ab(a+b)/(a²+b²)` si `ab>0` y `0` en otro caso:

```
ds/da = b²(b² + 2ab − a²)/(a²+b²)²,   ds/db = a²(a² + 2ab − b²)/(a²+b²)²
```

evaluadas tras escalar por `max(|a|,|b|)` para evitar subdesbordamiento. En el
conjunto de conmutación `ab=0` (extremos locales) el limitador no es
diferenciable; allí se usa la rama de pendiente nula, que es una dirección de
Newton válida (BDF/Radau solo necesitan un Jacobiano aproximado). También se
derivan exactamente la cara de entrada (valor de Danckwerts `c_b`) y la cara de
salida (extrapolación lineal limitada), incluida la fila de masa de salida
acumulada, que con TVD depende de `c[N-2]` y `c[N-1]`.

La estructura CSC (banda `i-2..i+1` en el bloque líquido) se ensambla una sola
vez; en cada llamada solo se suman los valores. Las diferencias finitas usan el
patrón ensanchado `_jacobian_pattern(cells, "tvd")`. Las pruebas comparan el
producto Jacobiano-vector con diferencias centrales de un `rhs` escrito de forma
independiente (error relativo ~1e-12) y comprueban que el patrón cubre todos
los no ceros. Ver `docs/axial_schemes.md` para precisión y coste.

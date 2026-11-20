# Jacobiano analítico opcional

La columna LDF con isoterma Langmuir o lineal admite:

```python
from pyfast.solvers import SolverOptions
options = SolverOptions(jacobian="analytic", method="BDF", axial_cells=100)
# result = pyfast.simulate.column(config, options=options)
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

Esta implementación puede reducir el coste de construir Jacobianos numéricos;
la mejora depende del caso, plataforma y tolerancias. No corrige difusión
numérica espacial ni demuestra convergencia en mallas grandes. Los casos E04 de
lecho largo y tasa superior siguen sin una puerta de malla establecida; no hay
calibración ni validación ambiental por incorporar esta opción.

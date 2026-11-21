# Operadores de observación experimentales

`sorbflow.observation` separa transporte ideal, muestreo y solver. No cambia `Bed`,
las ecuaciones de columna ni las curvas experimentales.

```python
from sorbflow.observation import LiquidSegment, collection_window, fraction_average

segment = LiquidSegment(volume_m3=1e-5)
flow = 1e-7  # m3/s
delay = segment.residence_time(flow)
window = collection_window(200., volume_m3=7e-6, flow_m3_s=flow, rule="mid")
# cumulative_mass debe proporcionar kg en los extremos desplazados requeridos.
# average = fraction_average(cumulative_mass, window, delay_s=delay,
#                            initially_at_rest=True)
```

`LiquidSegment` admite solamente posición `upstream` y modelos `plug` y `none`.
El tiempo de pistón es V/Q, sin porosidad del lecho. CSTR y dispersión aguas arriba
no están implementados y se rechazan; no se sustituyen por filtros de salida.

`plug_delay(signal, time_s, delay_s)` desplaza una señal prescrita. Si requiere
tiempos negativos, debe declararse `history` o afirmarse explícitamente
`initially_at_rest=True`, que proporciona cero. No se infiere la historia.
Sustituir un segmento aguas arriba por un desplazamiento de salida del lecho
requiere además invariancia temporal y un estado inicial compatible en equilibrio.
Un lecho inicialmente cargado que desorbe no satisface automáticamente esa condición.

`CollectionWindow` declara inicio, final y volumen integrado. `collection_window`
calcula una ventana para Q constante con reglas `start`, `mid` o `end`.
La observación instantánea utiliza directamente `plug_delay`: no es una división
entre una ventana de duración cero. Las ventanas anteriores a t=0 se señalan con
`WINDOW_STARTS_BEFORE_T0`; nunca se recortan ni renormalizan silenciosamente.

`fraction_average(M, window)` calcula [M(b)-M(a)]/V. La identidad matemática
conserva los errores numéricos de M y la posible cancelación. Con retardo no nulo
se desplazan sus extremos; esa sustitución de masa del lecho presupone Q constante.
Con Q variable se debe suministrar M que ya integra Q(t)c_observada(t), declarar
el volumen integral y usar delay_s=0. No desplazar una integral de Q(t)c(t) como
sustituto de integrar Q(t)c(t-retardo).

`SampledSignal` realiza búsqueda exacta y rechaza extremos ausentes. Para una
columna, solicitar al solver los extremos positivos desplazados y t=0. No hay
interpolación implícita ni extrapolación de una malla insuficiente.

Los operadores trabajan en SI y no añaden parámetros ajustables. No establecen
que una capacidad de tubo de 7 mL sea el volumen experimental recogido, que los
tiempos publicados correspondan a puntos medios ni que exista un modelo de error
de laboratorio. Esas hipótesis deben registrarse por condición antes de comparar.

Las pruebas incluyen referencias analíticas puras y una columna trazadora
contrastada con su solución semidiscreta. Esto verifica operadores y acoplamiento;
no demuestra convergencia de la EDP para este caso ni validación ambiental E04.

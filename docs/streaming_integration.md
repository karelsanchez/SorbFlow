# Integración de columna con historia en streaming

`SolverOptions(history="streaming")` activa el muestreo por pasos en columnas LDF.
El valor por defecto es `dense`. BDF/Radau y las isotermas ya admitidas por la
columna LDF siguen disponibles; el Jacobiano analítico conserva su alcance
Langmuir/Linear. Batch y HSDM rechazan streaming explícitamente.

Cada interpolante se evalúa en los tiempos solicitados que le corresponden y se
descarta. Se conserva el estado inicial, cada estado aceptado y cada muestra en
un acumulador de controles de tamaño acotado: no se omiten mínimos de estado ni
residuales internos. Las muestras y el bloque de controles tienen orden Fortran
para mantener el orden de las sumas por columna de la ruta densa.

Las ecuaciones, fronteras, tolerancias y estados de masa acumulada no cambian.
La salida sigue incluyendo los perfiles solicitados; su memoria crece con el
producto de celdas y tiempos pedidos. Streaming reduce la retención de historia,
pero no garantiza memoria constante para los resultados.

Los errores físicos mantienen sus mensajes. `PhysicsViolation` añade una
localización en el acumulador; los fallos generales del integrador siguen siendo
`SimulationError`. Los controles físicos finalizan al terminar la integración,
como en la ruta densa; no se introduce aborto físico temprano silencioso.

Se utilizan las clases públicas BDF/Radau de SciPy. La asignación de un tiempo
exactamente en un extremo interno reproduce la convención de `solve_ivp`: siguiente
segmento para BDF, anterior para Radau. Las pruebas con segmentos artificiales
detectan cambios de esa convención; futuras versiones de SciPy requieren repetir
la verificación. No se usan clases privadas de SciPy en producción.

La selección se guarda en las opciones y en el fingerprint. Añadir el campo
`history` puede cambiar huellas de versiones anteriores sin cambiar trayectorias.
Los protocolos históricos deben permanecer intactos; no se reanudan mezclando
fuentes nuevas con evidencia antigua sin una importación comprobada.

En la medición registrada, streaming redujo la memoria privada de 1.632,9 MB a
956,7 MB con la misma curva de salida, y permitió resolver 7.440 celdas y 4.767
instantes en ≤262,4 s. La convergencia espacial se confirma comparando mallas en
cada condición, como en los controles E04; activar esta opción no calibra parámetros.

La [evidencia seleccionada](../audit/streaming_20261120/summary.json) conserva la
distinción entre la nueva escalera Q1 del núcleo y la escalera Q3 del prototipo
bajo enmienda. Ambas pasan sus pares declarados en 3720–7440 celdas; eso no
certifica toda la caja de tasas ni constituye una calibración.

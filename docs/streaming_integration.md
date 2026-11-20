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

Reducir memoria y completar una simulación no demuestran convergencia espacial,
identificabilidad ni validación ambiental. E04 requiere controles de malla por
condición y parámetros antes de calibrar; no hay calibración automática al activar
esta opción.

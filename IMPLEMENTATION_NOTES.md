# Etapas científicas E2–E3: decisiones previas a implementación

Fecha: 2026-11-18. Alcance: isotermas y LDF batch/columna propios. Sin evidencia
experimental aún; se extiende el alcance a HSDM tras las referencias LDF.
Inferencia avanzada, NSGA-II y CAD permanecen pendientes.

## Dominio genérico y API

No se codifican cuatro materiales ni un contaminante fijo. Species y material son
identidades configurables; una receta admite N componentes y fracciones másicas secas
que sumen uno. La receta documenta preparación: no se deduce una isoterma de mezcla
por promedio de parámetros sin datos. El dominio numérico inicial sigue siendo una
especie acuosa y una temperatura fija por ensayo. Configurar otro contaminante no
implementa competencia, especiación de metales ni cambios de pH automáticamente.

La superficie prevista es `sorbflow.fit`, `sorbflow.simulate`, `sorbflow.optimize`,
`sorbflow.uncertainty`, `sorbflow.design`, `sorbflow.validate`, API/CLI y web posterior.
El core científico y diagnósticos serán independientes de la edición comercial.
SorbFlow se publica bajo Apache-2.0 (decisión del titular, K. A. Sanchez Hernandez,
2026-11-21) con el nombre de distribución `sorbflow`. Una posible edición
`sorbflow-design-pro` se mantendría en un repositorio separado.

## E2

Isotermas con protocolo extensible y fábrica desde parámetros: Langmuir, Freundlich
normalizado y lineal (K>=0, incluyendo trazador K=0). La nueva variante `linear` es
aditiva al esquema v1: archivos anteriores siguen siendo legibles; software anterior
no interpreta la nueva variante. Funciones vectorizadas SI y derivadas explícitas.
Freundlich con exponente<1 tiene derivada singular en cero: se informa, no se suaviza.

Batch cerrado: dos estados c y q; una misma fuente LDF s=k(q*(c)-q) se usa en
dc/dt=-(m/V)s y dq/dt=s. Se integra con BDF/Radau y tolerancias físicas separadas.
Referencia lineal exacta: c_eq=(V c0+m q0)/(V+m K),
c(t)=c_eq+(c0-c_eq)exp[-k(1+mK/V)t]; q se obtiene del balance total.

## E3

Columna cilíndrica uniforme, malla axial de N volúmenes finitos. Flujo interno
J=u*c_upwind-epsilon*Dax*(c_right-c_left)/dz. Fronteras de flujo J_in=u*c_in,
J_out=u*c_last, que discretizan Danckwerts y salida sin gradiente. Se acopla
epsilon dc_i/dt=-(J_right-J_left)/dz-rho_b*s_i, dq_i/dt=s_i.
Inventario por celda A dz(epsilon*c_i+rho_b*q_i); entradas y salidas acumuladas
como estados: dMin/dt=Q*c_in, dMout/dt=Q*c_last. El balance telescopa exactamente
en el espacio. El primer esquema upwind tiene difusión numérica de orden uno.
El valor de salida representa la última celda, no una concentración puntual exacta.

Los integradores implícitos pueden evaluar iteraciones de Newton fuera del dominio.
Solo para esas evaluaciones se extiende q*(c) de forma impar a c<0, sin modificar
la isoterma para c>=0. No se recortan estados ni resultados. Se comprueban los pasos
aceptados y las salidas: negatividad por encima de diez tolerancias absolutas,
estado no finito, fallo del integrador o residuo de masa excesivo generan error.
Una derivada singular puede causar fallo numérico: se reporta, no se oculta.

Jacobiano disperso por diferencias finitas con patrón de dependencias de transporte,
cinética local y cuadraturas. BDF/Radau de SciPy son integradores externos permisivos;
las ecuaciones y flujos de SorbFlow son originales y no usan FAST.

## Evidencia requerida antes de entregar

Isotermas: valores conocidos, límites, derivadas y entradas inválidas. Batch: solución
lineal exacta, equilibrio, adsorción/desorción, masa y comparación BDF/Radau. Columna:
trazador frente analítico, solución de cadena de tanques equivalente al FV, equilibrio,
conservación con dispersión y adsorción/desorción, refinamiento axial/temporal y
comparación entre integradores. Resultados con unidades, opciones, huella de problema,
versiones y diagnósticos exportables sin confundirlos con validación experimental.

Dependencias nuevas revisadas: [licencia NumPy](https://numpy.org/doc/stable/license.html)
y [licencia SciPy](https://github.com/scipy/scipy/blob/main/LICENSE.txt), BSD de tres
cláusulas en sus núcleos. Los wheels pueden incluir bibliotecas adicionales con sus
avisos. Se instalan como dependencias y no se redistribuyen dentro del código SorbFlow.
[solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html)
documenta los integradores y tolerancias usados.

## E4 — HSDM antes de codificarlo

Radios de caras uniformes, centros de cascarón y volúmenes esféricos exactos
w_j=(r_right³-r_left³)/3. El término radial es la diferencia de flujos r²Ds*dq/dr
dividida por w_j. En r=0 el flujo se fija a cero, sin evaluar 1/r². La carga media
usa pesos w_j/sum(w_j).

Película acoplada a la última celda radial: con delta=R-r_last y g=rho_p*Ds/delta,
resolver k_f*c_s+g*q*(c_s)=k_f*c+g*q_last. El lado izquierdo es monótono para las
isotermas actuales; se usa bisección vectorizada acotada y se verifica el residuo.
Para iteraciones implícitas se utiliza la extensión impar documentada, no una
regularización en c>=0. El flujo compartido j=k_f*(c-c_s) entra en la partícula y
sale del líquido con área específica 3(1-epsilon)/R. La igualdad de fuentes y
sumas de cascarones conserva exactamente la masa en la discretización espacial.
La solución de película tiene tolerancia ligada a precisión de máquina; no se
selecciona una concentración superficial ad hoc ni se elimina película implícitamente.
Se permiten hasta 256 bisecciones, con salida al alcanzar residuo relativo de máquina;
casos extremos que no lo alcancen fallan explícitamente.

Se selecciona la expresión de flujo mejor condicionada entre k_f(c-c_s) y
g(q*(c_s)-q_last), comparando escalas de cancelación absolutas. Esto evita pérdida
de precisión en película casi nula o difusión casi instantánea. Compartir un flujo
garantiza conservación, pero por sí solo no prueba que ese flujo sea preciso.

Se retienen perfiles radiales en resultados y JSON. Referencias: serie analítica
de difusión esférica a superficie fija (hasta 80 cascarones), balance columna,
trazador, comparación BDF/Radau y refinamiento radial. Superficie fija es un
benchmark del operador radial, separado del problema físico con película finita.

## Ajuste inverso inicial

`sorbflow.fit.isotherm` ajustará parámetros positivos en coordenadas logarítmicas por
mínimos cuadrados, con incertidumbres de medición opcionales. En Freundlich se fija
c_ref: ajustar simultáneamente q_ref y c_ref introduciría redundancia estructural.
`sorbflow.fit.batch_rate` estimará únicamente k_LDF cuando equilibrio y condiciones se
dan como conocidos. Usará tolerancias de simulación más estrictas que el cambio
de parámetros empleado para diferencias finitas.

SVD del Jacobiano respecto a log-parámetros, condición, rango y covarianza local son
diagnósticos iniciales. No sustituyen perfiles de likelihood, incertidumbre en entradas,
multimodalidad ni validación independiente. El rango deficiente no se oculta con una
pseudoinversa que parezca un intervalo confiable: la covarianza no se devuelve.
No se admiten observaciones censuradas en esta API inicial.

## UQ, diseño y optimización iniciales

Monte Carlo recibirá un muestreador con Generator local y semilla explícita. Conservará
las muestras reales, salidas, cuantiles y error estándar de la media; un fallo del
modelo abortará con índice de muestra, sin eliminar silenciosamente casos inviables.
Sensibilidad central requerirá pasos físicos explícitos para cada parámetro.
La correlación de entradas corresponde al muestreador; no asumir independencia.

Diseño inicial: propiedades hidráulicas, EBCT, masa seca, Ergun y energía de bombeo.
Los costos usarán precios proporcionados por el llamador, moneda y año base explícitos;
no se inventarán valores de mercado. DXF contendrá solo envolvente geométrica en metros,
con metadatos de alcance; STEP y cálculo mecánico serán adaptadores posteriores.

NSGA-II será un adaptador opcional a pymoo, cuya licencia Apache-2.0 se revisa antes
de usarlo. No se copia su implementación. Objetivos de minimización y restricciones
normalizadas g<=0 serán explícitos; fallos de simulación abortan. Se reevalúan las
soluciones finales y se rechaza un resultado sin soluciones factibles. Semilla,
opciones, límites e identificador del problema acompañan el frente. Un frente de
un algoritmo heurístico no prueba óptimo global ni diseño industrial validado.
La robustez se construye con muestras de escenarios comunes entre diseños; la
incertidumbre no se reduce a volver a sortear escenarios en cada evaluación.

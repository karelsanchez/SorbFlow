# Protocolo confirmatorio de benchmarking — SorbFlow / EnvSoft

Versión 0.1; fecha de preparación 2026-11-18, America/Bogota. **Propuesta aún no
congelada ni ejecutada íntegramente.** Los números de diseño muestral y umbrales
de este documento son decisiones propuestas, no resultados observados ni requisitos
editoriales. Los pilotos se identifican y no se mezclan con el conjunto confirmatorio.

## 1. Registro y reglas transversales

Congelar en Git antes de la ejecución: preguntas C01–C08 de NOVELTY_MATRIX.md,
modelos/hipótesis, límites físicos, datos y particiones, generadores de escenarios,
semillas, métricas primarias/secundarias, presupuesto, criterio de parada, tratamiento
de fallos y análisis estadístico. Cambios posteriores generan una enmienda fechada;
no redefinir éxito después de ver resultados. No afirmar prerregistro público sin
depósito real. Conservar resultados negativos e inconclusos.

Unidad de repetición: ensayo/dataset sintético completo, ejecución del optimizador
o candidato previamente seleccionado, según la pregunta; los puntos de una misma
curva no son réplicas independientes. Separar aleatoriedad de datos, inicializaciones,
optimizador, escenarios de búsqueda y validación. Derivar semillas de IDs estables
con SeedSequence/hash explícito, nunca del orden de llegada ni de hash() de Python.

Estados permitidos por experimento: PLANNED, PILOT, RUNNING, PASSED, FAILED,
INCONCLUSIVE, BLOCKED_DATA, BLOCKED_LICENSE. Una figura de demostración no cambia
PLANNED a PASSED. Cada resultado cita configuración, commit, entorno, entrada,
semilla, run_id, log, versión de métrica y hashes de artefactos.

## 2. E01 — verificación física, discretización y estabilidad

**C01/C06.** Distinguir error de formulación, espacial, radial, temporal y clasificación
de restricciones. Separar la evaluación de un sistema discreto exacto de la convergencia
a una EDP continua. Un cierre de masa pequeño no garantiza precisión del transporte.

| Familia | Referencia independiente | Variaciones y métricas |
|---|---|---|
| Batch lineal LDF | Solución exponencial cerrada | Adsorción, desorción, equilibrio, inventario cero y escalas de masa |
| Transporte sin adsorción, Dax=0 | Frente convectivo continuo y cadena de tanques FV exacta | Pe infinito; error L1, llegada t50, masa; no orden puntual en discontinuidad |
| Transporte con dispersión, Pe finito | Referencia continua compatible con Danckwerts o MMS; matriz FV con dispersión como referencia discreta separada | La matriz verifica el sistema discreto, no demuestra convergencia a la EDP |
| Equilibrio instantáneo lineal | Modelo reducido explícito con retardo | No sustituirlo por un k artificialmente enorme |
| Solución suave manufacturada | Fuente y fronteras derivadas de c(z,t),q(z,t) prescritas | Orden espacial; fuente independiente del RHS productivo |
| Difusión esférica | Serie analítica a superficie fija | Carga media y perfil, centro, pesos de cascarón |
| HSDM con película lineal | Eliminación analítica de interfaz y exponencial de matriz | Ambas resistencias, precarga, dispersión y estados no nulos |
| Límites de transferencia | Formulaciones reducidas y flujo lineal exacto | Película casi nula, difusión rápida/lenta, equilibrio sin flujo espurio |
| Cargas no lineales | BDF/Radau y refinamientos cruzados | Langmuir/Freundlich; c cercano a cero, rigidez y derivada singular |

Mallas propuestas: Nz=25,50,100,200,400; Nr=10,20,40,80. Refinar por separado
antes de un refinamiento conjunto. Tolerancias relativas 1e-4,1e-6,1e-8 y una
referencia más estricta cuando el rango de máquina lo permita; atol por fase/unidad.
No relajar automáticamente el criterio de masa para conseguir un resultado exitoso.
Una corrida deliberadamente gruesa para medir error se identifica como tal.

Mapa de regímenes: Pe=vL/Dax en {1,10,100,1000} y caso Dax=0; Da_LDF=kL/v en
{1e-3,1e-1,1,10,1e3}; para HSDM, tiempos R²/Ds y kf junto con un Bi definido
explícitamente, p.ej. Bi=kf R c_ref/(rho_p Ds q_ref). No comparar números Bi/St
de distintas convenciones. Los extremos numéricos no se presentan como condiciones
experimentales plausibles. Registrar todos los parámetros dimensionales del mapa.

Criterios candidatos: masa relativa <=1e-6 con escala física explícita y masa absoluta
reportada; estados finitos y negatividad dentro de tolerancias, sin clipping; referencia
batch L2 relativa <=1e-5; captación esférica relativa <=1e-3 en tiempos declarados;
error de llegada de referencia <=1%; cambio <0.5% en t10,t50,t90 y capacidad entre
dos mallas finales, cuando esos indicadores existan. Para MMS suave convectiva,
orden esperado aproximadamente uno (p>=0.8); difusión centrada radial se evalúa aparte.
Si la asintótica no se alcanza o un indicador está censurado, reportar INCONCLUSIVE,
extender estudio o delimitar dominio; no asignar un valor de ruptura inexistente.

Calcular capacidad captada con inventarios y entradas/salidas, incluyendo precarga
y líquido retenido; no equiparar toda remoción líquida a carga sólida. Registrar
errores de flujo superficial y de la raíz de película además de masa.

**Prueba de decisión:** obtener c_out/eventos con dos mallas y tolerancias. Si la
clasificación factible/inviable cambia, marcar no resuelto, refinar y contabilizar
su costo. Comparar el procedimiento con y sin control de error numérico (C06).
Richardson empírico no se denomina cota rigurosa universal.

## 3. E02 — problema inverso e incertidumbre

**C03/C04.** Generar verdades sintéticas fuera del código inverso cuando sea posible:
soluciones exactas y un solver independiente/malla de referencia. Evitar el inverse
crime de producir y recuperar datos con la misma malla sin perturbaciones.

Diseños de información: isoterma en rango estrecho/amplio, una curva de columna,
ensayos complementarios batch/columna y variación de caudal/tamaño de partícula.
Mantener presupuesto de información igual entre métodos comparados. Si un método
elige ensayos adicionales, incluir su costo y un baseline con igual número de ensayos.

kf depende de hidrodinámica: predefinir una correlación/mapping kf(Re,Sc,dp) con
dominio y factor global, o estimar parámetros por ensayo justificadamente. No asumir
que k_LDF global o kf constantes se transfieren a Q/dp distintos sin una hipótesis
comprobable. Ds puede compartirse solo entre material/lote/T compatibles.

Factores: LDF/HSDM, isoterma, resistencia dominante, nivel de ruido y diseño de datos.
Baseline de error: gaussiano aditivo/heteroscedástico conocido; extensiones con
correlación, censura y discrepancia son estudios separados. Especificar LOD y protocolo
de muestreo; no convertir no detectados en ceros. Validación por ensayo completo.

Comparadores: ajuste puntual de un inicio; multi-inicio con mismas restricciones;
metodología con perfiles/decisión de parametrización; ablations sin diagnóstico y
sin dependencia de parámetros. Al menos 20 inicios propuestos, con mismo presupuesto
total de evaluaciones; fijar antes del estudio. SVD local no sustituye perfiles.

Métricas: recuperación relativa/escalada, sesgo, RMSE, multimodalidad, mínimos
alcanzados, perfiles abiertos/cerrados, correlación, cobertura de theta y de predicción,
anchura de intervalos y costo. No evaluar error relativo de un parámetro cuyo valor
verdadero sea cero. Intervalos muy amplios no cuentan como buen desempeño por cobertura sola.

Plan candidato de cobertura: piloto R=50 datasets por régimen para dimensionar costo;
estudio confirmatorio R=500 en regímenes preseleccionados. A cobertura nominal 0.95,
el error estándar binomial esperado para R=500 es aproximadamente 0.00975; esto
es cálculo de diseño, no cobertura observada. Presentar intervalos binomiales y
evaluar tolerancias predefinidas de cobertura y anchura. Si se cambia R por presupuesto,
declarar potencia/precisión resultante, sin reutilizar el piloto como test independiente.

Verificar inferencia frecuentista mediante datasets repetidos; inferencia bayesiana
incluye diagnósticos propios y sensibilidad a priors. Distinguir respuesta latente
de observaciones futuras. Propagación debe incluir incertidumbre de entradas y,
cuando se justifique, discrepancia; Monte Carlo de una covarianza local no demuestra
esas capacidades. Sensibilidad bajo entradas correlacionadas requiere definición adecuada.

## 4. E03 — benchmark de decisión robusta

**C05/C06.** Comparar, en varios regímenes físicos y no solo un material:

- B0: diseño convencional con regla explícita, información y parámetros declarados.
- B1: optimización determinista con estimación puntual, restricciones nominales.
- B2: optimización robusta con escenarios y el mismo modelo/datos de calibración.
- B3: metodología completa con diagnóstico de identificabilidad, dependencia de
  parámetros y control de clasificación por error numérico.
- Ablaciones de B3: sin perfiles/decisión de parametrización, sin correlaciones,
  solo incertidumbre paramétrica, y sin control numérico. Cambiar un factor cada vez.

Los métodos no reciben datos retenidos ni escenarios de validación. Fijar objetivos
y direcciones comunes, límites de dominio, precios/moneda/año, restricciones conjuntas
de trayectoria y reglas de selección de candidatos. Comparar costo de robustez junto
con confiabilidad; no esperar que robustez domine en todo objetivo.

### Presupuesto y Pareto

Métrica primaria de presupuesto: número total de solves físicos de fidelidad declarada,
incluyendo escenarios, calibración cuando difiera entre métodos, refinamientos y fallos.
El número de evaluaciones de diseño de pymoo no es ese costo: una evaluación robusta
puede ejecutar muchas EDP. Informar también CPU-horas, wall time, memoria y caché.
Mostrar curvas de calidad vs presupuesto; comparación secundaria a igual número de
candidatos debe etiquetar el cómputo extra. Propuesta inicial: 30 semillas de optimizador
por método/régimen y presupuesto elegido con un piloto, después congelado.

Usar normalización y punto de referencia de hipervolumen comunes, fijados antes del
conjunto confirmatorio; no normalizar cada frente con sus propios extremos. Evaluar
hipervolumen fuera de muestra de frentes factibles, distancias cuando haya frente
analítico y estabilidad entre semillas. No existe frente verdadero conocido para
la aplicación física: no inventarlo. Reportar factibilidad, dispersión de resultados,
trade-offs y candidatos no resueltos, no solo el mejor run.

### Confiabilidad fuera de muestra

Definir evento conjunto G=max de restricciones normalizadas en trayectoria, presión
y dominio. Usar escenarios comunes congelados en búsqueda y escenarios independientes
para validación. Seleccionar el conjunto de candidatos antes de abrir validación;
si luego se elige sobre ese test, reservar un test adicional o ajustar la inferencia.

Para un candidato fijo con k incumplimientos de n escenarios IID independientes,
usar cota unilateral exacta de probabilidad de fallo. Para k<n:

    p_U = BetaQuantile(1-beta; k+1,n-k); si k=n, p_U=1.
    aceptar confiabilidad declarada solo si p_U<=alpha.

Si k=0: p_U=1-beta^(1/n). Ejemplos aritméticos, **no resultados**: a confianza
unilateral 95%, cero fallos en 59 escenarios permite p_U≈4.95%; en 299 permite
p_U≈0.997%. Tres escenarios independientes darían ≈63.2%, y los tres escenarios
actuales de búsqueda ni siquiera constituyen ese test independiente. Para 20 diseños
simultáneos y alpha=1%, Bonferroni beta/20 exige al menos 597 escenarios por diseño
si todos tienen cero fallos. Usar el tamaño y la regla reales, no estos ejemplos por defecto.

No tratar escenarios correlacionados, cuantiles o draws de una cadena no convergida
como n IID. Incertidumbre en la ley generadora requiere análisis externo/sensibilidad.
No aplicar garantías de métodos convexos de escenarios a NSGA-II no convexo sin sus
hipótesis. Si no existe ley probabilística defendible, cambiar el claim a robustez
en un conjunto de escenarios, sin certificado probabilístico.
Referencia operativa para intervalos binomiales: [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html).

### Análisis de comparación

Primaria: diferencia pareada de frecuencia/riesgo de incumplimiento fuera de muestra
a igual presupuesto, con intervalo de confianza y magnitud práctica predefinida.
Secundarias: hipervolumen factible, material, energía/costo, error y runtime.
Para distribuciones asimétricas usar bootstrap por seed/ensayo, no por punto temporal;
controlar comparaciones múltiples. No equiparar p>0.05 con equivalencia: esta exige
margen y diseño específicos. Definir Delta=p_fallo(B1)-p_fallo(B3), positivo cuando favorece al método robusto,
y un beneficio práctico mínimo delta_min antes del estudio. Para la hipótesis de
dirección Delta>0, un IC que cruza cero es INCONCLUSIVE; no prueba igualdad. Para
la hipótesis práctica Delta>=delta_min, límite inferior>delta_min apoya el beneficio,
y límite superior<delta_min excluye ese objetivo práctico con la precisión indicada.
Esto último puede limitar la superioridad práctica aunque la dirección siga
inconclusa; no se denomina prueba de equivalencia. Un IC completamente negativo
apoya efecto adverso para este dominio/presupuesto. Si la ventaja desaparece al
igualar presupuesto o incluir discrepancia razonable, delimitar ese alcance.
El valor de delta_min queda por fijar y justificar antes de congelar el protocolo,
no se elegirá después de observar los resultados.

## 5. E04 — aplicación ambiental independiente

**C02/C08.** Ver EXPERIMENTAL_VALIDATION.md. Separar los cuatro materiales y mezclas
como registros externos. Retener ensayos completos, declarar extrapolación y no
reajustar con la curva usada para evaluar predicción. Cada parámetro transferido debe
tener mapping físico y dominio de validez. Las métricas y umbrales se fijan con
incertidumbre experimental, no para favorecer una curva. Sin datos autorizados,
estado BLOCKED_DATA, sin curvas experimentales o estadísticos ficticios.

## 6. E05 — reconstrucción, ejecución paralela y recuperación

**C07.** En el prototipo, `checkpoints` son estados RAM para controles; no son
checkpoint persistente de integrador ni ejecución distribuida. Un arnés SMOKE con
dos tareas paralelas tampoco demuestra escalabilidad del framework científico.

Para el estudio completo: workloads batch/LDF/HSDM de costo heterogéneo, conjunto
fijo de tareas, serial vs 2/4/8 workers si existe hardware, y nodos múltiples solo
si realmente disponibles. Registrar CPU/RAM/SO, versiones, afinidad, BLAS threads,
I/O y almacenamiento; evitar oversubscription. Varias repeticiones con orden aleatorio,
warm/cold start separados. Strong scaling: mismo trabajo, S_p=T_1/T_p y E_p=S_p/p.
Weak scaling: trabajo proporcional a p. Separar cómputo, cola, serialización e I/O.

Pruebas de recuperación: matar un worker, interrumpir coordinador, introducir fallo
de solver y artefacto corrupto; reanudar sin duplicados, sin reutilizar hashes inválidos
ni perder fallos. Comparar estados de tarea y resultados con la ejecución ininterrumpida.
Persistir población/RNG del optimizador para reanudar una búsqueda; reiniciar una
EDO desde c/q sin historia BDF no garantiza identidad de trayectoria de integración.
Declarar si se reanudan tareas completas, optimizador o integrador.

Reproducibilidad numérica: misma semilla y entorno deben reconstruir las mismas
tareas y resultados con tolerancias preregistradas. Para optimización generacional,
ensamblar resultados en orden estable; no permitir que el orden de finalización cambie
la selección sin declararlo. Fallos/costo deben permanecer visibles.

## 7. FAST y otras comparaciones externas

FAST requiere instalación legal del usuario, versión/hash, condiciones de licencia
compatibles y contrato I/O documentado. No redistribuir EXE/recursos ni ejecutar
simulaciones existentes. Normalizar ecuaciones, unidades, base seca/húmeda, densidades,
isoterma y ejes antes de comparar. Si no coinciden modelos, explicar diferencia;
concordancia no prueba verdad. Estado actual: NOT_RUN/BLOCKED_LICENSE_OR_INTERFACE,
no poner error cero ni asumir compatibilidad.

Pysorb/RUPTURA/pyAPEP/pyDAC se comparan solo donde dominio y formulación sean compatibles.
SWAT-UQ/Optienv/UQPyL/EMA/OpenMORDM son antecedentes metodológicos/orquestación;
no comparar directamente sus errores hidrológicos con los de una columna acuosa.
Un comparador indisponible se declara, no se sustituye por números publicados bajo
hardware/datos distintos como si fueran mediciones pareadas.

## 8. Artefactos mínimos y decisión editorial

Entregar tabla por E01–E05 con estado, alcance y razón de fallo; métricas en formato
tabular, fuentes/configuraciones versionadas, semillas, logs, manifiestos, scripts
de figuras/tablas y release inmutable. El registro de claims debe poder concluir
SUPPORTED_WITHIN_DOMAIN, REFUTED, INCONCLUSIVE o NOT_TESTED. La aceptación en una
revista no se deduce de pasar pytest ni de completar esta lista.

## Precisiones de comparación

Para referencias manufacturadas comparar promedios de volumen/cascarón consistentes con los estados FV, no valores puntuales en centros como si fueran la misma magnitud. Las fuentes manufacturadas son instrumentación de prueba explícita, no reacciones añadidas silenciosamente al modelo productivo. En E02 evaluar identificabilidad de cantidades de decisión además de parámetros: no rechazar un diseño solo por ambigüedad paramétrica si su predicción está suficientemente determinada.

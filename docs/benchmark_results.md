# Benchmarks ejecutados — 20 de noviembre de 2026

[Inicio](index.md) · [Estado científico](scientific_status.md)

La [evidencia resumida](../audit/benchmarks_20261120/summary.json) y los
[hashes de protocolos](../audit/benchmarks_20261120/protocol_hashes.json)
identifican campañas congeladas antes de calcular. Son subestudios acotados del
plan original; no equivalen a ejecutar todas las variantes de ese plan.
La [captura de arneses y guía de reproducción](../benchmarks/reproduction_20261120/README.md)
conserva los scripts originales, pruebas e insumos sintéticos sin datos externos.

## Verificación física y numérica

E01 añadió 29 casos y 148 criterios, todos aprobados: batch Langmuir frente a
referencia implícita derivada por balance y separación de variables; HSDM lineal
acoplado con película frente a una matriz discreta construida independientemente;
refinamientos y comparación BDF/Radau para modelos no lineales. Se conservaron
masa, negatividad, indicadores de ruptura y carga sólida.

La matriz comprueba el problema discreto, no una EDP continua. Las comparaciones
entre integradores no son referencias analíticas. Siguen fuera de este estudio
la solución manufacturada no lineal continua, el mapa completo Pe/Da/Bi y la
referencia analítica del HSDM no lineal.

## Inferencia con ruido conocido

E02 materializó 3.000 datasets sintéticos y calculó 6.000 perfiles exactamente
en la verdad; todos terminaron sin inconclusos. El predictor es la solución
analítica de batch lineal: esta campaña comprueba la inferencia de perfiles,
sin solves ODE ni afirmación de cobertura para columnas.

| Escenario | Réplicas | Inclusión marginal de K | Inclusión marginal de k |
|---|---:|---:|---:|
| S1 | 1.000 | 0,950 | 0,941 |
| S2W | 1.000 | 0,957 | 0,960 |

Los cinco escenarios diagnósticos restantes tuvieron 200 réplicas cada uno.
El resumen conserva conteos e intervalos Wilson descriptivos. Las proporciones
anteriores son observadas, no garantías de cobertura. El estudio no acredita
equivalencia, cobertura conjunta, cierre de intervalos ni identificación global.
Se conservaron las medidas negativas y las diferencias de chi-cuadrado sin recorte.

## Diseño determinista y robusto

E03 utilizó el solver LDF lineal real, NSGA-II, dos semillas por método y
distribuciones sintéticas declaradas. Los diseños se congelaron antes de generar
40 escenarios comunes de evaluación independientes del entrenamiento.

La campaña inicial consumió 881 solves. El acuerdo entre mallas N40/N80 falló
en 12 pares y cambió una clasificación de factibilidad. Una enmienda posterior
conservó diseños, escenarios y tolerancias y comprobó N80/N160, con reglas
prospectivas para N320/N640 si fueran necesarias. Las 200 comprobaciones pasaron
en N80/N160, con 200 solves adicionales y sin reoptimización.

| Diseño congelado | Incumplimientos / 40 |
|---|---:|
| Base | 0 |
| Determinista, semilla 1 | 13 |
| Determinista, semilla 2 | 6 |
| Robusto, semilla 1 | 0 |
| Robusto, semilla 2 | 0 |

Los diseños robustos se mantuvieron dentro de especificación en los 40 escenarios
independientes, frente a 6 y 13 incumplimientos de los deterministas. Es una
comparación descriptiva con un presupuesto fijado de antemano: amplía la evidencia
con más semillas y escenarios antes de generalizar a otros problemas. El refinamiento
resuelve la evaluación numérica de los diseños elegidos; los costes reales y de
caché se conservan por separado.

## Caso de columna C-B

La continuación de C-B alcanzó convergencia local en 13 evaluaciones y añadió
48 solves completos. El candidato tiene k=7,78219e-6 s^-1,
q_max=0,152827 kg/kg y SSE=9,25617 sobre 183 puntos. La mejora descriptiva respecto
a C-A es aproximadamente 2,22 % (la primera campaña C-B había registrado 2,14 %).
Los controles de malla pasaron. Las diferencias por condición señalan dónde un modelo
más completo del sistema puede mejorar el ajuste. Las condiciones de evaluación ya
estuvieron expuestas en campañas anteriores y las observaciones proceden de una
figura publicada.

## Criterio de publicación del software

SorbFlow se describe y evalúa mediante referencias analíticas, datos sintéticos y
datasets existentes, con instalación, pruebas y documentación reproducibles. La
publicación depende además de la revisión de derechos y distribución. El paquete no
incluye ejecutables ni recursos de otros programas.

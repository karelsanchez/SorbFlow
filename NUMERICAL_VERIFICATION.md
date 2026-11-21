# Estado científico y verificación numérica — 0.2.0.dev0

Fecha: 2026-11-18 (America/Bogota). Repositorio independiente `D:\PyFAST`.
Estado: **prototipo con referencias numéricas seleccionadas, sin validación experimental**.
No se ha comparado contra salidas FAST ni se ha alegado novedad por usar Python o NSGA-II.

## Implementado y ejecutado

- Langmuir, Freundlich normalizado y lineal, incluyendo derivadas y trazador K=0.
- Batch LDF cerrado con solución lineal exacta y masa compartida entre fases.
- Columna LDF por volúmenes finitos, dispersión axial y fronteras Danckwerts.
- Columna HSDM por cascarones esféricos, película acoplada y perfiles radiales.
- BDF/Radau con patrón disperso, tolerancias físicas y controles de pasos aceptados/salidas.
- Ajuste de isotermas y de k_LDF batch; rango, condición y covarianza logarítmica local.
- Monte Carlo con correlaciones, cuantiles, error estándar y sensibilidad central.
- NSGA-II opcional, restricciones normalizadas, semillas y reevaluación de candidatos.
- EBCT, residencia, masa seca, Ergun, potencia, costo parcial con precios externos y DXF de proceso.
- CLI de simulación, JSON/CSV con unidades, huellas, versiones y ejemplos integrados.

Los identificadores de especie/material y mezclas de N componentes son datos. El
ejemplo sintético no fija las cuatro materias primas de la investigación ni impone
una ley de mezcla no contrastada. La parametrización para otros contaminantes exige
datos, equilibrio y supuestos químicos apropiados.

## Evidencia cuantitativa reproducible

`examples/numerical_benchmarks.py` genera los datos que acompañan este informe en
`audit/numerical_metrics.json`. Son casos concretos, no garantías para todo parámetro.

| Referencia | Resultado observado |
|---|---|
| Batch lineal, BDF a rtol=1e-9 | Error máximo c = 1.442e-11 kg/m³ |
| Batch lineal, masa | Residuo máximo escalado = 5.082e-16 |
| Trazador, 200 celdas, comparación temporal con cadena FV exacta | Error máximo normalizado = 5.806e-8 |
| Trazador, llegada t50 a 200 celdas | Error relativo = 0.1666% |
| Trazador, error L1 frente discontinuo Nz=25/50/100/200 | 0.15898 / 0.11261 / 0.07969 / 0.05638 |
| Difusión esférica, Nr=10/20/40/80 | Error máximo de carga media normalizada: 0.01774 / 0.003808 / 0.0009282 / 0.0002307 |

El error integral del frente discontinuo disminuye lentamente por difusión numérica
upwind; el buen t50 no demuestra precisión de t10/t90. La comparación con cadena
de tanques verifica la integración del sistema FV, y la comparación con el frente
continuo verifica el refinamiento espacial: son evidencias distintas.
La difusión esférica muestra aproximadamente segundo orden en estos puntos de
Fourier. Ese benchmark fija concentración/carga superficial; las pruebas con película
finita verifican adicionalmente balance, signo de desorción y BDF/Radau.

## Flujo sintético integrado

Se ejecutó `examples/scientific_demo.py`: ajuste Langmuir -> LDF/HSDM -> propagación
local lognormal de parámetros -> hidráulica -> JSON/CSV, DXF y figura.
Recuperó qmax=0.005 kg/kg y b=10 m³/kg, con condición del Jacobiano logarítmico≈5.95.
En ese ejemplo el residuo máximo absoluto fue 1.34e-17 kg (LDF) y 2.04e-16 kg (HSDM);
residuos escalados 1.08e-9 y 8.15e-9. Los valores negativos mínimos HSDM fueron del
orden de 1e-51/1e-54, muy por debajo de las tolerancias y sin recortarlos.
Las dos curvas usan hipótesis cinéticas distintas: su separación no es un error de
comparación ni demuestra equivalencia LDF/HSDM.

La covarianza local supone sigma de medición sintética conocida; los cuantiles de
32 muestras no son una prueba de cobertura ni de convergencia estadística. Se conservan
muestras/semilla/huellas para permitir repetición y aumentar el estudio.

`examples/robust_column_design.py` ejecutó NSGA-II con población 16, cinco generaciones,
tres escenarios sintéticos comunes y semilla 42. Produjo 11 candidatos preliminares;
los 11 pasaron concentración máxima al horizonte y presión máxima al reevaluarlos
con 80 celdas, frente a 20 durante la búsqueda. Esto es un ejemplo funcional, **no**
un frente convergido, una garantía probabilística ni un diseño industrial aceptado.
Los escenarios, límites, configuración y resultados refinados acompañan el ejemplo.

## Pruebas y alcance pendiente

La suite actual tiene 269 casos y los 269 pasan, con 98.31% de cobertura de líneas; el registro final de ejecución, tipos, lint,
construcción e instalación se guarda en `audit/verification_v02.txt`.
La matriz Windows/Linux y Python 3.11–3.13 está configurada pero solo se ejecuta
localmente Windows/Python 3.11.2 en esta tarea. La cobertura no demuestra validez física.

Pendientes antes de cerrar V1: caso manufacturado suave completo, barrido de regímenes
rígidos/Pe/Biot y errores t10/t90/capacidad con refinamiento suficiente por problema.
Pendientes E5/E6: perfiles de likelihood, multi-inicio, censura, identificación conjunta
multiexperimento y cobertura predictiva con discrepancia de modelo.
Pendientes E7: estudio de semillas/hipervolumen, escenarios suficientes, reoptimización
y estimación mecánica/costos completos. STEP e interfaz web aún no están implementados. Parquet de salida/balance es un extra opcional; CSV experimental con unidades explícitas ya está disponible.

V2 requiere ensayos independientes con geometría, flujo, unidades, masa seca/humedad,
analítica, incertidumbres, censura, lotes y derechos de uso. El ZIP de FAST no aporta
esos datos. La publicación científica, nombre PyPI, licencia abierta definitiva y
titularidad universitaria siguen pendientes; no impiden continuar la verificación técnica.

## Separación de dependencias y derechos

El solver de SorbFlow usa NumPy/SciPy y balances/discretización propios; no usa FAST.
El extra NSGA-II usa pymoo Apache-2.0 y moocore LGPL-2.1-or-later. Sus condiciones
de redistribución no se trasladan a una supuesta licencia propietaria por omisión;
el árbol opcional debe revisarse al preparar un producto comercial. Detalle en
IP_LICENSE_AUDIT.md. No se incluyen ejecutables FAST ni wheels de terceros.
El ZIP original conserva su SHA-256 de auditoría y no se ejecutó ni alteró.

## Revisión independiente en paralelo

Una segunda revisión derivó matrices afines lineales para los sistemas discretos LDF/HSDM con dispersión, película y estados iniciales no nulos. `examples/linear_matrix_reference.py` compara con expm(Mt) y se ejecuta como prueba. Métricas en audit/linear_matrix_metrics.json: errores de concentración del orden de 1e-12–1e-11 kg/m³ y masa escalada <6e-16 en el caso revisado.

La revisión detectó cancelación en el cálculo de película casi nula: un flujo compartido puede cerrar masa y ser inexacto. Se corrigió seleccionando la expresión mejor condicionada entre película y sólido. Las regresiones cubren kf de 1e-12 a 1e9 m/s como límites numéricos, sin afirmar plausibilidad física de todo ese rango. El error relativo lineal pasó a aproximadamente 1e-13 y se eliminó el flujo de equilibrio espurio relevante.

La envolvente DXF fue leída y auditada por ezdxf 1.4.5: unidades metros, geometría esperada, cero errores y cero reparaciones. Eso no equivale a un plano mecánico. CSV y Parquet agregan pruebas de conversiones, preservación del original, metadatos e ida/vuelta.

## Comprobaciones de distribución

Ruff (lint/formato), mypy estricto (37 archivos), pip check y construcción wheel/sdist pasan. El wheel se instaló en un directorio/entorno independiente y los 269 casos también pasaron contra esa instalación; se comprobó su ruta de importación y contenido byte a byte. Para esa prueba se reutilizaron dependencias del entorno ya verificado sin procesar sus archivos editable .pth: se verifica aislamiento del paquete SorbFlow, no una resolución de dependencias desde cero en otro sistema. La ejecución remota de la matriz CI sigue pendiente.

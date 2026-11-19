# Validación experimental independiente y separación del caso ambiental

Versión 0.2, 2026-11-19. Estado de E04: **BLOCKED_METADATA**.
Hay seis fuentes externas descargadas en `datasets_benchmark_pyfast/`,
documentadas por su inventario local. Ese inventario registra tres series
acuosas con reservas y cero curvas listas para validación física independiente.
Las licencias y verificaciones previas se registran como reportadas por ese
inventario; esta integración no vuelve a certificar su procedencia.
Consultar `../benchmarks/data_catalog/DATASET_READINESS.md` y
`../benchmarks/data_catalog/DATASET_REGISTRY.json` para las limitaciones
por fuente. No se han ajustado ni simulado estos datos en esta entrega.
Siguen pendientes los metadatos, derechos y datos independientes del caso
de los cuatro materiales. No se inventan mediciones ni resultados.

## 1. Preguntas y unidad experimental

Evaluar predicción de efluente, ruptura/capacidad y confiabilidad de diseño con datos
no utilizados para estimar los parámetros de ese ensayo. Separar desempeño del
adsorbente de desempeño de la metodología/modelo. Un material puede remover bien
y estar mal modelado, o un modelo representar bien un material de baja capacidad.

La unidad independiente es un ensayo/preparación/lote, no cada punto de una curva.
Definir qué réplicas son técnicas y cuáles son preparaciones/columnas independientes.
No inflar n con muestreos densos del mismo ensayo. Dimensionar réplicas e información
mediante un piloto y análisis de incertidumbre/potencia, sin anunciar un número como
si ya se hubiese ensayado o como garantía universal de identificabilidad.

## 2. Paquete de aplicación separado del framework

Estructura de datos propuesta, sin escribir dentro de los originales:

    case_studies/water_adsorption_four_materials/
      registry/       # IDs, unidades, responsables, derechos y particiones
      raw/            # copias autorizadas o referencias de solo lectura + hashes
      processed/      # transformaciones explícitas, reversibles y versionadas
      configurations/ # modelos, dominio, priors/bounds y mapeos entre condiciones
      splits/         # ensayo/lote/condición: calibration, development, test
      results/        # run_id, diagnósticos y artefactos generados

Si los datos deben permanecer privados, mantenerlos en almacenamiento autorizado
y publicar fixtures sintéticos y las transformaciones; declarar qué resultados no
pueden reproducirse públicamente. No afirmar reproducción completa del artículo si
un resultado central requiere datos inaccesibles o un módulo comercial.

Los cuatro materiales serán registros con IDs definidos por sus propietarios.
Los rótulos M1–M4 pueden servir para planificar, pero no son identidades ni mediciones.
Las mezclas admiten N componentes, fracciones másicas secas y trazabilidad de lotes.
No promediar isotermas/cinéticas automáticamente. Si se ajusta una ley de mezclas,
declarar interacción, diseño en el simplex y validación de composiciones retenidas.
Cambiar de material o contaminante no debe introducir una rama específica en el solver.

## 3. Metadatos mínimos a obtener

| Grupo | Datos requeridos y su incertidumbre |
|---|---|
| Procedencia/derechos | Propietario, responsable, versión, uso permitido, publicación, hash y fecha |
| Material | Identidad, preparación, lote, humedad/base seca, composición y tratamiento |
| Partículas | Distribución de tamaños, forma, densidad aparente y método de medida |
| Lecho | L, diámetro, masa seca, porosidad, empaque, soporte y condiciones iniciales |
| Operación | Q medido y variación, c_in medida en el tiempo, T, pH, química de matriz |
| Analítica | Método, calibración, blancos, LOD/LOQ, incertidumbre y tratamiento de censura |
| Muestreo | Tiempos reales, volumen/promediado, réplicas, pérdidas y perturbación del sistema |
| Hidráulica | Presión, unidades, pérdidas del soporte/conexiones y estado del lecho |
| Observación | Datos originales, flags de calidad, valores ausentes y causas; sin imputación oculta |

Los límites de efluente del estudio se documentan por finalidad/criterio externo.
Una curva bajo un límite de investigación no certifica potabilidad ni cumplimiento
normativo no evaluado. El código no debe introducir un límite universal por nombre
del contaminante.

## 4. Comprobación de hipótesis físicas

Antes de calibrar, evaluar blancos y balance de laboratorio: pérdida en paredes,
degradación, precipitación, volatilización u otros mecanismos pueden invalidar una
interpretación exclusivamente adsorptiva. Documentar qué se examinó realmente.
Revisar régimen diluido, T estable, constancia de Q/c_in y evidencia de canalización,
dispersión o distribución de partículas. Si la entrada varía, no representarla como
constante sin cuantificar el efecto; el prototipo actual requiere esa extensión.

Estimar porosidad/RTD con un trazador apropiado y contrastar el almacenamiento líquido
intrapartícula. Un trazador que acceda a poros internos no determina automáticamente
la epsilon interpartícula del HSDM actual. Las densidades deben ser compatibles con
masa seca y volumen aparente. Registrar incertidumbre y dependencia entre esas medidas.

La transferencia k_LDF efectiva o k_f puede cambiar con Q, dp y condiciones. Para
predicción en una condición retenida, fijar antes un mapping/correlación con dominio
y parámetros globales; incluir su incertidumbre. Reajustar k_f con la propia curva
retenida invalida la afirmación de predicción externa. Si no existe mapping defendible,
restringir el claim a las condiciones calibradas en lugar de asumir transferibilidad.

## 5. Estrategia de calibración y particiones

1. Isotermas independientes a condiciones compatibles, cubriendo el rango de operación.
2. Datos cinéticos complementarios que distingan equilibrio, película y difusión.
3. Definir parámetros compartidos y específicos por lote/ensayo, límites y modelo
   observacional antes de mirar test. Comparar complejidad LDF/HSDM por evidencia.
4. Ajustar con calibration; usar development para decisiones metodológicas. Congelar
   parámetros, preprocessing, criterios y selección de modelos antes de abrir test.
5. Evaluar columnas retenidas completas y reportar cada ensayo, incluidas discrepancias.

Si q se deriva como (V/m)(c0-c_eq), q y c_eq comparten error; no tratarlos como
mediciones independientes de concentración exacta sin justificación. Conservar
datos primarios y propagar covarianzas/errores en variables cuando corresponda.
Censura se modela por likelihood adecuada; ND no se transforma silenciosamente en cero.

Proponer separación por lote/preparación y condiciones, además de una evaluación
intradominio. Para generalización química, necesitar un sistema adicional autorizado
y un modelo aplicable; los cuatro materiales por sí solos no acreditan universalidad
en colorantes, metales y compuestos orgánicos.

## 6. Métricas, aceptación y resultados negativos

Evaluar residuales con dependencia temporal, sesgo de concentración/capacidad,
RMSE con escala y unidades, t10/t50/t90 cuando existan y cobertura/anchura predictiva.
Considerar censura de ruptura si el horizonte no cruza el umbral. Capacidad sólida
se diferencia del almacenamiento líquido y de pérdidas no adsorptivas.

Los umbrales se fijan con la precisión analítica y relevancia de diseño. Los valores
anteriores de 5% en capacidad y 10% en tiempos son **candidatos de planificación**,
no normas editoriales ni criterios ya satisfechos; justificarlos o revisarlos antes
del estudio. Reportar resultados dentro/fuera del dominio medido y sensibilidad al
modelo de error, porosidad y variación de entrada.

C08 queda apoyada solo dentro de condiciones/ensayos retenidos si errores e intervalos
cumplen el criterio previo. Queda limitada/refutada si solo funciona tras recalibrar
con test, si el balance físico no cierra o si la mejora depende de excluir ensayos
adversos. Una discrepancia puede recomendar un modelo más rico; no borrar la curva.

## 7. Relación entre artículos

El artículo EnvSoft evalúa metodología/framework y sus límites mediante E01–E05.
El artículo experimental evalúa preparación, mecanismos/desempeño de adsorbentes y
mezclas específicas. Si comparten datos, declarar qué se reutiliza y citar el estudio
correspondiente; no presentar las mismas comparaciones como dos hallazgos independientes.
Los resultados metodológicos centrales deben poder reconstruirse con el core científico
abierto y los datos autorizados incluidos en la entrega.

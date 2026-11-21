# Plan de verificación y validación

Fecha: 2026-11-18. Estado: motor LDF/HSDM implementado con referencias numéricas; los estudios ejecutados se resumen en docs/scientific_status.md.
Las pruebas actuales incluyen balances dinámicos, referencias analíticas y refinamiento. Los límites de esa evidencia y los casos aún pendientes se detallan en NUMERICAL_VERIFICATION.md.
Los umbrales siguientes son criterios de aceptación propuestos, no resultados medidos.

## Niveles de evidencia

V0: contratos y unidades. V1: ecuaciones/discretización verificadas contra soluciones
analíticas o manufacturadas. V2: validación experimental independiente dentro de un
dominio declarado. V3: calibración, UQ y diseño predictivo con incertidumbre documentada.
Cada release publica matriz con PASA/FALLA/PENDIENTE y enlaces a artefactos reproducibles.
Una comparación con FAST solo establece concordancia entre implementaciones.

## V0 — pruebas iniciales automatizadas

- Conversiones mg/L↔kg/m³, mg/g↔kg/kg, mL/min↔m³/s, mm↔m, horas↔s y °C↔K.
- Rechazar dimensiones incorrectas, bool, arrays, NaN, infinito, caudal cero,
  porosidad fuera de (0,1), T<=0 K y concentraciones negativas.
- Validar densidad seca derivada y coherencia de parámetros/modelos; q_initial>q_max
  se rechaza en Langmuir. Concentración molar no se convierte sin regla explícita.
- Tiempos de observación ordenados y no negativos; incertidumbres positivas y longitudes
  coincidentes. UUID, zona horaria, SHA-256 y versión de esquema obligatorios.
- Serialización determinista, ida/vuelta estricta, claves desconocidas rechazadas,
  tipos incorrectos rechazados y huellas sensibles al contenido.
- Instalar wheel fuera del checkout y construir sdist; el paquete no debe contener
  binarios o imágenes FAST. Ruff/mypy; matriz CI propuesta no equivale a ejecución local.

## V1 — conservación

M(t)=A integral_0^L [epsilon c+rho_b q_bar] dz.
R(t)=M(t)-M(0)-A integral_0^t [J(0,s)-J(L,s)] ds.
Escala=max(M(0), masa entrante acumulada, M_ref), con M_ref positivo elegido en
la configuración de prueba y declarado en kg; no usar un número sin unidades.
Requerir |R|/escala<=1e-6 y |R|<=atol_mass+1e-6 escala en todo punto informado.
Se propone atol_mass=1e-12 kg para las referencias de laboratorio; escalarlo para
casos pequeños y demostrar que no oculta pérdidas. Reportar también residuo absoluto.
En sistema cerrado usar V_l c+m_s q_bar; en HSDM integrar con pesos radiales exactos.
Incluir adsorción, desorción, agotamiento, entrada cero y carga inicial no nula.
No usar balance reconstruido exclusivamente desde una curva de salida interpolada.

## V1 — referencias y convergencia

| Caso | Referencia | Aceptación propuesta |
|---|---|---|
| Estado uniforme en equilibrio | Derivadas cero | Error escalado <=1e-10 |
| Batch lineal q*=Kc, LDF | Exponencial con tasa k(1+m_s K/V_l) | Error relativo L2 <=1e-5; masa <=1e-8 |
| Transporte sin adsorción, D_ax=0 | Escalón con llegada epsilon L/u | Error de llegada <=1% en malla refinada |
| Isoterma lineal, equilibrio instantáneo | Frente a t=(epsilon+rho_b K)L/u | Error de llegada <=1%, sin oscilaciones significativas |
| Difusión esférica | Serie analítica de captación, superficie fija | Captación media <=1e-3 relativa fuera de t=0 |
| Caso suave manufacturado | Fuente y fronteras derivadas independientemente | Orden espacial inicial cercano a 1, p>=0.8 |

Las dos pruebas de equilibrio instantáneo requieren implementar explícitamente ese
límite, no fijar una constante de transferencia arbitrariamente enorme.
Para transporte con discontinuidad usar errores integrales y posición del frente,
no exigir orden puntual. Para difusión/esquema centrado suave esperar orden 2 y
verificarlo en una prueba separada de convección. Refinar Nz=50,100,200,400;
Nr=10,20,40,80 para HSDM, separando refinamientos. Reducir tolerancias temporales
1e-4â†’1e-6â†’1e-8 con atol por estado; primero aislar error espacial del temporal.
Exigir cambio <0.5% en t10/t50/t90 y capacidad entre las dos mallas más finas.
Si no hay ruptura en el horizonte, marcar el indicador censurado, no inventar un tiempo.

## Estabilidad y robustez

Barrido de Pe, tasas LDF, D_s, k_f, porosidad y capacidades sobre intervalos
declarados. Casos rígidos con BDF/Radau y comparación cruzada a tolerancias estrictas.
Variar max_step y malla: no aceptar estabilidad solo porque el integrador terminó.
Pruebas no negativas: mínimo>=-atol_state; exceso superior solo si la física lo permite
(por ejemplo desorción de un sólido precargado). No imponer c<=c_in universalmente.
Examinar Jacobiano por diferencias finitas en estados suaves; verificar peso del
centro y cancelación exacta de flujos internos. Controlar no convergencia de película,
agotamiento de iteraciones, memoria y tamaños extremos con errores reproducibles.

## Identificabilidad y calibración

Usar isotermas batch y cinéticas a varios caudales/tamaños de partícula para separar
equilibrio, película y difusión. Analizar sensibilidades escaladas y rango del Jacobiano
por SVD; condición >1e8 o correlación |r|>0.95 activa revisión, no descarte automático.
Perfiles de likelihood con intervalos finitos; comparar posterior/prior para detectar
parámetros dominados por supuestos. Recuperar parámetros sintéticos con ruido y
semillas conocidas; estudiar cobertura, sesgo y multimodalidad con múltiples inicios.
No estimar simultáneamente k_f y D_s desde una sola curva sin evidencia de identificabilidad.
Tratar límites de detección con likelihood censurada; incertidumbre temporal y de entrada
puede requerir modelos de error adicionales. No rellenar valores no detectados con cero.

## V2 — validación física externa

Datos no usados en ajuste, separados por ensayo completo, material/lote y condición.
Documentar geometría, masa seca, humedad, flujo, T, pH, tamaño de partícula, blancos,
método analítico, incertidumbres y procedencia/derechos. Congelar preprocesamiento y
criterios antes de ver el conjunto de validación. Comparar residuales, sesgo y
dependencia temporal además de RMSE; no aceptar solo R².
Umbrales iniciales a acordar según incertidumbre experimental: sesgo de capacidad
<=5%, t10/t50/t90 <=10% y cobertura predictiva nominal 95% compatible con intervalo
binomial para ensayos independientes. Si la incertidumbre impide esos umbrales,
revisar el protocolo antes del estudio, no después de observar resultados.
Publicar rango validado y fallos, incluyendo casos fuera del régimen monocomponente.

## V3 — UQ, optimización y artículo

Convergencia Monte Carlo y sensibilidad respecto a tamaño de muestra; separar
incertidumbre paramétrica, observacional y de discrepancia de modelo. Semillas y
subflujos reproducibles. Optimización: restricciones con unidades, frente Pareto
repetido con varias semillas, convergencia de hipervolumen con referencia declarada,
verificación de todas las soluciones finales en malla fina y con incertidumbre.
Artículo: derivación, benchmarks independientes, datasets autorizados con DOI,
entorno exacto, versión/commit, limitaciones, costos computacionales y scripts
reproducibles. No publicar afirmación de validación antes de cerrar V1 y V2.

## Protocolo del artículo objetivo

PAPER_ENVSOFT/BENCHMARK_PROTOCOL.md amplía este plan con E01–E05, presupuestos, particiones, unidades de repetición, métricas, criterios y refutaciones por claim C01–C08. Sus valores son propuestas a congelar antes del estudio, no mandatos editoriales ni resultados. La evidencia 0.2 se conserva como referencias seleccionadas; E02/E03 completos, E04 y E05 no se infieren de pruebas unitarias o demos.

Distinguir calibración, desarrollo, escenarios de búsqueda y test independiente. Si q se deriva de c_eq, modelar la correlación de errores. La transferibilidad de kf/k_LDF entre Q/dp requiere mapping validado. La factibilidad terminal no sustituye cumplimiento de trayectoria; tres escenarios de búsqueda no certifican una probabilidad de fallo.


Actualización de datos 2026-11-19: el inventario externo y los bloqueos científicos
se documentan en `benchmarks/data_catalog/`. E04 está BLOCKED_METADATA;
ninguna curva se considera lista para validación física independiente.
Retomar las etapas 2, 3 y 4 según `CONTINUE_HERE.md`.

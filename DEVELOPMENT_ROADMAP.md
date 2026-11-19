# Roadmap de desarrollo

Fecha: 2026-11-18. Orden por dependencias y evidencia, sin prometer fechas sin equipo
y datos disponibles. La primera entrega cerró E0/E1. La continuación implementa prototipos E2–E7; sus criterios científicos completos aún no se consideran cerrados.

| Etapa | Entregables | Criterio de aceptación | Dependencia |
|---|---|---|---|
| E0: auditoría/diseño | Cinco especificaciones, inventario y hallazgos | Original intacto, límites y licencia explícitos | ZIP local y documentación pública |
| E1: fundación | Paquete tipado, unidades, esquemas, pytest, wheel/sdist, CI propuesta | Pruebas locales, tipos y lint pasan; instalación fuera del repo; sin recursos FAST | Python >=3.11 y entorno aislado |
| E2: equilibrio y batch | Langmuir/Freundlich, derivadas, batch LDF | Dominios, límites analíticos, masa y recuperación sintética pasan | Revisión de ecuaciones/unidades |
| E3: columna LDF propia | FV 1D, BDF/Radau, eventos y resultados trazables | Cierre masa, convergencia, estabilidad y benchmarks V1 | E2 y SciPy/NumPy revisados |
| E4: HSDM/película | FV radial esférico y acoplamiento conservativo | Serie analítica, convergencia radial y flujos iguales/opuestos | E3 |
| E5: calibración | Likelihood, censura, multi-inicio, perfiles | Identificabilidad demostrada y parámetros sintéticos recuperados | E3/E4 y datos autorizados |
| E6: UQ/sensibilidad | Muestreo, priors, intervalos predictivos | Convergencia y cobertura verificadas; semillas reproducibles | E5 |
| E7: diseño multiobjetivo | Ergun, costos, energía, Pareto y restricciones | Soluciones factibles re-simuladas en malla fina con UQ | E6 y bases de costos |
| E8: validación externa | Campaña independiente, métricas y dominio validado | Protocolo V2 predefinido satisfecho o limitaciones publicadas | Datos de varios ensayos |
| E9: publicación | API 1.0, licencia definitiva, DOI, artículo, paquete | Reproducción por tercero, matriz CI, release firmado y revisión de IP | E8 y titularidad resuelta |

## Hitos paralelos sin código científico complejo

- Resolver titularidad/licencia abierta y nombre de distribución antes de publicar.
- Solicitar datos de columna y batch: unidades originales, incertidumbres, réplicas,
  censura analítica, lotes, humedad, pH, T y distribución de tamaños.
- Definir protocolo independiente de validación y métricas antes de calibrar.
- Completar referencias primarias para discretización y correlaciones; las páginas
  FAST sirven de contexto, no como prueba de corrección del nuevo solver.

## FAST como integración opcional

Etapa independiente posterior a E3. Exigir instalación del usuario, versión y permisos
compatibles, documentación de entradas/salidas, aislamiento de directorios, timeout,
fallos controlados y pruebas sin tocar simulaciones activas. No es requisito para core,
publicación ni E8. No se migran binarios al repositorio.

## Política de aceptación y cambios

Cada etapa incluye código, docstrings, ejemplos reproducibles, pruebas y registro
de resultados. No avanzar por aprobación nominal si faltan las evidencias numéricas.
Mantener decisiones en arquitectura y migraciones versionadas del esquema. Solver
verificado y validación experimental son estados distintos y se publican por modelo.
LDF puede cerrarse antes que HSDM sin atribuir esa evidencia a HSDM.

## Riesgos que condicionan el calendario

No hay código fuente o datos experimentales FAST en el insumo; no se puede convertir
directamente el programa original ni validar resultados experimentales hoy.
Identificabilidad de película/difusión, rigidez numérica, significado de densidades,
Freundlich cerca de cero y uso fuera del régimen diluido necesitan ensayos explícitos.
Implementar multicomponente, regeneración, transferencia térmica o comerciales amplía
el alcance y requiere nuevas especificaciones antes de escribir algoritmos.

## Próxima acción técnica

Ampliar V1 con casos manufacturados suaves, un barrido sistemático de rigidez/transferencia y criterios de t10/t90/capacidad por malla. Después, calibración multiexperimento con perfiles de likelihood e integración de datos autorizados para V2. El prototipo funcional no sustituye esas evidencias.

## Estado 0.2 y trabajo restante

- E2: isotermas y batch LDF con solución exacta, masa y recuperación sintética.
- E3: columna LDF conservativa, trazador, refinamiento y BDF/Radau. Pendiente caso manufacturado suave y barrido extenso de rigidez.
- E4: HSDM con película, referencias esféricas, refinamiento radial y masa. Pendiente matriz amplia de regímenes y comparación externa autorizada.
- E5: ajuste de isotermas/k_LDF y SVD local. Pendientes perfiles de likelihood, multi-inicio, censura y calibración HSDM multiexperimento.
- E6: Monte Carlo con correlaciones y sensibilidad local. Pendientes cobertura, discrepancia de modelo y convergencia estadística por problema.
- E7: NSGA-II opcional, restricciones, hidráulica, costos limitados y ejemplo robusto con escenarios comunes; 11 candidatos preliminares pasan factibilidad en malla refinada. Pendientes hipervolumen/múltiples semillas, más escenarios y diseño mecánico.
- Exportación: CSV/JSON y envolvente DXF implementados. Parquet de salida/balance y CSV experimental con unidades implementados; STEP y aplicación web pendientes.
- E8/E9: requieren datos autorizados, revisión científica externa, titularidad/licencia y preparación editorial. No se han cerrado.

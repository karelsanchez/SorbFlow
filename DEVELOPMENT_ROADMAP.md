# Roadmap de desarrollo

Fecha: 2026-11-18. Orden por dependencias y evidencia, sin prometer fechas sin equipo
y datos disponibles. Esta tarea implementa exclusivamente E0 y la fundación E1.

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

Revisar MODEL_SPECIFICATION y aprobar casos analíticos de E2. Implementar primero
isotermas y batch LDF, sin saltar a HSDM ni a optimización. Incorporar datos medidos
solo con procedencia y derechos registrados. La entrega actual no inicia E2.

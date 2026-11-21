# Lista verificable de reproducibilidad y disponibilidad

Versión 0.1, 2026-11-18. Esta lista es un estándar propuesto del proyecto, no una
transcripción de requisitos editoriales no consultados. Estado: prototipo científico
local; **la reconstrucción externa del artículo completo no está demostrada**.

## 1. Evidencia disponible y pendiente

| Control | Estado actual | Cierre requerido para el artículo |
|---|---|---|
| Git independiente y código tipado/modular | Implementado, repositorio local SorbFlow | Release/tag inmutable y revisión humana identificada |
| pytest | 269 pasan en el registro 0.2 local | Suite científica completa + CI externa, sin confundir cobertura con validez |
| Instalación wheel fuera del checkout | Verificada reutilizando dependencias | Instalación desde cero y reproducción en equipo/entorno ajeno |
| Versiones/semillas/hash de entradas y opciones | Implementación parcial | Dataset, estudio, tarea, escenario y algoritmo con IDs enlazados |
| Lock de entorno | Snapshot local de versiones | Lock/artefactos por plataforma con hashes e instrucciones verificadas |
| Datos sintéticos/figuras | Ejemplos ejecutados | Scripts que reconstruyan todas las figuras/tablas citadas en el paper |
| E01 | Referencias seleccionadas | MMS, dominio/errores de decisión y suite completa |
| E02/E03/E04 | Propuestos; sin estudio confirmatorio | Resultados reales o estados NOT_TESTED/BLOCKED explícitos |
| Paralelo/reanudación | RAM de solver; arnés SMOKE separado | Cola persistente, fallos/retomas y estudio E05 medido |
| Licencia abierta | Apache-2.0 propuesta, titularidad pendiente | Concesión/avisos correctos y acceso público efectivo |
| DOI/cita/depósito | Pendiente | Archivo inmutable de software/datos y cita verificable |

La cifra de pruebas corresponde al log versionado 0.2, no a una promesa de conteo
fijo para futuras versiones. Ningún estado se marca PASSED por estar diseñado.

## 2. Contrato de un experimento reproducible

Cada estudio debe incluir: pregunta y claims, protocolo/versionado y enmiendas,
casos/modelos y dominios, particiones de datos, escenarios de búsqueda/test,
presupuesto y criterios de parada, métricas versionadas, hardware/entorno y
tratamiento de fallos. Prohibir rutas absolutas de autor como único modo de correr.
Los paquetes de datos se resuelven por manifiesto y hash, sin alterar originales.

Un task_id estable depende de: estudio, réplica, caso, configuración física,
modelo/solver, semilla, inputs/datasets, versión de código y entorno relevante.
El run_id identifica una ejecución concreta. La caché no debe reutilizar resultados
si cambia cualquier componente que pueda afectar el resultado. Documentar si el
hash de software incluye fuentes no confirmadas por commit.

Registro por tarea: estado, tiempos, recursos, intento, exit code, fuente de error,
inputs y hashes, salida completa y hashes, tolerancias, diagnóstico de masa/positividad,
semilla y versiones. Estados persistidos mediante escritura atómica o base de datos
transaccional; no dejar un resultado parcial como exitoso tras una interrupción.
Los reintentos conservan evidencia y no borran fallos. No usar una caché para ocultar
solves del presupuesto comparativo: informar costo con/sin caché.

## 3. Semillas, paralelismo y reanudación

- Separar RNG para datos, muestreo, multi-inicio, optimización y test; conservar
  correlaciones y muestras efectivas, no solo la semilla.
- Derivar subflujos de IDs, no del worker ni orden de planificación. Evitar estado RNG global.
- Fijar BLAS/OMP threads por worker y registrar hardware/recursos para comparaciones.
- Distinguir reanudar tareas, optimizador e integrador. Guardar RNG/población/archivo
  si se pretende continuar NSGA-II; guardar c/q no restaura la historia de BDF.
- Comparar serial/paralelo y fallos al 25/50/75% del trabajo; no medir solo una corrida feliz.
- Rechazar artefactos corruptos y cambios de fingerprint; no mutar la carpeta original.

El arnés `reproduce_smoke.py`, cuando se integre y verifique, solo orquesta dos
referencias/demos sintéticos y reutiliza tareas completas verificadas. No implementa
distribución multinodo ni checkpoint de solver, y no cierra E01–E05 completos.

## 4. Artefactos de artículo

Rutas propuestas: `PAPER_ENVSOFT/configs/`, `study_registry/`, `results/<study_id>/`,
`figures/`, `tables/` y `manifests/`. Datos originales en paquete externo autorizado.
Los scripts leen resultados, no contienen a mano números de conclusiones. Cada tabla
registra unidades, definición, denominador, fallos/exclusiones y precisión; cada figura
registra generador, datos y parámetros. Curvas sintéticas se identifican visualmente.

Antes de depósito, verificar:

1. Un comando documentado reconstruye las figuras/tablas sin editar rutas o código.
2. Una persona/equipo externo lo ejecuta desde un entorno nuevo y registra discrepancias.
3. El manifiesto incluye hashes de todos los datos/artefactos y acceso/licencia de cada uno.
4. Los resultados coinciden dentro de tolerancias declaradas; bitwise solo si se prueba.
5. Los claims enlazan a experimentos confirmatorios realmente ejecutados.
6. No hay FAST propietario, secretos, datos personales o datasets sin autorización.
7. El core y todos los componentes necesarios para el paper son accesibles y licenciados;
   no dependen de `sorbflow-design-pro` ni de credenciales comerciales.
8. DOI/release, referencias de software, contacto y declaración de disponibilidad son reales.

Un archivo zip local y una semilla no sustituyen estos controles.

## 5. Registro editorial y fuentes

Guardar fecha de consulta/versiones de la guía de autores al preparar el envío. La
guía específica devolvió 403 en esta revisión, por lo que faltan formatos y requisitos
particulares. Preparar una ficha de disponibilidad por transparencia, sin afirmar
que el formato sea obligatorio. La [política general de datos Elsevier](https://www.elsevier.com/en-gb/about/policies-and-standards/research-data/faq)
explica que cada revista puede tener condiciones propias; no inferirlas de otra revista.

La autoría, revisión y responsabilidad científica son humanas. Registrar el uso
de IA en investigación/código y preparar las declaraciones que correspondan conforme
a la [política general Elsevier sobre IA](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals),
revalidada al enviar. No atribuir autoría a herramientas ni fabricar figuras/datos.

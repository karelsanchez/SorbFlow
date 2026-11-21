Ubicación actual: `C:\Users\Karel\Documents\Codex\2026-11-18\empaqueta-x20\PyFAST`. El usuario trasladó el repositorio desde D:.
Las rutas D: de las inspecciones anteriores se conservan como antecedentes.

# Retomar SorbFlow: etapas 2, 3 y 4

Guía de continuación, no acta de congelación ni resultado de validación. Se revisaron
en lectura el dossier de `work/envsoft_dossier/PAPER_ENVSOFT` y los listados/README
de `D:\PyFAST\datasets_benchmark_pyfast`. No se ejecutaron motores externos, no se
alteraron originales y no se verificaron aquí licencias ni contenidos de descargas.

## Clasificar los insumos antes de utilizarlos

| Clase | Uso posible | Lo que no demuestra |
|---|---|---|
| Analíticos: batch exacto, frente sin dispersión, esfera, matriz afín | E01: exactitud de ecuaciones o sistema discreto, según la referencia | Validación experimental |
| Sintéticos: generadores con parámetros/ruido conocidos | E01/E02: recuperación, cobertura y decisiones bajo supuestos declarados | Datos observados ni validez física externa |
| Ogata–Banks/USGS | Candidato analítico de advección-dispersión | No es automáticamente la solución de una columna finita con Danckwerts: alinear dominio, IC/BC y magnitudes |
| PSDM/EPA y salidas simuladas | Comparación numérica externa tras alinear modelo, parámetros, unidades y fronteras | Observaciones experimentales; las plantillas con efluente cero no son mediciones |
| FAST original | Eventual comparación externa autorizada, con instalación/versionado y contrato I/O | El ZIP no aporta curvas de referencia; no asignar error cero ni ejecutar para llenar una tabla |
| Experimentales acuosos candidatos | E04, después de cerrar procedencia, metadatos y compatibilidad | La descarga, una figura o una extracción numérica no los hacen aptos para validación |
| RUPTURA | Antecedente y datos secundarios gaseosos según inventario | No equivale al SorbFlow acuoso monocomponente |

El README del inventario declara **cero curvas listas para validación física del
SorbFlow actual**. Esta guía no certifica ese inventario ni sus declaraciones de licencia.
Antes de reutilizar/publicar, revisar avisos, atribuciones y permisos del activo concreto.

Pendientes registrados que no deben resolverse por suposición:

- MAR2PROTECT: etiquetas de masa/volumen, identificación del tercer bloque HPLC,
  promedios, propiedades/geometría faltantes y tratamiento de LOQ/2. Tres especies
  no prueban tres corridas independientes ni ausencia de competencia.
- Banana peel/azul de metileno y quitosano: datos de autores o digitalización trazable;
  el suplemento banana no está localizado. En quitosano, alturas de cachés Word y
  texto no coinciden; no admitir esas cachés como observaciones verificadas.
- RUPTURA: el inventario describe mezcla gaseosa a 473 K y 5 bar. No convertirla
  en una curva acuosa por cambiar etiquetas/unidades.
- PSDM/EPA: separar entradas, parámetros, series simuladas y cualquier observación
  auténtica, con su procedencia. No se ha ejecutado PSDM en esta preparación.

## 2. Congelar el protocolo, sin convertir propuestas en decisiones

Fuentes: `BENCHMARK_PROTOCOL.md`, `MATHEMATICAL_FRAMEWORK.md`, `NOVELTY_MATRIX.md`,
`EXPERIMENT_REGISTRY.csv` y `CLAIMS_REGISTRY.json` del dossier.

**La congelación confirmatoria está bloqueada mientras haya umbrales o presupuestos
pendientes.** El registro aún dice `0.1-draft`, no prerregistro público, y conserva
`practical_effect_threshold=TO_BE_SET_BEFORE_CONFIRMATORY_RUN`. No cambiar ese valor
por un resultado observado ni crear un tag que afirme protocolo final sin resolverlo.

Cerrar y justificar antes del tag: dominio/modelos y casos; atol y escala de masa
por caso; normas y tiempos de referencia; criterios de ruptura/capacidad y orden;
tratamiento de fallos/censura; generadores/semillas; comparadores y ablaciones;
presupuesto de solves; réplicas y parada; análisis estadístico, multiplicidad y
beneficio mínimo `delta_min`; riesgo/confianza y regla de selección de diseños.
Separar escenarios de búsqueda y test y datos de calibración/desarrollo/test.

Guardar revisión, hashes, fecha, razones y enmiendas. Un freeze interno en Git no
es un prerregistro público. Si solo E01 está completamente definido, puede congelarse
**su subprotocolo explícito**; eso no congela E02–E05 ni cierra C03–C08. Mientras
sus propios criterios sigan pendientes, solo ejecutar pilotos etiquetados.

## 3. Ejecutar E01: verificación numérica antes de usar candidatos experimentales

1. Comenzar por referencias propias analíticas/sintéticas: batch lineal, trazador
   `Dax=0`, esfera y matriz afín. No requieren convertir descargas ambiguas en datos.
2. Para Pe finito usar MMS/referencia continua con BC compatibles. Una matriz FV
   exacta verifica integración del sistema discreto; no demuestra convergencia a la EDP.
3. Ejecutar la matriz de mallas/tolerancias congelada, separando refino axial, radial
   y temporal. Incluir precarga/desorción, límites de película y no linealidades.
4. Registrar masa, finitud, negatividad/capacidad, error de flujo/raíz, normas por
   fase, orden observado, t10/t50/t90 y capacidad corregida por almacenamiento líquido.
   No recortar estados ni inventar un cruce que no existe en el horizonte.
5. Conservar todos los casos y costos. Si cambia el signo de una restricción al
   refinar, marcar no resuelto y refinar; no aceptar factibilidad por masa sola.

Los valores del dossier —masa escalada 1e-6, batch L2 1e-5, captación esférica 1e-3,
llegada 1%, cambio entre mallas 0.5%, orden upwind 0.8— **son criterios candidatos**
hasta cerrar su definición y dominio. No son resultados generales alcanzados.
Una corrida SMOKE solo comprueba el arnés. E01 conserva evidencia parcial hasta
que la matriz confirmatoria definida esté ejecutada y evaluada.

No modificar FAST ni ejecutar otros motores como parte de este paso sin cerrar
las condiciones técnicas y de uso. E04 sigue bloqueada para los datos no aptos;
descargar nuevas fuentes no cambia por sí solo ese estado.

## 4. Producir reportes desde registros reproducibles

Cada fila de `RESULTS_TEMPLATE.csv` debe enlazar caso/réplica, run_id, configuración,
commit, métrica/unidad, valor realmente calculado, estado y artefacto. Un valor ausente
no es cero: conservar `PLANNED`, `INCONCLUSIVE`, fallo o bloqueo y su causa.
Actualizar claims solo con evidencia del experimento correspondiente.

Generar tablas/figuras mediante scripts que lean esos resultados y manifiestos:
error vs malla/tolerancia, masa absoluta/escalada, mapa de fallos/dominio, ruptura y
costo computacional. Etiquetar curvas analíticas, sintéticas, simuladas externas o
experimentales; no mezclar sus denominadores ni presentar figuras sintéticas como
validación física. Guardar fuentes, hashes, entorno, semillas y comandos efectivos.

Desde la raíz del repositorio trasladado a C:, el arnés admite, por ejemplo:

```powershell
& .\.venv\Scripts\python.exe .\PAPER_ENVSOFT\reproduce_smoke.py --repo . --output .\runs\smoke_234 --jobs 2
& .\.venv\Scripts\python.exe .\PAPER_ENVSOFT\reproduce_smoke.py --repo . --output .\runs\smoke_234 --jobs 2 --resume
```

Usar carpeta nueva en el primer comando; el segundo reutiliza tareas completas
íntegras compatibles. No restaura historia BDF ni población NSGA-II y no acredita
E05 completo. Un reporte piloto reproducible sigue siendo piloto. Antes de presentar
resultados del artículo, exigir reproducción externa, licencias/derechos resueltos y
el enlace afirmación→experimento→artefacto, sin completar celdas con números inventados.

## Consulta de consistencia, sin modificar archivos

Tras integrar el comprobador en `benchmarks/data_catalog/`:

```powershell
& .\.venv\Scripts\python.exe .\benchmarks\data_catalog\check_benchmark_readiness.py --repo .
& .\.venv\Scripts\python.exe .\benchmarks\data_catalog\check_benchmark_readiness.py --repo . --require-confirmatory
```

Emite JSON por stdout. Exit 0: informe normal, aunque sea `draft`/`blocked`.
Con `--require-confirmatory`, exit 2: protocolo draft/umbral pendiente o ningún dato
declarado apto para validación física. Exit 1: archivos o estructuras inconsistentes.
Valida IDs, rutas relativas, conteos, booleanos y referencias C/E. No inspecciona
descargas ni deduce readiness por presencia; no verifica licencias ni valida modelos.
`declared_requirements_met` significa coherencia declarada, no certificación científica
ni prueba de congelación en Git. No sustituye el checklist de congelación E01.

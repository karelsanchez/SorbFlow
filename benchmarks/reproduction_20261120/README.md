# Captura de los arneses de benchmark

`execution_kits.zip` conserva los scripts y pruebas originales de las campañas
E01 suplementaria, E02 analítica y E03 sintética, más su enmienda de refinamiento.
`manifest.json` identifica hashes del archivo y de cada fuente. No incluye
resultados grandes, datos experimentales ni componentes FAST. Los arneses se
conservan como captura de investigación; no son API pública del paquete.

## Reproducción en una carpeta nueva

La disposición de trabajo de estos arneses requiere un directorio padre con el
checkout llamado `PyFAST/` y las salidas en el hermano `outputs/`. Esta limitación
es explícita; no extraer encima de campañas congeladas existentes. El entorno de
referencia fue Windows, Python 3.11.2; no se ha verificado esta captura en todos
los sistemas o versiones de dependencias.

1. En una carpeta nueva, obtener el checkout con nombre `PyFAST` y preparar su
   entorno con el extra `dev,optimize`. Conservar las versiones efectivamente
   utilizadas; la coincidencia binaria entre versiones no se garantiza.
2. Extraer `execution_kits.zip` en el directorio padre de `PyFAST`, verificando
   previamente su hash. Esto crea los directorios `outputs/PyFAST_E.../code` y
   sus insumos sintéticos, sin protocolos congelados ni resultados previos.
3. Desde ese directorio padre ejecutar las siguientes líneas, en orden dentro
   de cada campaña. `freeze` registra código, entorno y criterios antes de los
   cálculos. No repetir `freeze` sobre un protocolo existente.

```powershell
$benchPython = '.\PyFAST\.venv\Scripts\python.exe'
& $benchPython -I -B outputs\PyFAST_E01_CLOSURE_20261120\code\run.py freeze
& $benchPython -I -B outputs\PyFAST_E01_CLOSURE_20261120\code\run.py run
& $benchPython -I -B outputs\PyFAST_E02_COVERAGE_20261120\code\coverage_run.py freeze
& $benchPython -I -B outputs\PyFAST_E02_COVERAGE_20261120\code\coverage_run.py run
& $benchPython -I -B outputs\PyFAST_E03_BENCHMARK_20261120\code\run_e03.py freeze
& $benchPython -I -B outputs\PyFAST_E03_BENCHMARK_20261120\code\run_e03.py run
# Refinamiento: requiere la campaña E03 anterior terminada.
& $benchPython -I -B outputs\PyFAST_E03_REFINEMENT_20261120\code\refine.py freeze
& $benchPython -I -B outputs\PyFAST_E03_REFINEMENT_20261120\code\refine.py run
```

E01 usa un worker, E02 dos y E03 uno. Para ejecutar en paralelo deben respetarse
los presupuestos y recursos totales del equipo. Los datos sintéticos y semillas
se guardan por los scripts; ningún bucle numérico consulta modelos de lenguaje.
El caso C-B no se incluye porque depende de curvas externas y metadatos de una
aplicación concreta; su resumen y procedencia se conservan en la auditoría.

La captura fue comprobada mediante hashes y análisis sintáctico. Las campañas
originales sí se ejecutaron; no se ha repetido toda la campaña desde este ZIP
en un equipo nuevo. Véanse los [resultados y límites](../../docs/benchmark_results.md).

# Galería de ejemplos

Todos los ejemplos están en la carpeta `examples/` del repositorio y usan datos
sintéticos listos para ejecutar. Las carpetas de salida deben ser nuevas.

## Configuraciones listas para la terminal

| Archivo | Caso | Comando |
|---|---|---|
| `examples/batch_ldf.json` | Batch con isoterma lineal y cinética LDF | `sorbflow batch examples/batch_ldf.json --output runs/batch` |
| `examples/column_ldf.json` | Columna Langmuir/LDF | `sorbflow column examples/column_ldf.json --output runs/col_ldf --cells 40` |
| `examples/column_hsdm.json` | Columna Langmuir/HSDM con perfiles radiales | `sorbflow column examples/column_hsdm.json --output runs/col_hsdm --cells 40 --radial-cells 12` |

## Scripts de Python

| Archivo | Qué muestra | Comando |
|---|---|---|
| `examples/configuration.py` | Crear, guardar y releer una configuración tipada | `python examples/configuration.py` |
| `examples/run_ldf.py` | Curva de ruptura LDF con exportación trazable | `python examples/run_ldf.py --output runs/curva` |
| `examples/scientific_demo.py` | Flujo completo: ajuste → LDF/HSDM → incertidumbre → hidráulica → DXF e informe | `python examples/scientific_demo.py --output runs/demo` |
| `examples/robust_column_design.py` | Diseño robusto de columna con NSGA-II y escenarios comunes (extra `optimize`) | `python examples/robust_column_design.py --output runs/diseno` |
| `examples/profile_batch.py` | Perfiles de verosimilitud con objetivo batch compartido | `python examples/profile_batch.py --output runs/perfiles` |
| `examples/numerical_benchmarks.py` | Referencias numéricas independientes para verificación | `python examples/numerical_benchmarks.py --output runs/referencias` |
| `examples/linear_matrix_reference.py` | Referencia matricial exacta del sistema discreto lineal | `python examples/linear_matrix_reference.py` |
| `examples/e02_execution_kit.py` | Kit reanudable de calibración por perfiles sobre una tabla de escenarios (siete conjuntos) | `python examples/e02_execution_kit.py --table ESCENARIOS.json --output runs/e02` |

Más detalle en los [tutoriales](tutorials.md) y en [configuraciones](configurations.md).

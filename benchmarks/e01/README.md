# E01-A: ejecución de referencias numéricas acotadas

El protocolo ejecutable es `protocol.json`; la formulación y los límites están en
`PAPER_ENVSOFT/E01_SUBPROTOCOL.md`. No se necesitan FAST ni datos externos.

```powershell
& .\.venv\Scripts\python.exe benchmarks\e01\run.py --protocol benchmarks\e01\protocol.json --output runs\e01_a_nueva
& .\.venv\Scripts\python.exe -m pytest tests\test_e01_protocol.py -q
```

La carpeta de salida debe ser nueva. El arnés conserva el protocolo exacto,
resultados por caso, normas/umbrales/decisiones, trayectorias, versiones, estado Git
y SHA-256 de las fuentes científicas y del arnés antes/después. La GUI queda fuera
del dominio científico de este estudio. Los errores de una corrida permanecen en
su informe; nunca se eliminan para obtener un agregado favorable.

## Evidencia observada el 2026-11-19

Corrida local `runs/e01_a_20261119_01`, resultado `PASS_SCOPED_E01_A`: 40
integraciones y un agregado, 219 comprobaciones, cero fallos. Duración de los
casos: 10.025 s, con otros workers activos sobre GUI/documentación; no es un
benchmark comparativo de rendimiento. Se generaron y revisaron dos figuras.

| Cantidad | Observación |
|---|---:|
| Máximo error normalizado de trazador frente a cadena FV exacta | 7.832e-8 |
| Error relativo t50, N=400 | 8.329e-4 |
| Esfera Nr=80: error relativo máximo de carga media | 7.477e-4 |
| Órdenes radiales observados, refinamientos a Nr40 / Nr80 | 2.0366 / 2.0085 |
| Matriz LDF, máximo error c, BDF / Radau (kg/m³) | 1.173e-12 / 3.055e-14 |
| Matriz LDF, máximo error q, BDF / Radau (kg/kg) | 1.194e-14 / 1.153e-15 |
| Pruebas unitarias del protocolo/arnés | 13 aprobadas |

Protocolo congelado antes de ejecución en commit
`e60dba96c911330434e88484663c242622a7e07a`, SHA-256
`a62addb00e66e283ff413b8169f0fbd910dc6789aa7509cb2e207446fa1992c6`.
El árbol de trabajo tenía cambios concurrentes: no se presenta como limpio.
SHA-256 combinado de fuentes registradas, idéntico antes y después:
`abeca453c6fb193741fa769d911c79b33eb9ccb4886d8903a666d92ed469db06`.
SHA-256 del arnés ejecutado:
`84dc86a24c1f8ba2a93eed5f4aeda6967e81a576187602e1b8026e738b576a3c`.

Los resultados detallados y hashes de artefactos están en `summary.json`,
`metrics.csv`, `trajectories.csv` y `manifest.json` de esa corrida. Las carpetas
`runs/` se excluyen de Git; una distribución de evidencia debe conservar esos
archivos explícitamente.

Este resultado no cierra E01 general ni demuestra física experimental. La matriz
verifica el sistema discreto; la esfera usa superficie prescrita sin película ni
columna HSDM acoplada. El caso trazador estudia Dax=0 y la convergencia L1 del
frente; no acredita convergencia general a Pe finito, ni t10/t90/capacidad dentro
del criterio de E01 general. Los ejemplos previos informaron la selección del
protocolo: no es una confirmación ciega independiente del desarrollo.

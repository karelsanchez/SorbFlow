# Rendimiento

SorbFlow resuelve columnas de alta resolución en minutos en un equipo de escritorio.
Las cifras siguientes son mediciones del 20 de noviembre de 2026 en el equipo de
desarrollo (Windows, Python 3.11), con protocolos fijados antes de medir.

| Capacidad | Configuración | Resultado |
|---|---|---|
| Jacobiano analítico | Columna LDF, 620 celdas, dos réplicas por método | Mediana 7,77 s frente a 17,09 s con diferencias finitas: **2,2 veces más rápido** |
| Modo streaming | Misma columna, Jacobiano analítico | Memoria privada máxima 956,7 MB frente a 1.632,9 MB (**−41 %**); curvas de salida idénticas |
| Alta resolución | 7.440 celdas axiales, 4.767 instantes de salida | **≤262,4 s** por simulación y 2,02 GB de memoria máxima |
| Campaña de calibración | Columna con datos publicados | 48 simulaciones completas en 276,7 s (≈5,8 s cada una) |
| Estudio de diseño robusto | NSGA-II con escenarios comunes | 1.081 simulaciones completas |

## Cómo aprovecharlo

```python
from sorbflow.solvers import SolverOptions

options = SolverOptions(
    axial_cells=400,
    jacobian="analytic",   # columna LDF con isoterma Langmuir o lineal
    history="streaming",   # menor memoria con la misma salida
)
```

- Empiece con mallas moderadas y refine hasta que el indicador que le interesa
  (tiempo de ruptura, capacidad útil) deje de cambiar.
- Para muchos casos, ejecute procesos en paralelo: cada simulación es independiente.
- La interfaz web está pensada para casos interactivos; los estudios grandes se
  ejecutan con la API o con el comando `sorbflow`.

## Evidencia

Los informes y datos de estas mediciones se conservan fuera del paquete, en las
carpetas de entrega históricas del proyecto (nombre anterior PyFAST):
`outputs/PyFAST_ANALYTIC_JACOBIAN_20261120/INFORME.md`,
`outputs/PyFAST_STREAMING_20261120/INFORME.md` y, en este repositorio,
`audit/benchmarks_20261120/summary.json`. Los tiempos varían con el hardware y la
configuración elegida.

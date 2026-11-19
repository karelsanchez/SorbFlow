# Demostración sintética de perfil batch

Desde la raíz del repositorio, con el Python del proyecto:

```powershell
& .\.venv\Scripts\python.exe examples/profile_batch.py --output runs/perfil_batch_nuevo
```

El destino debe ser nuevo. Se crean dos series sintéticas con verdad batch lineal
analítica, semilla fija y ruido Gaussiano de sigma conocida. No son datos de los
cuatro materiales ni de las fuentes descargadas. No se recortan observaciones.

El ejemplo perfila K mientras reoptimiza k_LDF mediante dos inicios y tres puntos
de malla. Usa el [solver batch mediante este objetivo](batch_objective.md) y
[perfiles con sigma conocida](profile_likelihood.md). Conserva datos, hashes,
configuraciones, límites, opciones, semilla y versiones. Distingue llamadas del
callback de solves físicos: dos experimentos implican dos solves por callback.

La ejecución de desarrollo produjo estado COMPLETE con 213 callbacks y 426 solves;
baseline K≈0.51624 m³/kg y k≈0.019253 s⁻¹, frente a verdad K=0.5 y k=0.02. Solo
K=0.5 de la malla [0.4,0.5,0.6] fue aceptado. No interpretar esa lista como intervalo
continuo, anchura cero, cobertura demostrada ni identificabilidad global.

No ejecuta el estudio [E02-A](inverse_study_plan.md), ni estima sigma desconocida,
censura, múltiples temperaturas o competencia entre contaminantes. El presupuesto
global es 1200 callbacks; los fallos y truncamientos deben conservarse.

[Índice](index.md) · [Estado científico](scientific_status.md)

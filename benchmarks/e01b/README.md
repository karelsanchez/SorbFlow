# E01-B: referencia continua ADE a Pe finito

La referencia resuelve el trazador sin adsorción con entrada Danckwerts y salida
Neumann mediante modos de Sturm–Liouville independientes del solver FV. Usa
promedios analíticos de celda para perfiles y valor continuo de frontera para el
flujo de salida. La derivación, criterios y exclusiones están en
`PAPER_ENVSOFT/E01B_SUBPROTOCOL.md`; el JSON ejecutable es `protocol.json`.

```powershell
& .\.venv\Scripts\python.exe benchmarks\e01b\run.py --protocol benchmarks\e01b\protocol.json --output runs\e01_b_nueva
& .\.venv\Scripts\python.exe -m pytest tests\test_e01b_reference.py -q
```

La salida debe ser nueva. Contiene protocolo exacto, JSON de resumen/manifiesto,
CSV de normas/decisiones y trayectorias, y figura si matplotlib está disponible.
Los hashes de core/referencia/arnés se registran antes y después; GUI y calibración
quedan fuera del dominio científico y de esos hashes. Nunca se modifica el solver.

## Evidencia observada el 2026-11-19

Corrida `runs/e01_b_20261119_01`: `PASS_SCOPED_E01_B`. Se ejecutaron 16
integraciones FV (Pe=2/10, N=25/50/100/200, BDF/Radau), dos grupos de comprobaciones
de referencia y un agregado: 138 criterios, cero fallos, fuentes estables. Se
generó y revisó visualmente la figura de convergencia. CPU 7.391 s y duración
7.388 s: mediciones locales con otros workers activos, sin valor de comparación de
rendimiento. El árbol de trabajo incluía cambios concurrentes y no se afirma limpio.

| Error en N200, normalizado por concentración de entrada | Pe=2 | Pe=10 |
|---|---:|---:|
| RMS de perfiles, BDF | 3.27444e-4 | 1.45685e-3 |
| L-infinito de perfiles, BDF | 9.99166e-4 | 4.88971e-3 |
| L-infinito de salida, BDF | 5.86595e-4 | 3.71134e-3 |
| RMS de perfiles, Radau | 3.27442e-4 | 1.45685e-3 |
| L-infinito de salida, Radau | 5.86595e-4 | 3.71134e-3 |

Los dos últimos órdenes de perfil/salida, ambos métodos y ambos Pe, estuvieron
entre 0.97648 y 1.01426, compatibles con el upwind de primer orden en este dominio.
La diferencia computada entre 64 y 128 modos fue cero a precisión flotante en la
malla de comparación: no es una prueba de error exactamente cero ni una cota
universal. Máximo residuo de proyección/cuadratura: 1.631e-15; de identidad de
masa continua: 3.553e-15. Las pruebas unitarias también contrastan promedios con
cuadratura, ortogonalidad, condiciones Robin, EDP mediante diferencias finitas,
dominio de entrada y conservación de fallos.

Protocolo congelado antes de comparaciones FV en commit
`3155b72f2d39e6dec40f4cf0bb46c9807673d49f`, SHA-256
`e189b9cfee6c4b7e97b109e6c5081d366fe93398e45fae062038beebe381bdf1`.
SHA-256 combinado de fuentes, idéntico antes/después:
`8d197a41173950ecc5e81ad63e8cd4c1c67d48067e71a42daa641846e8045532`.
Los hashes individuales de referencia/arnés y artefactos están en el manifiesto.
Las carpetas `runs/` se excluyen de Git; deben conservarse explícitamente en el
paquete de evidencia.

Este resultado amplía la verificación continua de E01 a Pe=2/10 para trazador;
E01 general sigue parcial. No acredita HSDM acoplado/no lineal, identificabilidad,
UQ, t10/t90/capacidad convergidos, límites singulares de Pe, escalabilidad ni
validación experimental. No usa FAST ni datos externos.

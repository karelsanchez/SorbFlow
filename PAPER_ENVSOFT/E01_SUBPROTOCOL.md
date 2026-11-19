# E01-A: subprotocolo prospectivo de referencias existentes

Preparado el 2026-11-19. Definiciones ejecutables: `benchmarks/e01/protocol.json`,
versión 1.0. El archivo se guarda y se calcula su SHA-256 antes de ejecutar el arnés.
Cada corrida conserva exactamente esos bytes y su hash; una enmienda exige otra
versión y otra ejecución, sin relajar un criterio después de observar un fallo.

**Alcance limitado:** E01-A no congela ni cierra E01 completo, no establece validación
experimental y no prueba identificabilidad, cobertura predictiva, diseño robusto o
escalabilidad. Los ejemplos/tests previos ya informaron la elección de referencias y
tolerancias: no se presenta este estudio como ciego o independiente del desarrollo.
Ningún dato descargado ni motor externo entra en esta ejecución.

## Casos, hipótesis y cantidades de referencia

| Familia | Hipótesis y referencia | Diseño y aceptación predeclarada |
|---|---|---|
| Batch lineal cerrado | q*=Kc; mismo s=k(Kc-q) en ambas fases. c_eq=(V c0+m q0)/(V+mK), c(t)=c_eq+(c0-c_eq)exp[-k(1+mK/V)t], q por masa | Adsorción, desorción, equilibrio y vacío; BDF/Radau; tres tolerancias decrecientes. RMS de error/escala <=1e-3 en toda corrida y <=1e-5 en la más estricta. Transitorios: error final/coarse <=0.1; diferencia máxima entre métodos/escala <=1e-5 |
| Trazador, Dax=0 | Lecho inicialmente limpio, K=0, entrada constante. Cadena FV exacta: c_out/c_in=P(N,Nt/tau), tau=epsilon V_b/Q. Frente PDE: H(t-tau) | N=25/50/100/200/400 y dos métodos. Error L∞ frente a cadena FV <=1e-6. Error L1 normalizado del frente disminuye por factor <=0.8 al refinar. Error relativo t50 final <=1% |
| Esfera con superficie Dirichlet | q inicial cero; q(R,t)=q_surface constante, sin película ni columna. Captación media normalizada =1-6/pi² sum exp(-n²pi²Fo)/n², Fo=Ds*t/R² | Nr=10/20/40/80 y Fo=0.01/0.03/0.1/0.3/1; BDF, rtol=1e-10. Error relativo máximo de carga media en Nr80 <=1e-3; dos últimos órdenes observados >=1.8. Truncación de serie acotada por 6 exp(-pi²N²Fo_min)/(pi²N) <=1e-12 |
| Matriz afín LDF | Malla axial fija, isoterma lineal, dispersión y estados iniciales no nulos. Matriz construida independientemente y estado constante aumentado para el influente | N=4, BDF/Radau, rtol=1e-10. Máximo error c<=2e-10 kg/m³ y q<=2e-12 kg/kg. Verifica el sistema discreto, no convergencia espacial de la EDP |

Los parámetros SI, escalas, tolerancias absolutas y estados iniciales completos están
en el JSON. Las escalas batch son 0.01 kg/m³ y 0.01 kg/kg, evitando dividir por una
referencia cero. RMS significa sqrt(mean(error²))/escala. La norma L1 de trazador es
integral de |c_out/c_in-H(t-tau)| dt /tau sobre [0,3tau]. No se exige orden puntual
uno en un frente discontinuo: upwind introduce difusión numérica. Se informan t10 y
t90 por interpolación de la malla de observación, sin acreditar convergencia de esos
tiempos ni el criterio general de cambio 0.5% de E01 completo.

En batch/columna, residuo de masa absoluto <=1e-12 kg y escalado <=1e-6, con
M_ref=1e-12 kg. Se usan diagnósticos de estados aceptados y salidas del solver.
Negatividad solo dentro de diez atol por fase; no se recortan resultados.
En la esfera se comprueba además el telescopado instantáneo del operador radial en
los estados muestreados: pesos* dq/dt=3j/(rho_p R). Se escala por Ds*q_surface/R² y
se exige error <=1e-10. Esto no es una prueba de masa de una columna HSDM con película.

Los criterios precisos elegidos son suficientemente más estrictos que el orden de
las diferencias físicas que este estudio limitado pretende resolver, y compatibles
con las referencias anteriores; no son garantías universales ni normas editoriales.
Mallas gruesas de esfera permiten medir convergencia: su precisión absoluta no se
confunde con el criterio de exactitud de la malla más fina.

## Ejecución y trazabilidad

Desde la raíz del repositorio, con su Python local:

```powershell
& .\.venv\Scripts\python.exe benchmarks\e01\run.py --protocol benchmarks\e01\protocol.json --output runs\e01_a_nueva
```

`--output` debe ser nuevo y quedar fuera de fuentes/benchmark/datos originales.
Se generan `protocol.json`, `summary.json`, `metrics.csv`, `trajectories.csv`,
`manifest.json` y figuras si matplotlib está disponible. El manifiesto conserva
versiones, origen de importación, revisión Git, hashes de fuentes relevantes/arnés,
tiempos y hashes de artefactos. Los fallos se guardan por caso y no se descartan;
los agregados que no puedan evaluarse quedan inconclusos. Salida 0 significa que
pasaron los criterios E01-A, no E01 entero; salida 1 corresponde a fallo/inconclusión
de ejecución y salida 2 a protocolo/entrada inválida o carpeta ya existente.

Quedan fuera: MMS continuo, Pe finito continuo, equilibrio instantáneo reducido,
no linealidad completa HSDM/película, mapa general de rigidez, t10/t90/capacidad
convergidos y toda validación experimental. Esas brechas permanecen en el protocolo
general y no se cierran por pasar E01-A.

# E01-B: trazador continuo con dispersión finita

Protocolo prospectivo acotado, versión 1.0, preparado el 2026-11-19. El JSON
`benchmarks/e01b/protocol.json` se congela, se calcula su SHA-256 y se registra en
un commit antes de ejecutar comparaciones FV. Los ejemplos/E01-A informaron las
tolerancias; este ejercicio no constituye una validación ciega independiente del
desarrollo. Una comprobación fallida se conserva sin relajar umbrales post hoc.

## Formulación y referencia independiente

Trazador monocomponente sin adsorción: K=0, q inicial cero, c inicial cero,
geometría fija y flujo/entrada constantes positivos. Velocidad intersticial
v=Q/(epsilon A), tau=L/v, Pe=vL/D. Para t>0:

    c_t = D c_zz - v c_z
    v c(0,t) - D c_z(0,t) = v c_in
    c_z(L,t) = 0

El salto de entrada en t=0 es incompatible en la esquina con el estado inicial;
no se compara allí una serie truncada. Se usan x=z/L, theta=t/tau y C=c/c_in.
Con h=Pe/2, C=1+exp(hx)U, resulta U_theta=U_xx/Pe-Pe U/4,
U_x(0)=hU(0), U_x(1)=-hU(1). El problema autoadjunto es positivo: su forma
cuadrática integra |U_x|²+h[U(0)²+U(1)²], por lo que no hay modo cero ni
modos hiperbólicos que agregar para h>0.

Los modos son f_n=cos(k_n x)+(h/k_n)sin(k_n x), con
(h²-k²)sin(k)+2hk cos(k)=0. Para evitar el cero espurio de esta ecuación,
se resuelve k-2 atan(h/k)-n*pi=0: es estrictamente creciente y tiene exactamente
una raíz en (n*pi,(n+1)*pi), n=0,1,... . La serie es

    C(x,theta)=1+exp(hx) sum b_n f_n(x) exp[-(k_n²/Pe+Pe/4)theta]
    b_n= -[2h/(h²+k_n²)] / integral_0^1 f_n² dx

La integral del numerador proviene de proyectar -exp(-hx); se contrasta con
cuadratura adaptativa independiente. La norma posee integral trigonométrica
cerrada y también se contrasta mediante cuadratura. Los modos y sus derivadas
satisfacen ambas condiciones de frontera; se comprueba su residuo normalizado.
No se usan RHS, matrices ni patrones de Jacobiano del solver para esta referencia.

La integración analítica de exp(hx)f_n sobre cada celda se evalúa con exponenciales
complejas. Se comparan **promedios de celda** frente a estados FV, no valores en
centros. El flujo continuo de salida es v*c(L,t); por tanto se compara por separado
C(1,theta) con el último estado FV, que el esquema usa como concentración de
salida. Esa comparación es de convergencia de la aproximación de flujo de salida,
no una afirmación de identidad entre promedio de última celda y valor puntual.

## Diseño y criterios fijados

Pe=2 y 10; N=25/50/100/200; BDF y Radau; theta=0.1..3 en 60 puntos uniformes.
El solver empieza en t=0, pero las normas de referencia excluyen ese instante.
Los parámetros SI y todas las tolerancias están en el JSON.

- Se comparan 64 y 128 modos en todos los puntos/celdas y salida: L-infinito
  normalizado <=1e-11. Es una comprobación operacional de truncación, no una
  cota rigurosa universal de la cola. Fallarla invalida la referencia del caso.
- Residuos modales de frontera <=1e-10 y diferencia de proyección/norma frente a
  quad <=1e-11, escalada por max(1,|valor|). Identidad continua de masa
  d(integral C dx)/dtheta = 1-C(1,theta), residuo <=1e-10. C entre 0 y 1 con
  margen 1e-11; estado theta=30 cercano a equilibrio con error <=1e-10.
- Perfil: RMS sobre tiempos y celdas y L-infinito, ambos divididos por c_in.
  En N200 RMS<=1%, L-infinito<=2%. Salida: L-infinito/c_in<=2%.
- RMS del perfil y L-infinito de salida deben disminuir en cada refinamiento
  por factor <=0.75; los dos últimos órdenes log(e_N/e_2N)/log(2)>=0.7.
  Upwind es de primer orden: este margen permite régimen asintótico imperfecto,
  y puede refutarse con las mallas fijadas. No se exige orden dos ni precisión
  puntual uniforme en t=0.
- Diferencia BDF/Radau normalizada <=1e-6 en perfiles/salida con cada malla.
  La tolerancia temporal se fija varios órdenes por debajo del error espacial
  permitido para no confundir convergencia temporal y espacial.
- Masa del solver: residuo absoluto<=1e-12 kg y escalado<=1e-6; negatividad
  únicamente dentro de diez atol. Los diagnósticos incluyen estados aceptados.

Los umbrales espaciales son criterios operacionales para este subestudio (máximo
1–2% de la escala de entrada), no una norma editorial ni tolerancia universal de
diseño. La referencia se verifica por identidades independientes antes de
interpretar los errores FV. Fallos del solver/referencia se conservan y los
agregados no evaluables quedan inconclusos. No se seleccionan casos post hoc.

## Ejecución, trazabilidad y límites

```powershell
& .\.venv\Scripts\python.exe benchmarks\e01b\run.py --protocol benchmarks\e01b\protocol.json --output runs\e01_b_nueva
& .\.venv\Scripts\python.exe -m pytest tests\test_e01b_reference.py -q
```

Salida nueva: JSON, CSV, figuras si matplotlib disponible, protocolo exacto,
versiones, hash de referencia/arnés/core antes y después, estado Git, duración y
fallos por caso. Los tiempos locales bajo concurrencia no son comparaciones de
rendimiento. Salida 0: todos los criterios E01-B; 1: fallo/inconclusión; 2: entrada
inválida. Nunca se sobrescribe una corrida existente.

E01 general permanece parcial. No se verifica aquí HSDM acoplado/no lineal,
identificabilidad, incertidumbre, t10/t90/capacidad convergidos, límites Pe->0 o
Pe->infinito, escalabilidad ni validación experimental. No se usa FAST.

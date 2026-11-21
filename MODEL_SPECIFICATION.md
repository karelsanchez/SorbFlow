# Especificación matemática — SorbFlow

Estado: formulación implementada para batch LDF y columna LDF/HSDM, con verificación numérica E01. Fecha: 2026-11-18; actualizado 2026-11-20.
Ecuaciones formuladas desde balances físicos; no transcripción de código FAST.
Resumen con ecuaciones renderizadas y figuras en [modelos y ecuaciones](docs/models.md).

## Hipótesis y unidades

Lecho cilíndrico uniforme, especie diluida acuosa, líquido incompresible,
temperatura constante, partículas esféricas monodispersas, sin reacción química,
sin expansión ni gradientes radiales de columna. Radio de partícula R, eje 0<z<L.
No se modelan inicialmente gas, calor, pH, especiación ni competencia multisoluto.
La densidad de partícula incluye el volumen interno, pero la masa es adsorbente seco.
HSDM representa almacenamiento adsorbido; no agrega almacenamiento acuoso intrapartícula.
Si este no es despreciable, se requiere un modelo poroso distinto para evitar doble conteo.

| Símbolo | Definición | SI |
|---|---|---|
| c, c_s, c_in | Concentración acuosa por volumen líquido | kg soluto/m³ líquido |
| q, q_bar | Carga por masa seca de adsorbente | kg soluto/kg adsorbente seco |
| epsilon | Porosidad interpartícula | 1 |
| rho_p | Masa seca/volumen aparente de partícula | kg/m³ partícula |
| rho_b=(1-epsilon)rho_p | Masa seca/volumen de lecho | kg/m³ lecho |
| Q, A, u=Q/A, v=u/epsilon | Caudal, área, velocidad superficial e intersticial | m³/s, m², m/s, m/s |
| D_ax, D_s | Dispersión axial, difusión superficial | m²/s |
| k_f, k_LDF | Transferencia de película, tasa LDF efectiva | m/s, 1/s |
| a_s=3(1-epsilon)/R | Área externa por volumen de lecho | 1/m |
| T | Temperatura absoluta | K |

Usar masa de soluto consistente en todas las fases. `mg/g` de carga equivale a
1e-3 kg/kg; `mg/L` equivale a 1e-3 kg/m³. Aunque q es dimensionalmente una razón
de masas, su significado no se intercambia con epsilon. Concentraciones molares
requieren masa molar de la especie explícita. No inferir ppm acuoso como mg/L.
No convertir base húmeda/seca sin contenido de humedad medido.

## Balance en columna

Definir flujo superficial J=u c - epsilon D_ax dc/dz [kg/(m² s)].

    epsilon dc/dt + rho_b dq_bar/dt = -dJ/dz

Equivalentemente, epsilon dc/dt + u dc/dz = epsilon D_ax d²c/dz²
- rho_b dq_bar/dt para propiedades constantes. La misma fuente sólida debe
reutilizarse con signo contrario en la fase líquida; no evaluarla dos veces con
interpolaciones diferentes. En HSDM rho_b dq_bar/dt = a_s k_f(c-c_s).

Frontera de Danckwerts en z=0, D_ax>0:

    u c(0,t) - epsilon D_ax dc/dz(0,t) = u c_in(t)
    dc/dz(L,t) = 0

Con D_ax=0: c(0,t)=c_in(t); salida convectiva sin imponer otra condición.
Estado inicial c(z,0)=c_initial(z)>=0; q_bar(z,0)>=0 o q(z,r,0)>=0.
Puede existir carga inicial fuera del equilibrio y desorción. Especificar escalón
en t=0+ sin forzar compatibilidad artificial con el interior en t=0.
Primera versión de esquemas: valores iniciales uniformes, entrada y Q constantes.
Entradas por tramos serán una ampliación con reinicio del integrador en discontinuidades.

## Equilibrio y cinética

Langmuir: q*(c)=q_max b c/(1+b c), con q_max [kg/kg] y b [m³/kg soluto].
Dominio c>=0, q_max>0, b>0. La temperatura de calibración debe acompañar el modelo.

Freundlich normalizado: q*(c)=q_ref (c/c_ref)^alpha.
q_ref>0 [kg/kg], c_ref>0 [kg/m³], alpha>0. No imponer universalmente alpha<1:
su validez se delimita por el intervalo experimental. q*(0)=0; la derivada es
singular en cero si alpha<1, por lo que el futuro Jacobiano necesita tratamiento
documentado. No regularizar sin registrar el cambio físico. Convención FAST `n`
y posible `1/n` deben verificarse antes de importar parámetros.
K_F dimensional tradicional = q_ref/c_ref^alpha; no transportarlo como un float
independiente de las unidades. Sips, competitivas e IAST quedan para etapas posteriores.

LDF efectiva inicial:

    dq_bar/dt = k_LDF [q*(c)-q_bar]

Incluye resistencia global empírica; no sumar película aparte ni identificar
k_LDF con k_f. La aproximación k_LDF≈15 D_s/R² se limita a hipótesis de difusión
en esfera y equilibrio apropiadas; no es una identidad general para isotermas no lineales.

HSDM:

    dq/dt = D_s/r² d/dr(r² dq/dr), 0<r<R
    dq/dr(0)=0
    rho_p D_s dq/dr(R)=k_f[c-c_s]
    q(R)=q*(c_s)
    q_bar=3/R³ integral_0^R q(r)r² dr

El signo en superficie representa flujo positivo hacia la partícula cuando c>c_s.
Resolver c_s>=0 y el flujo acoplado conservativamente, evitando invertir una isoterma
fuera de su dominio. En el centro usar volumen esférico finito, nunca dividir por cero.
D_s>0, k_f>0; límites de resistencia nula se tratan con modelos reducidos explícitos.

Batch de referencia, líquido perfectamente mezclado V_l y masa seca m_s:

    V_l dc/dt = -m_s dq_bar/dt
    c(0)=c_initial, q_bar(0)=q_initial

Sin entrada ni salida. El balance debe conservar V_l c + m_s q_bar.

## Magnitudes derivadas y diseño futuro

V_b=AL, m_s=rho_b V_b, EBCT=V_b/Q, tiempo de residencia líquido=epsilon EBCT,
volúmenes de lecho tratados=Qt/V_b. No confundir estos tiempos o volúmenes.
Pe=v L/D_ax; tau_LDF=1/k_LDF; tau_s=R²/D_s. Todo Biot modificado debe llevar su
definición completa y capacidad diferencial; no importar Bi o St de FAST sin conversión.

Pérdida de carga: Ergun con u superficial, implementado en `sorbflow.design.hydraulics`,
DeltaP/L=150 mu(1-epsilon)² u/(epsilon³ d_p²)
+1.75 rho_l(1-epsilon)u|u|/(epsilon³ d_p).
Requiere viscosidad y densidad del líquido; el usuario verifica el régimen de flujo.
Objetivos futuros: tiempo de servicio a umbral declarado, capacidad útil, costo
con moneda/año base y energía integral Q DeltaP dt. Restricciones: concentración
máxima, pérdida de carga, geometría y disponibilidad de material. No optimizar un
modelo fuera del rango calibrado sin declarar extrapolación e incertidumbre.

## Discretización implementada

Volúmenes finitos axiales: flujos convectivos upwind iniciales y dispersión centrada;
integración temporal rígida BDF/Radau, escalamiento por especie y fase, Jacobiano
disperso. Volúmenes radiales esféricos con pesos exactos de cascarón para HSDM.
Balance discreto global debe telescopar a flujos de frontera. Cuadratura acumulada
de entradas/salidas como estados del integrador. Interpolación de salida no debe
alterar los flujos usados para el balance. No recortar valores negativos: reportar
violación y refinar o fallar. Ver VALIDATION_PLAN.md antes de declarar uso predictivo.

FAST público describe HSDM/LDF y parámetros operativos, pero no documenta aquí un
solver abierto ni demuestra equivalencia con esta formulación. La página general
de documentación menciona solo Freundlich, mientras descargas y ayuda local indican
Langmuir para 2.1 beta: la versión debe constar en cualquier comparación.
Fuente contextual: [FAST](https://www.fast-software.de/documentation.html).


Detalles de mallas, película, tratamiento de iteraciones fuera del dominio y API numérica: IMPLEMENTATION_NOTES.md. La formulación lineal q*=Kc, K>=0 [m³/kg], agrega referencias exactas y el límite de trazador K=0. HSDM usa la carga media con pesos exactos de cascarón; conserva los perfiles radiales en resultados.

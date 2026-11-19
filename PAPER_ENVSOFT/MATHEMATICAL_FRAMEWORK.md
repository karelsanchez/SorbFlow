# Marco matemático y metodología científica

Versión 0.1, 2026-11-18. Distingue **modelo implementado I**, **método de estudio P**
y **extensión futura F**. No implica que toda la metodología esté implementada o validada.
Para detalles de código y evidencias actuales: MODEL_SPECIFICATION.md,
IMPLEMENTATION_NOTES.md y NUMERICAL_VERIFICATION.md en la raíz del repositorio.

## 1. Sistema, hipótesis y dominio físico (I)

Una especie diluida en agua, columna cilíndrica de área A y longitud L, líquido
incompresible, temperatura fija, porosidad de lecho epsilon uniforme y partículas
esféricas de radio R. Flujo positivo Q, entrada y propiedades constantes durante
cada ensayo. Sin reacción, competencia, especiación, transferencia térmica, expansión,
distribución de tamaños, canalización o evolución de propiedades por ensuciamiento.
Las identidades del contaminante y material son datos, no límites de cuatro materiales.

| Símbolo | Significado | SI y base |
|---|---|---|
| c,c_s,c_in | Concentración líquida, superficial y de entrada | kg soluto/m³ líquido |
| q, q_bar | Carga local y media de partícula | kg soluto/kg adsorbente seco |
| rho_p | Masa seca/volumen aparente de partícula | kg/m³ partícula |
| rho_b=(1-epsilon)rho_p | Densidad seca de lecho | kg/m³ lecho |
| u=Q/A, v=u/epsilon | Velocidades superficial e intersticial | m/s |
| D_ax,D_s | Dispersión axial y difusión superficial | m²/s |
| k_f,k_LDF | Película y tasa LDF global | m/s y 1/s, respectivamente |
| a_s=3(1-epsilon)/R | Área externa por volumen de lecho | 1/m |

Las cargas y densidades deben compartir base seca; no convertir masa húmeda sin
humedad medida. Conversiones molares requieren masa molar y especie explícitas;
no inferir ppm como mg/L. Las isotermas corresponden a T, pH, fuerza iónica y rango
de concentraciones medidos. Esos dominios aún no se hacen cumplir automáticamente:
añadirlos al contrato científico es un cambio requerido.

HSDM almacena soluto en la fase adsorbida y omite almacenamiento acuoso intrapartícula.
Evaluar su importancia, por ejemplo mediante phi_p*c/(rho_p*q_ref), antes de usar
esa simplificación. Si no es despreciable, comparar un modelo poroso apropiado;
no corregir una estructura incorrecta solo ajustando D_s.

## 2. Balance de columna y fronteras (I)

Definir flujo superficial másico J=u*c-epsilon*D_ax*dc/dz [kg/(m² s)]:

    d(epsilon*c + rho_b*q_bar)/dt = -dJ/dz, 0<z<L.

Para propiedades constantes:

    epsilon dc/dt + u dc/dz = epsilon D_ax d²c/dz² - rho_b dq_bar/dt.

Con D_ax>0, condiciones de Danckwerts y salida sin gradiente:

    J(0,t)=u*c_in; dc/dz(L,t)=0.

Con D_ax=0 se prescribe c(0,t)=c_in y la salida es convectiva, sin segunda
condición artificial. Estado inicial c(z,0)=c_initial>=0 y q_bar(z,0)>=0 (LDF)
o q(z,r,0)>=0 (HSDM). El código inicial usa campos uniformes, admite precarga y
desorción. Un escalón de entrada en 0+ no exige continuidad del estado interior.

Para geometría A(z) o propiedades variables (F), conservar el balance por longitud:

    d[A(z)(epsilon*c+rho_b*q_bar)]/dt
       = -d[Q(t)c-A(z)epsilon D_ax dc/dz]/dz.

No presentar esta extensión como resuelta por el cilindro uniforme actual. Entradas
por tramos requieren reinicio en discontinuidades y nuevas pruebas de balance/eventos.

## 3. Equilibrio y transferencia (I)

Langmuir: q*(c)=q_max*b*c/(1+b*c), q_max>0 [kg/kg], b>0 [m³/kg soluto].
Freundlich normalizado: q*(c)=q_ref*(c/c_ref)^alpha, con q_ref,c_ref,alpha>0.
c_ref se fija para evitar redundancia al ajustar q_ref/alpha. La derivada de
Freundlich es singular en cero para alpha<1; el código la informa explícitamente.
Lineal: q*=K*c, K>=0 [m³/kg]; K=0 sirve como referencia de trazador.
Freundlich no impone saturación: restringir la extrapolación al dominio medido.

LDF global:

    s = dq_bar/dt = k_LDF(q*(c)-q_bar).

k_LDF representa resistencia efectiva; no identificarlo con k_f ni sumar una
segunda película sin derivar el nuevo modelo. 15D_s/R² es una aproximación bajo
hipótesis específicas de esfera/difusión, no conversión universal entre modelos.

HSDM con película:

    dq/dt = D_s/r² d/dr(r² dq/dr), 0<r<R,
    dq/dr(0,t)=0,
    rho_p D_s dq/dr(R,t)=j=k_f(c-c_s),
    q(R,t)=q*(c_s),
    q_bar=3/R³ integral_0^R q(r)r²dr.

r crece hacia la superficie; j>0 significa entrada de masa a la partícula. De
integrar el balance radial se obtiene rho_b*dq_bar/dt=a_s*j. La misma j se utiliza
con signo contrario en líquido. D_s,k_f>0; límites nulos/infinitos se estudian
como referencias reducidas, sin constantes extremas presentadas como física real.

Batch cerrado LDF de referencia:

    V_l dc/dt = -m_s*s; dq_bar/dt=s;
    M=V_l*c+m_s*q_bar=constante.

Para q*=Kc, c_eq=(V_l*c0+m_s*q0)/(V_l+m_s*K) y
c(t)=c_eq+(c0-c_eq)exp[-k_LDF(1+m_s*K/V_l)t].

## 4. Discretización y aceptación numérica (I/P)

Volúmenes finitos axiales uniformes, convección upwind y dispersión centrada:
J_face=u*c_upwind-epsilon*D_ax*(c_R-c_L)/dz. Fronteras de flujo impuestas. En HSDM,
cascarones con w_j=(r_right³-r_left³)/3 y pesos w_j/sum(w_j); flujo de centro cero,
sin dividir por r=0. En superficie g=rho_p*D_s/(R-r_last) y se resuelve
k_f*c_s+g*q*(c_s)=k_f*c+g*q_last. Se usa la expresión de flujo menos afectada por
cancelación entre película y sólido; conservación sola no prueba precisión de j.

Integración rígida BDF/Radau, patrón Jacobiano disperso y tolerancias físicas
separadas. Min y Mout son estados acumulados del integrador, no cuadraturas de una
curva interpolada a posteriori. Extensión impar de q* solo para iteraciones numéricas
fuera de dominio; no cambia q* para c>=0 ni justifica resultados negativos físicos.
Se revisan pasos aceptados y salidas; negatividad >10 atol, no finitud o fallo de
masa producen error, sin recorte de estados. El límite de saturación y la validez
del régimen se ampliarán como diagnósticos explícitos de dominio (P).

    M(t)=A integral_0^L [epsilon*c+rho_b*q_bar]dz,
    R_M=M(t)-M(0)-Min(t)+Mout(t),
    S_M=max[M(0),Min(t),M_ref].

M_ref tiene unidades kg y se declara para cada escala. Criterio propuesto y
aplicado en el guard actual: |R_M|/S_M<=mass_rtol y
|R_M|<=atol_mass+mass_rtol*S_M. Referencias de laboratorio usan mass_rtol=1e-6;
la tolerancia absoluta no debe ocultar error relativo relevante. Refino espacial
y temporal deben separar sus errores. Un frente discontinuo se evalúa por norma
integral y posición, no por orden puntual. Una malla adecuada para t50 no garantiza
t10/t90 o clasificación de una restricción.

## 5. Modelo inverso y de observación (P, implementación parcial)

Datos de ensayo e: y_ei=h_ei(theta,x_e)+delta_ei+error_ei. h incluye salida, método
de muestreo/promediado y unidades. x_e comprende geometría, flujo, entrada, T,
humedad y condiciones iniciales; su error no se trata como certeza por conveniencia.
theta incluye equilibrio y transferencia identificables. delta representa discrepancia
estructural, separada del error analítico y sin flexibilidad arbitraria que absorba
los parámetros. Una mezcla nueva tiene propiedades medidas propias, no media de theta.

Para error gaussiano con covarianza Sigma_e:

    ell(theta)=-1/2 sum_e [r_e^T Sigma_e^-1 r_e + log|Sigma_e| + n_e log(2pi)],
    r_e=y_e-h_e(theta,x_e)-delta_e.

Diagonal heteroscedástica es el baseline; correlación temporal o entre réplicas se
evalúa con modelos explícitos. Con errores independientes, censura bajo LOD
contribuye mediante log F(LOD|h+delta,sigma), no como cero ni LOD/2. Si Sigma no es
diagonal, usar la densidad de las observaciones no censuradas multiplicada por la
probabilidad conjunta/condicional de la parte censurada dada la parte observada;
no sumar CDF marginales como si las observaciones fueran independientes. La API actual de ajuste no implementa censura ni este modelo
general. Si x es incierto, integrar sobre su distribución o modelarlo jerárquicamente;
no ponderar solo y y afirmar propagación completa.

Ajuste en parámetros logarítmicos positivos con límites físicos; varias inicializaciones
y comparación de mínimos. SVD escalada diagnostica sensibilidad local, pero no prueba
identificabilidad estructural/global. Definir perfil
PL_j(a)=max_{theta_-j} ell(theta_j=a,theta_-j), reoptimizando todos los demás parámetros.
Intervalos por razón de likelihood requieren verificar hipótesis regulares o calibrar
umbral por bootstrap cuando hay fronteras/no regularidad. Parámetros no identificables
se reportan y motivan más datos, reparametrización o restricciones justificadas; no
se fijan arbitrariamente para obtener intervalos estrechos. Referencia metodológica:
[Raue et al., 2009](https://doi.org/10.1093/bioinformatics/btp358).

Vía frecuentista principal propuesta: MLE/WLS, perfiles y bootstrap de ensayos completos.
Vía bayesiana opcional: p(theta,x,delta|D) proporcional a likelihood por priors declarados,
con diagnósticos de convergencia y sensibilidad a priors. No llamar posterior a una
covarianza local gaussiana ni convertirla automáticamente en confiabilidad demostrada.

## 6. Incertidumbre y sensibilidad (P, implementación parcial)

Separar: parámetros theta; entradas/proceso xi; medición; discrepancia/modelo;
error numérico. Separar incertidumbre epistemológica de variabilidad aleatoria.
Estimar distribuciones y correlaciones desde datos o elicitar escenarios explícitos.
Si las probabilidades no están justificadas, presentar robustez por escenarios/deep
uncertainty y no restricciones probabilísticas certificadas.

Propagación anidada o conjunta de draws compatibles, preservando dependencia de
parámetros. Para escenarios de optimización usar números aleatorios comunes congelados;
para evaluación, draws independientes. La evaluación de cobertura repite datasets
sintéticos, recalibra cada uno y distingue intervalos de parámetros, respuesta latente
y predicción observada. Sensibilidad local es exploratoria; Morris/Sobol o alternativas
para entradas dependientes requieren elección y presupuesto específicos. No interpretar
índices Sobol clásicos bajo correlación sin la transformación/definición apropiada.

## 7. Diseño robusto multiobjetivo (P)

Decisión d: L, diámetro, masa/mezcla, Q operativo u otras variables con dominio
fabricable y validado. Evitar parametrización redundante de L, volumen y masa.
Estado Y(d,theta,xi) del modelo físico. Ergun para pérdida de carga en el dominio
aplicable y energía de bombeo integral Q*DeltaP/eta dt; precios, moneda/año y límites
externos declarados. El costo parcial actual no es un modelo económico de ciclo de vida.

Vector de minimización candidato:

    F(d)=[E(C_lifecycle), E(E_pump), CVaR_beta(L_service)]

donde L_service puede ser déficit de volumen tratado seguro; seleccionar dos o tres
objetivos no redundantes antes del benchmark. CVaR_beta(L)=min_eta
[eta+E(max(L-eta,0))/(1-beta)]. Ninguno de estos operadores es novedoso por sí mismo.
Comparar también otras elecciones de riesgo y revelar el costo de robustez.

Restricción conjunta de efluente durante horizonte T_s:

    G_c(d,theta,xi)=max_{0<=t<=T_s}[c_out(t)-c_limit]/c_limit,
    P(G_c<=0 y G_pressure<=0 y G_domain<=0 | D)>=1-alpha.

No confundir probabilidad punto a punto con cumplimiento de toda la trayectoria,
ni probabilidad predictiva condicionada a D con confianza de la estimación Monte Carlo.
El ejemplo actual verifica escenarios finitos y concentración terminal, no esta
restricción general. Si hay incertidumbre profunda sin una ley defendible, usar
regret/escenarios y declarar que no hay interpretación probabilística.

Una aproximación por escenarios tiene Ghat o frecuencia de fallo; su factibilidad
en entrenamiento no certifica fuera de muestra tras seleccionar d. Validar candidatos
retenidos en un conjunto independiente y usar intervalos binomiales exactos y control
de multiplicidad si se comparan varios diseños. Fallos de solver cuentan como fallo
o estado no resuelto conservador, no como muestras descartadas.

La incertidumbre numérica puede cambiar la clasificación. Estimar/refinar error en
salida/evento y aplicar margen conservador; si el signo depende de malla/tolerancia,
clasificar no resuelto y refinar. Richardson empírico no es una cota rigurosa universal.
Registrar tanto fallo seguro como posible fallo y no presentar falsa certificación.

## 8. Alcance de las conclusiones

Exactitud seleccionada de sistemas discretos no implica convergencia universal de la
EDP, validez química, identificabilidad ni confiabilidad industrial. La superioridad
se contrasta con baselines y ablaciones de BENCHMARK_PROTOCOL.md, a igual presupuesto,
con intervalos y escenarios independientes. La necesidad de un algoritmo nuevo no
se presupone; tampoco se presupone que una metodología integrada ya sea novedosa.

## Precisiones del problema inverso y decisión

Cuando q=(V/m)(c0-c_eq), q y c_eq comparten error de medición: representar esa dependencia o justificar una aproximación de errores en variables. Perfilar también cantidades de decisión, por ejemplo PL_g(a)=max ell(theta) sujeto a g(theta,d)=a. Parámetros individuales ambiguos no implican automáticamente una decisión ambigua. Aplicar las acciones C03/C06 de NOVELTY_MATRIX, comparándolas con ablaciones y presupuestos equivalentes.

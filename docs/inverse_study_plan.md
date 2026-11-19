# E02-A: diseño sintético de identificabilidad e intervalos

**Estado: DISEÑO PROPUESTO; estudio no ejecutado ni confirmatorio.** Ya existen
una [API experimental de perfiles](profile_likelihood.md) y un
[objetivo batch K/k](batch_objective.md), probados separadamente. El estudio de
identificabilidad/cobertura completo sigue pendiente. E01 continúa parcial;
E04 continúa BLOCKED_METADATA, con 0 curvas listas. La interfaz web es opcional y
no participa en los criterios científicos del artículo.

Este subestudio concreta [E02 del protocolo](../PAPER_ENVSOFT/BENCHMARK_PROTOCOL.md)
y las afirmaciones candidatas C03/C04 de la
[matriz de novedad](../PAPER_ENVSOFT/NOVELTY_MATRIX.md). Antes de ejecutar se deben
congelar casos, semillas, límites físicos, presupuesto, umbrales y revisión del
código en un manifiesto. Un piloto puede cambiar el protocolo mediante una
enmienda registrada; sus datos no se reutilizan como confirmación independiente.

## 1. Alcance y capas disponibles

| Capa real | Uso permitido en E02-A | Trabajo pendiente |
|---|---|---|
| [pyfast.fit](../src/pyfast/fit.py) | Baseline de isoterma y tasa batch LDF | Ajuste conjunto de equilibrio/tasa, multiinicio y perfiles |
| [calibration.least_squares](../src/pyfast/calibration/least_squares.py) | SVD y covarianza local en coordenadas logarítmicas | Likelihood general, límites físicos explícitos y resultado de perfiles |
| [pyfast.simulate](../src/pyfast/simulate.py) | Predictor batch LDF; comprobar error numérico | Generador independiente y contador de solves |
| [esquemas](../src/pyfast/schemas.py) y [unidades](../src/pyfast/units.py) | Parámetros SI, especie, material y condiciones explícitas | Esquema del estudio y observaciones sintéticas con ruido firmado |
| [pyfast.uncertainty](../src/pyfast/uncertainty/__init__.py) | Utilidades de propagación y sensibilidad | Estudio repetido de cobertura de estimadores/intervalos |

La [API pública](../API_REFERENCE.md) actual `isotherm` estima parámetros de un
modelo con c sin error; Freundlich mantiene c_ref fijo. `batch_rate` estima
únicamente k_LDF, tratando equilibrio y condiciones como conocidos. No presentar
esta última función como ajuste conjunto de k y equilibrio. La nueva API de perfiles
reoptimiza nuisance en una malla positiva con sigma conocida: no entrega un intervalo
continuo ni una prueba de identificabilidad global. El ejemplo `examples/profile_batch.py`
es una demostración sintética de ingeniería, no el estudio E02-A.

## 2. Problemas y verdad sintética

Concentración c en kg/m³, carga q en kg/kg seco, masa m en kg seco, volumen V en m³,
tiempo en s y temperatura T en K. Identidad de material y contaminante es dato;
el estudio admite N materiales independientes, sin fijar cuatro ni compartir
parámetros entre materiales por conveniencia.

**Isotermas:** observaciones q_i = q*(c_i; theta) + sigma_i z_i, con c_i conocida,
z_i normales independientes estándar. Langmuir estima theta=(q_max,b);
Freundlich estima (q_ref,alpha) con c_ref fijo; lineal estima K. Un caso de rango
estrecho se contrasta con otro que cubra el cambio de curvatura. No añadir error
en c sin una likelihood de errores en variables: será una ampliación separada.

**Batch lineal:** balance V c + m q = V c0 + m q0 y dq/dt=k(Kc-q).
Para q0=0 y beta=m/V conocida, usar verdad exacta independiente del integrador:

    c_eq = c0 / (1 + beta K)
    lambda = k (1 + beta K)
    c(t) = c_eq + (c0-c_eq) exp(-lambda t)

Estimar primero theta=(K,k), con c0, q0, m y V conocidos. Comparar ventana temprana
con una curva que incluya transitorio y meseta. Verificar unidades y balance de la
verdad exacta antes de añadir ruido. Para batch no lineal, posponer la confirmación
hasta disponer de generador independiente o referencia refinada con error acotado;
reutilizar predictor y tolerancias del ajuste no constituye independencia.

Las soluciones exactas de equilibrio y batch lineal son sintéticas. No validan
la química de un material ni sustituyen E04. Ver [modelo](../MODEL_SPECIFICATION.md)+y [marco del artículo](../PAPER_ENVSOFT/MATHEMATICAL_FRAMEWORK.md).

## 3. Información, confusores y experimentos complementarios

| Diseño o incógnita | Qué permite o qué impide inferir |
|---|---|
| Solo equilibrio | Puede informar equilibrio; no contiene información sobre k |
| Langmuir con b c muy pequeño | Principalmente informa el producto q_max b; ampliar rango hacia curvatura ayuda a separar ambos |
| Solo saturación de Langmuir | Informa q_max; b puede quedar débilmente determinado |
| Freundlich con q_ref, c_ref y alpha libres | q_ref/c_ref^alpha es combinación redundante; fijar la referencia de unidades, no inferir tres parámetros |
| Batch lineal completo, beta conocida, c0 conocida, q0=0 | Amplitud/meseta y decaimiento pueden separar K y k en el caso ideal; no exige varios beta para identificabilidad estructural |
| Solo pendiente batch inicial | Aproxima el producto beta k K c0; no garantiza separación práctica de K y k |
| beta desconocida | El batch lineal observa beta K; cambiar nominalmente V/m sin medirlos no separa K y beta |
| q0 desconocida con una curva lineal | La meseta depende de c0+beta q0; puede confundirse con K y k. Medir/preparar q0 o aportar ensayos independientes |
| V/m conocidos y variados, transitorios/mesetas medidos | Puede mejorar sensibilidad y romper algunos confusores; evaluar perfiles, no prometer éxito universal |
| c0 variada con equilibrio no lineal | Puede ampliar el rango informativo; repetir únicamente el mismo régimen lineal no crea curvatura |
| T variada | No identifica una ley térmica que no esté parametrizada. Mantener T fija aquí; ajustar por T o declarar ley térmica antes de compartir parámetros |

Compartir datos entre ensayos exige mismo material/lote, especie y T, con parámetros
compartidos físicamente justificados. Cada ensayo conserva sus c0, q0, m, V y tiempos.
Un error desconocido de escala en masa o concentración necesita medición externa o
modelo explícito; no se trata como otra desviación estándar de q. No inferir Ds y
k_f separados a partir de una tasa LDF efectiva.

## 4. Ruido y parámetros nuisance

Dos ramas predefinidas: (A) sigma_i conocidas por diseño; (B) sigma_i=s w_i con
w_i conocidas, s>0 estimado conjuntamente. No usar varianza residual de A como si
sigma fuese desconocida. Si cada ensayo tiene su propio s, perfilarlos por ensayo
y registrar la pérdida de información. El caso s=0 y RSS=0 es singular: no producir
intervalos ordinarios; marcar no regular y revisar el diseño.

Variables nuisance candidatas posteriores: c0 y q0 por ensayo, o un offset común
con controles independientes. Incorporarlas una a una mediante escenarios
predeclarados. m y V se miden en la rama primaria; si son inciertos se necesita una
likelihood conjunta de sus mediciones, no fijarlos a su valor verdadero durante el
ajuste y afirmar propagación completa. No ajustar simultáneamente un ruido libre
por punto: el problema deja de estar sustentado por estas observaciones.

El ruido gaussiano puede producir observaciones negativas: no recortar, descartar
ni volver a muestrear. Elegir el régimen primario alejado del límite de detección,
registrando aun así todos los datasets y fallos. La API actual de observaciones no
admite concentraciones negativas; diseñar un contrato específico de medición antes
de estos ajustes, sin modificar el estado físico ni ocultar muestras incompatibles.
Censura, correlación y discrepancia quedan fuera de E02-A.

## 5. Ajuste, perfiles e intervalos

Baseline: un inicio. Comparador: 20 inicios distribuidos en el dominio logarítmico
físico congelado, incluyendo el inicio del baseline; semillas independientes del
generador de datos. Comparar también con presupuesto total equivalente para que
una mejora no se atribuya solo a más evaluaciones. Registrar todos los mínimos,
terminaciones y solves físicos reales, incluidas diferencias finitas y fallos.
`nfev` del optimizador no sustituye ese contador.

Para cada parámetro j y valor fijado a, calcular:

    ell_profile_j(a) = max_nuisance ell(theta_j=a, theta_-j)
    LR_j(a) = 2 [ell_hat - ell_profile_j(a)]

Reoptimizar **todos** los demás parámetros físicos y de ruido estimados, con varios
inicios; no evaluar una sección manteniéndolos en su óptimo global. Usar continuación
desde ambos lados y reinicios separados. Si un perfil encuentra mejor mínimo,
actualizar el óptimo y recalcular los perfiles afectados dentro del presupuesto;
si no alcanza, declarar INCOMPLETE. Los cruces requieren refinamiento/verificación,
no interpolar una malla gruesa como intervalo exacto.

Con errores gaussianos independientes y sigma conocidas, LR es la diferencia de
sumas de cuadrados ponderadas. Con una escala común desconocida perfilada por MLE,
LR = n log(RSS_w(a)/RSS_w_min), usando RSS_w ponderado por w_i; no sustituir esta
expresión por diferencia de RSS dividida por la varianza insesgada n-p. Con varios
ruidos o restricciones, evaluar la likelihood completa, incluidos log-determinantes.

Umbral candidato nominal 95% para un parámetro: cuantil chi-cuadrado de 1 grado de
libertad, aproximadamente 3.841, **solo como aproximación asintótica regular interior**.
Los casos de muestra pequeña, frontera, simetría o identificación débil requieren
evaluación/calibración por simulaciones paramétricas independientes predeclaradas;
no aplicar universalmente ese umbral. E02-A no incorpora bootstrap. Separar semillas
y datasets usados para calibrar umbrales de los usados para evaluar cobertura.

Un perfil abierto, multimodal o terminado por límite computacional se informa como
tal. Un extremo que alcanza el límite físico es `BOUND_LIMITED`, no evidencia de
intervalo cerrado por los datos. Valores cero admisibles requieren tratamiento
explícito de frontera: log-coordenadas estrictamente positivas no los representan.

La covarianza/SVD actual proporciona aproximación **local**. Buen rango/condición
no descarta mínimos alternativos, simetrías o regiones planas alejadas. Perfiles y
multiinicio finitos tampoco prueban identificabilidad global; las redundancias
estructurales requieren análisis del modelo. La referencia metodológica ya recogida
en el marco es [Raue et al. (2009)](https://doi.org/10.1093/bioinformatics/btp358);
este plan no afirma haber reproducido sus resultados.

## 6. Cobertura independiente y presupuesto candidato

Piloto candidato: R=50 datasets nuevos en cada uno de dos regímenes batch
(informativo y limitado). Confirmación candidata: R=500 por régimen, con semillas
independientes del piloto y de la calibración de umbrales. Elegir antes de congelar
qué rama de ruido confirma cada régimen; añadir factores multiplica el presupuesto.
Isotermas algebraicas se contabilizan aparte como evaluaciones, no solves de ODE.

Techo inicial por dataset batch de dos parámetros: 20 inicios × 150 solves = 3000;
dos perfiles × 21 puntos × 3 inicios × 60 solves = 7560; total 10560 solves físicos.
Reservar además un 20% explícito para refinamiento de cruces: techo 12672.
Así, 100 datasets piloto permiten hasta 1267200 solves y 1000 confirmatorios hasta
12672000, antes de calibración adicional de umbrales. Estos son límites de diseño,
no tiempos ni consumo observado. Congelar un presupuesto adicional separado de
calibración; si no existe, los escenarios no regulares quedan NOT_TESTED.

Toda llamada al predictor, incluida la de Jacobianos, consume presupuesto; los
solves analíticos no se hacen pasar por integración numérica. Agotarlo produce
INCOMPLETE, conserva evidencias y nunca reintenta silenciosamente con mayor techo.
El piloto puede reducir mallas/casos o ampliar recursos mediante enmienda; no
seleccionar después solo datasets fáciles. Paralelizar datasets independientes
debe conservar semillas y resultados, sin presentarlo como ejecución distribuida.

## 7. Criterios candidatos antes de confirmación

- Verdad exacta: balance y error numérico del predictor por debajo de 0.1 sigma_i
  en observaciones; verificar también al endurecer tolerancias. Si falla, separar
  error numérico de estadístico y suspender la inferencia correspondiente.
- Óptimos: reportar fracción de inicios que alcanzan likelihood equivalente
  (candidato delta LR <= 1e-4), sin convertir convergencia en prueba global.
  Refinar perfiles hasta variar sus cruces menos del 2% en escala del parámetro;
  divergencia entre reinicios produce INCOMPLETE, no cierre artificial.
- Cobertura marginal nominal 95%: mostrar frecuencia e intervalo binomial de cada
  parámetro y cantidad de interés. Candidato: límite inferior binomial 95% >= 0.92
  en regímenes informativos; fijar método binomial antes de correr. No confundir
  cobertura marginal con conjunta. A R=500, SE nominal esperado es 0.00975.
- Anchura: candidato mediana de anchura relativa <= 0.5 para parámetros positivos
  en el régimen informativo; en el limitado reportar amplitud/abertura honestamente,
  sin exigir una precisión imposible. Evaluar c(t) latente y futura observación por
  separado; ruido de medición solo pertenece al intervalo predictivo de observación.
- Reportar sesgo, RMSE, fallos, límites alcanzados y costo para todos los datasets.
  Una cota conservadora trata fallos como no cobertura; aportar también cobertura
  condicionada a éxito con denominador explícito. No excluir fallos del resultado.
- Comparar diagnóstico local, multiinicio y perfiles con igual información y costo
  declarado. Un beneficio solo en un régimen limita la afirmación al mismo régimen;
  un resultado negativo o intervalo no informativo sigue siendo publicable como tal.

## 8. Entregables para la siguiente implementación

1. Esquema congelable de casos/semillas/ruido y manifiesto de fuente, entorno y hashes.
2. Generador exacto probado separadamente, contador de solves y ajuste conjunto
   con límites/nuisance; API experimental separada de la estable hasta revisión.
3. Extender la evidencia de perfil con reoptimización y malla explícita; la API actual
   no emite intervalos continuos CLOSED/OPEN. Conservar estados de límite e incompletitud;
   pruebas de redundancias y mínimos alternativos además de recuperación favorable.
4. Piloto reproducible, enmienda explícita si procede y registro de cobertura
   independiente con presupuesto autorizado antes del estudio confirmatorio.
5. Tablas/figuras sintéticas E02-A con denominadores, incertidumbre Monte Carlo,
   anchuras, fallos y costos; actualización del registro solo tras revisar evidencias.

Hasta completar estos entregables, E02 permanece pendiente. Este diseño no habilita
afirmaciones de solver validado, cobertura demostrada ni validación experimental.

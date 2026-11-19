# Primer caso E04 recomendado

**Decisión: `NOT_READY`.** Hoy ningún conjunto acuoso es apto para validación física
independiente del PyFAST actual. Esto confirma, con evidencia propia, el estado heredado de
cero curvas listas. Los detalles están en `E04_ISSUES.md` y `E04_METADATA_MATRIX.csv`.

No se afirma validación del solver, superioridad ni permiso de redistribución.

## Candidato condicionado: Banana peel / MB (Stavrinou et al., *Processes* 2020, 8, 1467)

Es el conjunto acuoso **menos ambiguo** por tres razones:

| Criterio | Banana peel | MAR2PROTECT | Quitosano |
|---|---|---|---|
| Monocomponente | Sí (PUBLISHED) | UNKNOWN (¿mezcla?) | Sí |
| Geometría L, D | Publicada | Ausente | Publicada |
| ε, ρ_b, d_p, T | Publicados (Tabla 7, §2.1, Tabla 8) | Ausentes | Solo d_p y T |
| Masa coherente con ρ_b·A·L | Sí (2,43/4,86/7,29 g) | 1400 kg/g en conflicto | Masa no publicada; tablas incoherentes |
| Condiciones distintas | 8 (2 Q × 3 Lb, y 2 C0 a Lb mínimo) | 1–3, quizá una sola corrida | 7, una reutilizada |
| Datos t–C numéricos | **No** (solo figura) | Sí, con edición no trazable | Caché parcial de origen externo |

1. **Es el único con geometría y propiedades del lecho completas y coherentes entre sí.** La masa se recompone desde ρ_b·A·L, y el u0 de la Tabla 7 se explica como velocidad intersticial (conversión DERIVED).
2. **Es el único con un diseño factorial** que permite separar ensayos completos entre calibración y prueba.
3. **No tiene contradicciones internas** comparables a las de MAR2PROTECT (A3–A5) o quitosano (C1–C2).

Su bloqueo principal es de **forma**, no de consistencia: las observaciones solo existen como marcadores de la Figura 5.

MAR2PROTECT queda como **segunda vía**. Tiene datos numéricos a escala piloto, pero exige que la autora responda A1–A9. Aun resuelto, aporta como máximo una columna por analito, o una sola si fue una mezcla. Por eso no permite una partición interna calibración/prueba.

Quitosano **no se recomienda** mientras no aparezca el libro de datos original, porque sus tablas no cierran el balance de masa.

## Condiciones para admitir el caso Banana

Todas deben cumplirse **antes** de abrir la condición de prueba:

1. **Datos de observación.** Se necesitan pares t–C de los autores (preferible) o una digitalización documentada en una revisión posterior autorizada. La digitalización debe dejar constancia de:
   - el software y la versión;
   - la calibración de los ejes y sus unidades, verificadas en el PDF;
   - la resolución en píxeles y el error estimado en t y en C/C0;
   - un doble operador o una repetición;
   - que solo se digitalizan los **marcadores**, nunca las líneas ajustadas;
   - qué curva de qué panel se toma, sin contar dos veces las curvas compartidas (B5).
2. **Metadatos que faltan:**
   - masa en base seca, o confirmación de que los 2,43 g son secos;
   - método de medida de φ y confirmación de que es interpartícula;
   - relleno del tramo de columna sin lecho y su volumen muerto;
   - LOD/LOQ del UV-vis, si se diluyó y réplicas;
   - estabilidad medida de Q y de C0;
   - el tiempo cero, es decir, el retardo por las líneas.
3. **Isoterma y cinética independientes** de las curvas de columna. Los datos batch del mismo artículo (Tablas 2 y 5, Figuras 3 y 4) son el candidato, siempre que se usen sus *observaciones* (también solo en figura) y no las curvas ajustadas. Debe confirmarse que son compatibles en T (25 °C) y en granulometría.
4. **No usar parámetros ajustados por los autores con la curva de prueba.** La Tabla 8 (Smax, *a*) se estimó con cada una de las 8 curvas. Para la condición de prueba no puede usarse ni su valor ni un promedio que la incluya.
5. **Modelo de transferencia fijado de antemano.** Cualquier dependencia de k_f o k_LDF con Q o Lb (los autores observan que *a* varía con u0 y Lb) se fija con las condiciones de calibración y se declara antes de abrir la prueba. Si no hay un mapping defendible, el claim se restringe a las condiciones calibradas, como indica `EXPERIMENTAL_VALIDATION.md` §4.
6. **Conversiones explícitas en un registro:**
   - u = Q/A, y no el u0 de la Tabla 7;
   - ρ_p = ρ_b/(1−ε), solo si ε es interpartícula;
   - C0 en kg/m³;
   - cada conversión, marcada como DERIVED.

## Partición futura propuesta (por condición completa)

Se fija aquí como propuesta. Codex la revisará antes de usarla. La unidad es la condición completa, nunca puntos de una curva.

| Rol | Condiciones (Q mL/min, Lb cm, C0 mg/L) | Razón |
|---|---|---|
| Calibración | (1, 1,86, 100), (3, 1,86, 100), (1, 5,58, 100), (3, 5,58, 100) | Extremos de Q y Lb a C0 base |
| Desarrollo | (1, 1,86, 200) | Decisiones metodológicas (modelo de error, LDF frente a HSDM) |
| Prueba retenida | (1, 3,72, 100), (3, 3,72, 100), (3, 1,86, 200) | Interpolación en Lb a ambas Q, y C0 alta a Q alta |

Precauciones de la partición:
- La prueba en C0 = 200 extrapola en concentración respecto a la calibración. Debe reportarse por separado de la interpolación en Lb.
- Si las curvas resultan compartidas entre paneles (B5), se cuentan una sola vez.
- Parámetros, preprocesado, criterios y modelos se congelan antes de abrir la prueba.
- Las 8 condiciones son de un mismo lote de adsorbente y un mismo laboratorio. Esto **no** acredita generalización a otros materiales ni contaminantes.

## Limitaciones que persisten aun cumpliendo las condiciones

- Hay una curva por condición y no hay réplicas de columna, así que la incertidumbre entre ensayos no es estimable.
- La digitalización limita la resolución de la primera ruptura y de las colas.
- El sistema es a escala de laboratorio (D = 1,68 cm, d_p 125–500 µm, D/d_p de unos 34 a 134). La relevancia para diseño piloto no queda demostrada.
- El modelo de los autores difiere del de PyFAST (cinética de Langmuir con *a* dependiente de C, y dispersión F, k, aL). Que el modelo de los autores ajuste bien no implica nada sobre LDF/HSDM.

## Lista mínima de metadatos que faltan, por fuente

- **Banana:**
  - pares t–C (revisar LAPSE:2021.0468 cuando deje de responder 429);
  - unidades de los ejes de la Figura 5;
  - masa seca;
  - método de φ;
  - relleno de la columna;
  - LOD/LOQ;
  - Q y C0 medidos;
  - retardo de las líneas.
- **MAR2PROTECT:**
  - L y D de la columna;
  - disposición de la arena;
  - mezcla o monocomponente, y fechas;
  - confirmación de 1400 g (seco o húmedo) y de 4400 mL;
  - ε, ρ_p y ρ_b;
  - d_p;
  - T, pH y matriz;
  - LOQ por analito;
  - horas reales y tipo de muestreo;
  - influente medido;
  - serie primaria de DCF e IBU;
  - identidad del bloque HPLC N:R;
  - causa de C > 0 en t = 0.
- **Quitosano:**
  - libro de datos original (las cachés apuntan a XLSX externos no publicados);
  - masa seca;
  - ε y ρ_b;
  - estado húmedo o seco de las perlas;
  - LOD/LOQ;
  - aclaración de Veff, m_total y q_total;
  - rótulos de la Figura 17.

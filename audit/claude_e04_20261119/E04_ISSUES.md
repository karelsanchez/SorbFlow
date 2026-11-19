# E04 — Bloqueos de admisión de datos

Revisión independiente, 2026-11-19. El repositorio PyFAST se consultó en solo lectura.
Las rutas son relativas a `PyFAST/datasets_benchmark_pyfast/`, salvo que se indique otra cosa.
Las comparaciones reproducibles están en `_aux/` (`mar_cells.txt`, `mar_compare.txt` y los scripts que las generan).
La matriz por ensayo está en `E04_METADATA_MATRIX.csv` y los localizadores en `SOURCE_EVIDENCE.json`.

Convención de estados: **PUBLISHED** (valor en la fuente), **DERIVED** (conversión
dimensional justificada y explicitada), **INTERPRETATION** (lectura razonada, no un dato),
**CONFLICT** y **UNKNOWN**.

Prioridad:
- **P0** impide cualquier uso como validación.
- **P1** impide la predicción independiente aunque se permita un ajuste exploratorio.
- **P2** es una mejora de trazabilidad.

---

## A. MAR2PROTECT (`01_MAR2PROTECT/…BPA-DCF-IBU.xlsx`, Zenodo 10.5281/zenodo.21068675)

### A1 · P0 · No hay geometría del lecho
- **Evidencia:** ninguna celda de las cinco hojas da altura, diámetro ni área. La lista completa de cadenas compartidas está revisada (54 cadenas). La ficha Zenodo menciona *bed height* como categoría, pero no da su valor (API consultada el 2026-11-19).
- **Impacto:** sin A ni L no se obtienen u = Q/A, el número de Péclet, la dispersión axial ni el perfil axial. HSDM y LDF con dispersión no se pueden configurar sin inventar datos.
- **Pregunta:** ¿cuáles son el diámetro interno, la altura de la fase activa y la altura y posición de la arena?

### A2 · P0 · No se sabe si es mezcla o corridas monocomponente
- **Evidencia:**
  - Las tres hojas comparten Q = 170 mL/min, 4400/1100, una masa de 1400 y C0 nominal de 5 mg/L (`*!C5:C11`).
  - El calendario es diario en las tres, con duraciones de 45, 30 y 16 días.
  - Ninguna celda declara cómo se alimentó la columna.
  - Las réplicas "Mesure 1/2" son analíticas.
- **Impacto:** el solver es monoespecie. Si fue una mezcla, la competencia invalida usar cada analito como un ensayo independiente con su isoterma monocomponente, y tres analitos podrían ser **una sola** unidad experimental.
- **Pregunta:** ¿se alimentaron BPA, DCF e IBU juntos en una misma columna o en columnas o cargas distintas? ¿Con qué fechas y lotes?

### A3 · P0 · El tercer bloque HPLC está rotulado "DCF" pero contiene IBU
- **Evidencia:** `HPLC MICROPOLLUTANTS CONCENTRAT!N3` dice "DCF concentration", pero `Q6:Q22` es idéntico a `IBP FIXED BED COLUMN!E16:E32` (17/17) y distinto del bloque `H:L` (DCF).
- **Lectura:** *interpretación* fuerte de que N:R es IBU. El rótulo sigue en **CONFLICT** mientras la fuente no lo corrija.
- **Pregunta:** ¿confirma la autora que N3:R22 es ibuprofeno?

### A4 · P0 · Valores de DCF e IBU editados y no trazables a las medidas
- **Evidencia, DCF:**
  - `DCF FIXED BED COLUMN!E16:E46` difiere de la media HPLC `K6:K36` hasta en ±0,005 mg/L en 18 de 31 puntos (p. ej. E18 = 0,275 frente a K8 = 0,28).
  - `DCF!E29 = 1.25730337078652` y `E30 = 1.910112359550562` comparten las colas decimales de las medias de IBU `HPLC!Q19 = 4.82573033707865` y `Q20 = 4.91011235955056`.
- **Evidencia, IBU:**
  - Siete "Moyenne" de IBU no son el promedio de Mesure 1/2 (`Q8` = 0,774 frente a 0,77; `Q11` = 1,375 frente a 1,38; `Q19` = 4,8257 frente a 4,83, …).
  - La desviación típica de IBU (`R6:R22`) está tecleada, no calculada.
- **Observación:** el patrón es compatible con edición manual o copia entre series. No se afirma su causa.
- **Impacto:** las series de DCF e IBU no son medidas primarias verificables. Un ajuste o una validación heredaría errores de procedencia desconocida.
- **Pregunta:** ¿cuál es la serie primaria de DCF e IBU (cromatogramas o exportación del HPLC) y por qué difieren la hoja de columna y la hoja HPLC?

### A5 · P1 · Unidades contradictorias de masa y volumen
- **Masa:**
  - `C8` = 1400 con rótulo "Kg of active phase" (`D8`).
  - `J4` dice "Adsorbent amount (g)", y `qe = J16/C8` sale en mg/g (`K18`).
  - Con kg la densidad aparente sería unas 318 g/mL, físicamente imposible.
  - *Interpretación:* 1400 g. Sigue sin saberse si es masa seca o húmeda.
- **Volumen:**
  - `C4` e `I4` dicen L; `D5:D7` dicen ml.
  - `EBCT = C5/C9 = 25.88` (`C14`, sin unidad) solo es coherente con 4400 mL y 170 mL/min. Con L daría unos 25 882 min.
  - *Interpretación:* 4,4 L de fase activa y 1,1 L de arena.
- **BV:** `D16 = B16*C9/C5` cuenta solo la fase activa. No es un volumen de poro ni el volumen total de 5,5 L.
- **Impacto:** sin confirmación, ρ_b y EBCT no son admisibles como datos. El cociente 1400 g / 4,4 L no equivale a la ρ_b de PyFAST (masa seca por volumen de lecho) si la arena está mezclada.
- **Pregunta:** confirmar las unidades y si 1400 g es masa seca.

### A6 · P1 · Disposición de la arena
- **Evidencia:** `C4` dice "4,4 L Biochar/1,1 L Sand (V/V)".
- **Impacto:** PyFAST asume un lecho uniforme. Una capa inerte separada es un lecho de dos zonas; una mezcla cambia ε, ρ_b y la dispersión.
- **Pregunta:** ¿la arena va en capa (arriba, abajo o soporte) o mezclada con el biochar?

### A7 · P1 · Faltan propiedades del adsorbente y condiciones de operación
- **Faltan:** porosidad del lecho, densidad aparente de partícula, base seca, tamaño o distribución de partícula, origen y preparación del biochar, T, pH, matriz del agua, presión y estabilidad de Q.
- **Evidencia:** ausentes en el XLSX y en la ficha Zenodo.
- **Precaución:** el registro relacionado Zenodo 17962329 (Ennouri et al., ESFC 2025) describe **otro** sistema: biochar de hoja de palma funcionalizado con arcilla, columna de vidrio de 3 cm de diámetro, 2 mL/min y BPA a 10 mg/L. No se transfiere ningún valor de ese registro.
- **Pregunta:** ¿hay hoja de caracterización o publicación asociada a este piloto?

### A8 · P1 · Eje temporal nominal y entrada constante supuesta
- **Tiempos:** `B18 = B17+1440` y siguientes generan una rejilla diaria. No hay horas reales de muestreo ni se dice si cada muestra es puntual o compuesta.
- **Entrada:** C/C0 = E/5 usa un 5 fijo y no hay serie de influente medida.
- **Efluente en t = 0:** DCF da 0,2 mg/L (C/C0 = 0,04) e IBU 0,7 mg/L (C/C0 = 0,14). Esto puede indicar fuga inicial, desplazamiento del tiempo cero o un influente distinto.
- **Impacto:** el solver exige Q y c_in constantes, y esa constancia debe demostrarse. Errores de ±horas en t son relevantes a escala de días solo si el muestreo no fue diario.
- **Pregunta:** horas reales, tipo de muestreo, serie de influente medida y explicación de C > 0 en t = 0.

### A9 · P1 · Censura y LOQ
- **BPA:** `HPLC!C6:D14` = "<LOQ" y su media se sustituye por 0,03 en `E6:E14` y en `BPA!E16:E24`, según la nota LOQ/2 de `HPLC!B1`.
- **Sin valor:** el LOQ numérico no se declara. Si 0,03 es LOQ/2, el LOQ sería 0,06 mg/L, pero esto es solo una *interpretación*.
- **DCF e IBU:** no tienen ningún "<LOQ", aunque sus hojas repiten la nota (`DCF!A49`, `IBP!A34`).
- **Impacto:** los 9 primeros puntos de BPA deben tratarse como censurados por la izquierda (likelihood de censura), no como 0,03 exacto. Sin el LOQ no se puede construir esa likelihood.
- **Pregunta:** LOQ y LOD por analito y método, con su calibración.

### A10 · P2 · Magnitudes derivadas de la hoja no reutilizables
- **Balances:** `qe`, `q@BP` y `Re%` se calculan con C0 = 5 fijo y Q nominal.
- **Error de rango:** `q@BP = SUM(H17:H39)` usa el mismo rango en BPA y DCF. En DCF, la fila 39 tiene C = 3,8 mg/L, por encima del BP de 0,5, así que el rango es incorrecto.
- **Rótulo engañoso:** "BT time" (`C12`) es la duración total de la corrida, no un tiempo de ruptura.
- **Impacto:** no usar estas cifras como referencia de capacidad ni como objetivo de ajuste.

### A11 · P2 · Ausencia de replicación de columna
- **Evidencia:** solo hay una columna por analito. Mesure 1/2 son réplicas del HPLC.
- **Impacto:** n = 1 ensayo, como máximo, por analito, y 1 en total si fue una mezcla. No hay partición calibración/prueba posible dentro de MAR2PROTECT sin violar la independencia.

---

## B. Banana peel / MB (`02_…`, 10.3390/pr8111467)

### B1 · P0 · Las curvas solo existen como figura
- **Evidencia:** las curvas están en la Figura 5a-c (`article_deploy.xml`, fig `processes-08-01467-f005`). El XML no contiene `supplementary-material` ni declaración de disponibilidad de datos.
- **Consultas web:** la página MDPI y `/s1` responden 403 (2026-11-19). La URL candidata `s001.pdf` dio 404 según el inventario. El registro LAPSE:2021.0468 respondió 429 en tres intentos el 2026-11-19. Un buscador web confirma que el registro existe y enlaza el mismo DOI, pero no muestra sus archivos. Si incluye un suplemento sigue **pendiente**.
- **Impacto:** no hay pares t–C. Digitalizar introduce incertidumbre que debe cuantificarse y, según el encargo, aún no se hace.
- **Pregunta:** ¿existen datos tabulados de los autores o un suplemento en LAPSE?

### B2 · P1 · Las curvas continuas de la Figura 5 son ajustes por condición
- **Evidencia:** en §4.3, Smax y *a* se estiman en cada condición (C0, Q, Lb) minimizando la distancia con su propia curva medida, y la Tabla 8 da el SSR de cada ajuste. KL queda fijado desde batch a 25 °C.
- **Impacto:**
  - Solo los marcadores experimentales serían observaciones; las líneas no lo son.
  - Los parámetros de la Tabla 8 están ajustados con todas las curvas. Usarlos para "predecir" cualquiera de ellas es circular.
  - Una partición futura debe re-estimar con las condiciones de calibración y no usar la Tabla 8 para la condición de prueba.

### B3 · P1 · Velocidad de la Tabla 7 y convenciones
- **Evidencia:** la Tabla 7 da u0 = 2,15e-4 y 6,45e-4 m/s.
- **Conversión DERIVED:** Q/A = 7,52e-5 y 2,26e-4 m/s. Dividido por φ = 0,35 da 2,148e-4 y 6,445e-4, lo que coincide con la Tabla 7. Por tanto, el "u0" de la Tabla 7 es la velocidad **intersticial**, no la superficial `u` de PyFAST.
- **Masa:** ρ_b·A·Lb da 2,433, 4,865 y 7,298 g, coherente con ms = 2,43, 4,86 y 7,29 g.
- **Impacto:** usar u0 como u superficial triplicaría el caudal efectivo.
- **Porosidad y densidad:** φ = 0,35 se usa como porosidad del lecho en su modelo macroscópico, sin método de medida. Si es interpartícula, ρ_p = 907,7 kg/m³ (DERIVED), pero la base seca sigue sin saberse. El MIP de la Figura 2c-d mide la porosidad interna del grano, que no es ε.

### B4 · P1 · Lecho parcial, relleno y modelo de los autores
- **Evidencia:** la columna mide L = 6,65 cm y el lecho ocupa solo Lb (1,86 a 5,58 cm). Se desconoce el relleno del resto (Figura 1b, "Packing material").
- **Modelo de los autores:** incluye dispersión con F, k y aL (Tabla 7) y una cinética de Langmuir con *a* dependiente de C. No equivale a LDF/HSDM de PyFAST.
- **Impacto:** el volumen muerto y la dispersión del relleno afectan la primera ruptura. Los parámetros cinéticos de los autores no se pueden trasladar como k_LDF.
- **Pregunta:** ¿qué ocupa el resto de la columna? ¿Hubo ensayo de trazador?

### B5 · P2 · Correspondencia entre curvas y paneles
- **Evidencia:** hay 8 condiciones en la Tabla 8 y 3 paneles. Las condiciones Lb = 1,86 cm con C0 = 100 aparecen probablemente en dos paneles, lo que es una *interpretación* a confirmar visualmente.
- **Ejes:** sus unidades no pudieron verificarse porque el renderizado del PDF no está disponible en este entorno.
- **Impacto:** si se digitaliza, se debe evitar contar dos veces la misma curva.

### B6 · P2 · Analítica
- **Evidencia:** UV-vis con fracciones de 7 mL. No se declaran LOD/LOQ, linealidad a 100-200 mg/L (dilución) ni réplicas.
- **Impacto:** el modelo de error no es construible sin supuestos.

---

## C. Quitosano GCLCB / MB (`03_…`, 10.5281/zenodo.3452554)

### C1 · P0 · Las tablas de magnitudes derivadas son internamente incoherentes
- **Volumen efluente:** Veff ≠ Q·tt en todas las filas. En H = 1 cm se publica 410 mL frente a 825 mL calculados, y en Q = 10 mL/min, 560 mL frente a 3800 mL.
- **Masa alimentada:** m_total ≠ C0·Q·tt/1000. En H3/Q5/C10 se publica 211,08 mg frente a 21,25 mg calculados (factor de unos 10).
- **Balance imposible:** q_total > m_total en H = 2 cm (184,58 > 162,00) y en C0 = 12 (279,58 > 235,63).
- **Thomas:** el q0 de la Tabla 4 (unos 4 mg/g) es incompatible con qe(exp) de la Tabla 1 (90 a 225 mg/g).
- **Impacto:** las tablas no pueden servir de comprobación ni de restricción. El balance de masa publicado no cierra.

### C2 · P0 · Contradicción de alturas: precisada
- **Inventario previo:** decía que había cachés con 2/4/6 cm frente a 1/2/3 cm del texto.
- **Precisión:** `word/charts/chart2.xml` (rId27) está anclado en la **Figura 17** (Adams–Bohart, eje "ln[C/C⁰]"), no en la Figura 8. Sus series rotuladas 4, 6 y 2 cm tienen un número distinto de x e y (21/17, 19/16, 17/14) y valores ln > 0 (C > C0).
- **Figura 8:** la figura de alturas (1/2/3 cm) es un raster (`media/image10.png`) sin caché.
- **Observación adicional:** el vector x de la serie "6 cm" es idéntico al de la serie "5 mL/min" de `chart1`. Esto sugiere, como *interpretación*, que "6 cm" corresponde a la condición H3/Q5/C10, pero no se resuelve.
- **Impacto:** la caché de la Figura 17 es una transformación linealizada con defectos de alineación, no una curva de ruptura.

### C3 · P1 · La caché de la Figura 9 es coherente en rótulos pero no está verificada
- **Evidencia:** `chart1.xml` (rId19, Figura 9) contiene las series "5", "10" y "15 mL/min" con 19, 22 y 18 puntos C/C0–t, enlazadas a un XLSX externo local del autor que no está publicado (OLE `TargetMode="External"`).
- **Coincide con la Tabla 2:** el tt (C/C0 ≈ 1 a 425, 380 y 350 min).
- **No coincide con la Tabla 2:** el tb. La caché da unos 154, 102 y 76 min frente a 130, 80 y 70 publicados.
- **Otros defectos:** la serie de 10 mL/min tiene x = 0 duplicado y hay valores de C/C0 > 1.
- **Impacto:** es la única fuente numérica de quitosano, pero su procedencia (archivo externo de trabajo) y su discrepancia con la tabla impiden admitirla como medición.
- **Pregunta:** ¿existe el libro de datos original y cuál es la serie definitiva?

### C4 · P1 · Faltan masa seca, densidad y porosidad
- **Masa:** no se declara. Solo el cociente q_total/qe (0,82, 1,19, 1,24 g, …) que, por C1, no es fiable.
- **Estado de las perlas:** se guardan húmedas ("soaked in deionized water until further use"). El diámetro de 4,00 ± 0,02 mm no indica si es húmedo o seco.
- **Impacto:** no hay base seca, ρ_b ni ε. Con perlas de 4 mm y una columna de 5 cm, la relación D/dp = 12,5 y la altura de 1 cm (2,5 partículas) cuestionan la hipótesis de continuo 1D y de lecho uniforme.

### C5 · P1 · Independencia
- **Evidencia:** H3/Q5/C10 es la misma fila en las Tablas 1, 2 y 3, y hay 7 condiciones únicas. No se informan réplicas.
- **Impacto:** una sola corrida de referencia aparece en tres series.

### C6 · P2 · Errores de rótulo
- **Evidencia:** los pies de las Figuras 11, 14 y 17 dicen "inlet flow rate 5 mg/L". El texto dice "181.08 mg/g" y la Tabla 1, 181,04.

---

## D. Fuentes fuera del dominio experimental acuoso

| ID | Estado | Motivo y requisitos para un uso posterior |
|---|---|---|
| RUPTURA | OUT_OF_DOMAIN | Gas a 473 K y 5 bar, mezcla binaria 2mC4/2mC5 en MFI, datos experimentales secundarios (Jolimaitre et al.). Archivos de 2 columnas sin cabecera. En `break_2mC4_exp` la y alterna valores bajos y altos (0,039, 1,235, 0,058, 1,729…), lo que podría indicar series intercaladas, y llega a 1,77. Una sola corrida de mezcla, no dos ensayos. Solo serviría para un futuro modelo gaseoso multicomponente. |
| Ogata–Banks | ANALYTICAL_REFERENCE_ONLY | Solución cerrada ADE con frontera de concentración en un dominio semiinfinito. Para comparar con PyFAST (frontera de flujo de Danckwerts, dominio finito) hay que alinear la frontera o usar su versión de flujo, y cuantificar el efecto del dominio finito para Pe dado. No verifica HSDM. |
| PSDM/EPA | SIMULATED_REFERENCE_ONLY | 17 series de salida de modelo. `multi_*` es multicomponente (competencia) y `addesigns_single` y `*_rhine` incluyen correlaciones de ensuciamiento. Los casos `optimize_*` de `tce_curves.csv` usan k y 1/n ajustados (`tce_params.csv`), así que son salidas de ajuste. Los ceros de plantilla no son observaciones. |

**Requisitos para una comparación numérica PSDM–PyFAST (sin ejecutar motores):**
- seleccionar solo casos monocomponente sin ensuciamiento;
- extraer todos los parámetros de `columnSpecs` y `Properties` con sus unidades;
- mapear la difusión de poro y superficie de PSDM a HSDM (D_s) y suprimir la de poro, o declarar la discrepancia;
- alinear la isoterma de Freundlich (unidades de K y 1/n), las fronteras, las condiciones iniciales y los tiempos de salida;
- fijar las tolerancias numéricas (`RTOL, ATOL = 1e-6, 1e-9` en `generate_tce.py`).

Una coincidencia así sería **verificación entre implementaciones**, no validación física.

---

## E. Transversales

1. **Licencias.** Son las reportadas por el inventario y por la evidencia local: CC-BY-4.0 en `metadata.json` de los registros Zenodo y en el `<license>` del XML MDPI. La ficha Zenodo de MAR2PROTECT, consultada hoy, sigue indicando CC-BY-4.0. **No es una revisión jurídica.** No se ha verificado el material de terceros. Las figuras republicadas o los datos secundarios (RUPTURA → Jolimaitre) requieren revisar su atribución. No se afirma permiso de redistribución.
2. **Metadatos personales.** `docProps/core.xml` del XLSX y las rutas OLE del DOCX contienen correos o nombres de usuario de los autores. No deben propagarse a artefactos derivados.
3. **Incidente de proceso de esta revisión.** Por un `cd` fallido se creó y se borró inmediatamente `datasets_benchmark_pyfast/mar_formulas.txt` (76 bytes, solo un mensaje de error de Python). No se modificó ningún otro archivo de PyFAST. Los hashes de los originales coinciden con `00_Inventario/manifest_sha256.csv`.

# E04: revisión integrada con salvedades

Revisión del 2026-11-19 (estado de entonces: NOT_READY, E04 BLOCKED_METADATA).
Banana peel/MB era el primer candidato. Actualización: las curvas candidatas se
importaron después y se usaron en las campañas C-A y C-B; resultados en
[estado científico](scientific_status.md).

## Trazabilidad

Se archivaron byte por byte los cuatro entregables y el manifiesto de delegación:
[registro de importación](../audit/claude_e04_20261119/IMPORT_MANIFEST.json).
La [matriz original](../audit/claude_e04_20261119/E04_METADATA_MATRIX.csv) tiene
24 registros y 60 columnas: 18 condiciones acuosas bloqueadas, un grupo gaseoso,
una referencia analítica y cuatro grupos simulados. No son 24 ensayos independientes.

Antes de integrar coincidieron 7/7 hashes de entrada y 5/5 hashes/tamaños de fuentes.
Se comprobaron hechos críticos en XML/XLSX/DOCX, sin ejecutar `_aux` ni motores.
No se certificó cada afirmación ni se determinaron licencias. Los auxiliares no
se incluyen. El manifiesto explica las bases de rutas y los localizadores abreviados.

Claude declara creación y eliminación accidental de `mar_formulas.txt` bajo datos.
Actualmente no está presente; no corresponde afirmar ausencia absoluta de escrituras.
Los originales comprobados coinciden en hash. Esta integración no altera datasets.

El [registro canónico](../benchmarks/data_catalog/E04_REVIEW.json) y esta página
incorporan las salvedades; los originales conservan su redacción histórica.

## Conclusiones revisadas

- **Banana:** mejor documentado, pero bloqueado documental y físicamente: faltan
  observaciones, base seca, definición/medida de porosidad y volumen muerto.
  Las velocidades derivadas no son unidades del eje temporal: las unidades de los
  ejes de Figura 5 siguen pendientes. No configurar automáticamente rho_p a partir
  de rho_b/(1-epsilon) sin resolver sus hipótesis.
- Sus ocho condiciones forman un diseño parcialmente cruzado: 2 caudales × 3
  alturas a C100, más dos a C200; no un factorial completo 2×3×2. Lote UNKNOWN.
- La partición propuesta es DRAFT_NOT_FROZEN. C200 queda fuera del ajuste pero
  aparece en desarrollo: no es una concentración totalmente no vista. Confirmar
  curvas duplicadas entre paneles. No reutilizar ajustes por condición de Tabla 8
  para predecir esa misma condición ni promedios que incluyan la prueba.
- **MAR:** 1400 g y 4400 mL son interpretaciones, no correcciones autorizadas.
  Mezcla frente a ensayos separados sigue desconocido. Las discrepancias numéricas
  requieren aclaración; no se atribuye edición deliberada, copia o mala conducta.
- **Quitosano:** cachés 2/4/6 cm corresponden a Figura 17, Adams–Bohart; no se
  admiten como ruptura primaria. Persisten desalineación x/y y discrepancias de masa.
- **RUPTURA:** mezcla gaseosa fuera del dominio acuoso actual.
- **Ogata–Banks:** referencia analítica, no observación; alinear fronteras/dominio.
  E01-B ya aporta una referencia finita compatible para su propio alcance.
- **PSDM:** salidas simuladas, no validación experimental. Hay casos sin ensuciamiento;
  `tce_curves` usa influente variable. El mapeo con HSDM también debe reconciliar
  almacenamiento acuoso intrapartícula y bases físicas, no solo difusión de poro.

No se digitalizó, ajustó ni simuló ningún dataset. La matriz es texto léxico y no
se convirtió automáticamente a configuraciones del solver.

## LAPSE pendiente

Usuario e informe comunican tres intentos HTTP 429, agrupados en dos entradas
narrativas, sin tres registros HTTP brutos independientes. Codex no volvió a
consultar [LAPSE:2021.0468](https://psecommunity.org/LAPSE:2021.0468).
La coincidencia de registro/autores/DOI se conserva como búsqueda reportada por
Claude; la lista de archivos no se verificó aquí. Suplemento: **UNKNOWN**.

[Índice](index.md) · [Preparación de datos](data_preparation.md) ·
[Estado científico](scientific_status.md)

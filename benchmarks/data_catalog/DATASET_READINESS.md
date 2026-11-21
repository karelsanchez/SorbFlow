# Catálogo preparatorio de datos benchmark SorbFlow

Actualización de integración: la revisión Claude de 2026-11-19 está archivada en
`audit/claude_e04_20261119/`. El registro `E04_REVIEW.json` y `docs/e04_integration.md`
incorporan las salvedades de Codex. Decisión NOT_READY; banana peel es candidato
condicionado. La descripción siguiente se conserva como snapshot anterior.

Fecha del contexto: **2026-11-19**. Raíz inspeccionada solo en lectura:
`D:\PyFAST\datasets_benchmark_pyfast`. Las marcas UTC precisas de la inspección
figuran en INVENTORY.json; no sustituyen fechas de descarga originales.

## Resultado del snapshot

Se observaron **58 archivos**, 16 directorios y **78 152 351 bytes**. La enumeración
no aplica `.gitignore`: incluye `04_RUPTURA/Data_RUPTURA.zip` de 67 632 758 bytes,
que no se abrió, extrajo ni volvió a hashear. Se registran rutas relativas, tamaños,
extensiones, marcas de modificación y posibles nombres temporales.

Se leyeron README/inventarios locales y pequeñas evidencias de licencia/cabeceras.
Solo se calcularon SHA-256 de **10 sentinelas pequeños**: `README.md` y archivos de
`00_Inventario`, comprobando tamaño/mtime antes y después de cada lectura.
No se recalcularon hashes de originales grandes ni se verificaron nuevamente
los checksums publicados o el CRC reportados por la auditoría previa.

No aparecieron nombres `.part`, `.partial`, `.crdownload`, `.tmp`, `.aria2` o
equivalentes, ni cambios de tamaño/mtime entre los dos recorridos de esta inspección.
**Esto no demuestra que todas las descargas hayan terminado ni que los datos sean
inmutables.** No se tocaron descargas activas, movieron archivos, ejecutaron modelos
externos ni alteraron originales. No se hizo verificación web nueva.

## Preparación por fuente

Los estados siguientes proceden de `README.md`,
`00_Inventario/inventario_datasets.csv` y
`00_Inventario/curvas_utilizables_y_pendientes.csv`; no repiten una validación.

| Fuente | Papel candidato | Bloqueos principales registrados localmente |
|---|---|---|
| MAR2PROTECT | Ajuste exploratorio y posible validación acuosa después de resolver condiciones | Etiquetas kg/g y L/ml contradictorias; tercer bloque HPLC DCF; medias discrepantes; geometría/partículas/porosidad sin verificar; LOQ/2 y censura; tres analitos no prueban tres ensayos independientes |
| Banana peel MB | Datos de autores o digitalización documentada, con incertidumbre | Artículo PDF/XML, sin tabla numérica separada admitida; suplemento candidato no localizado; no tratar curvas ajustadas como observaciones |
| Chitosan fixed-bed | Datos de autores o digitalización documentada | Caches de gráficos Word 2/4/6 cm contradicen texto 1/2/3 cm; no se admitieron como curvas verificadas |
| RUPTURA | Referencia fuera de dominio; futura comparación de modelo gaseoso compatible | Mezcla binaria a 473 K/5 bar; datos experimentales secundarios; unidades de ejes y atribución a confirmar; no valida modelo acuoso monoespecie |
| Ogata–Banks | Referencia analítica para verificación ADE | No experimental; alinear dominio semiinfinito y condiciones de frontera con el caso numérico; no verifica HSDM por sí sola |
| PSDM/EPA | Comparación numérica entre implementaciones, previa alineación | Salidas simuladas, no observaciones; poro/superficie/ensuciamiento pueden diferir; unidades/configuración/fronteras pendientes; ceros de plantillas no son curvas experimentales |

El catálogo local declara **3 series acuosas con reservas**, **2 gaseosas secundarias**
y **17 series simuladas PSDM**. No son 22 experimentos independientes. El estado
heredado y conservado es **0 curvas listas para validación física independiente
del SorbFlow actual**. No se ha declarado ningún dataset validado en esta preparación.

## Licencia y procedencia

DATASET_REGISTRY.json conserva seis fuentes, DOI/URLs y evidencia local de licencia
con estado **reported_by_local_inventory**, no como revisión jurídica/web nueva.
Las cuatro colecciones MAR2PROTECT, banana, quitosano y RUPTURA se reportan CC-BY-4.0;
PSDM/EPA se reporta MIT y hay textos locales de licencia. Para Ogata–Banks, el
inventario reporta dominio público USGS, pero la política oficial no está conservada
localmente y esta inspección no la volvió a consultar. Revisar aportes de terceros,
atribución y alcance antes de redistribuir; una licencia de software no convierte
automáticamente salidas simuladas en observaciones experimentales.

Los hashes previos y afirmaciones de integridad permanecen en sus manifiestos
originales. Los nuevos sentinelas solo identifican la documentación usada para este
snapshot, no certifican la descarga científica ni la exactitud de sus declaraciones.

## Entrenamiento y validación

No se asignaron observaciones a entrenamiento/validación. Para fuentes acuosas
candidatas, resolver unidades, identidad de ensayos, lotes y censura; después fijar
por adelantado una partición por **ensayo/condición completos**, evitando repartir
puntos temporales de la misma curva entre ajuste y validación. Ogata–Banks y PSDM
son referencias analíticas/simuladas: esa partición experimental no corresponde.
RUPTURA no se admite al ajuste/validación acuosos actuales.

Esta colección externa tampoco identifica automáticamente las cuatro materias
primas de la investigación del usuario: su estudio debe conservar catálogo,
recetas, protocolos y permisos propios, separado del framework genérico.

## Siguientes pasos permitidos de preparación

1. Mantener este catálogo fuera del directorio raw y conservar las fuentes intactas.
2. Confirmar estabilidad/completitud de descargas antes de futuras lecturas extensas;
   conservar los intentos fallidos y la ausencia de suplementos.
3. Preparar mapeos explícitos de columnas/unidades y banderas de reserva sin corregir
   originales, imputar LOQ/2 como medición exacta ni promediar condiciones ambiguas.
4. Priorizar ADE analítica para verificación de transporte y PSDM para comparación
   numérica modelada, manteniéndolos separados de evidencia experimental.
5. Resolver los bloqueos MAR2PROTECT, banana y quitosano antes de admitirlos a un
   protocolo confirmatorio. No afirmar generalización química ni validación E02–E05
   por la mera disponibilidad de estos archivos.

Entregables: INVENTORY.json (snapshot/sentinelas/temporales) y
DATASET_REGISTRY.json (seis fuentes, dominios, roles candidatos, licencias reportadas
y bloqueos). No se ejecutaron algoritmos científicos ni software descargado.

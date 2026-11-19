# Preparar datos y configuraciones

[Inicio](index.md) · [Primeros pasos](getting_started.md) · [Estado científico](scientific_status.md)

## Identidad, unidades y procedencia

La [revisión integrada E04](e04_integration.md) conserva cero curvas admitidas y
prioriza banana peel solo de forma condicionada. No transforma la matriz de
metadatos en entradas del solver ni corrige unidades por suposición.

Conserve originales sin editar y genere derivados identificados por separado.
Registre especie, material/receta, lote, protocolo, tiempo, concentración, incertidumbre,
límites analíticos, geometría, flujo, temperatura y base de masa seca. No deduzca
masa seca a partir de masa húmeda sin humedad medida. Las unidades internas son SI;
los nombres de campo distinguen kg de soluto y kg de adsorbente.

`Species`, `Bed`, `Operation`, `SimulationConfig` y `BatchConfig` se documentan en la
[API](../API_REFERENCE.md). Las fábricas dimensionales convierten mediante Pint;
no se interpreta ppm como mg/L ni se convierte molaridad sin una regla explícita.

## Importar una curva CSV

Ejemplo **sintético** de formato, no datos del laboratorio:

```csv
time_min,C_mg_L,sd_mg_L
0,0,0.1
1,2,0.2
2,4,0.2
```

La correspondencia de columnas y unidades siempre es explícita:

```python
from pyfast.io import load_breakthrough_csv

observations = load_breakthrough_csv(
    "datos/mi_ensayo.csv",
    experiment_id="ensayo-identificado",
    species_name="especie-identificada",
    time_column="time_min",
    concentration_column="C_mg_L",
    time_unit="min",
    concentration_unit="mg/L",
    std_column="sd_mg_L",
    std_unit="mg/L",
)
```

El importador devuelve `Observations` en SI y una huella de los bytes originales.
No ordena, interpola, promedia ni elimina filas. Rechaza cabeceras duplicadas,
registros malformados, números no finitos y tiempos no crecientes. Las columnas
adicionales permanecen en el archivo fuente; no se añaden al objeto de observaciones.
Valores censurados como ND o `<LOQ` requieren un tratamiento/modelo de error específico:
no sustituirlos silenciosamente por cero o tomarlos como medidas exactas.

## Materiales y mezclas sin un límite fijo

`BlendComponent` y `AdsorbentBlend` describen N componentes con identificadores
distintos y fracciones másicas secas positivas que suman uno. Una receta documenta
preparación; **no calcula propiedades por mezcla de parámetros**. Ajuste/evalúe las
isotermas y resistencias adecuadas para la receta y condiciones reales.

Los cuatro materiales iniciales pueden constituir un caso de estudio separado del
framework. Cambiar un nombre no demuestra transferencia entre contaminantes; metales,
colorantes y compuestos orgánicos pueden necesitar química y datos diferentes.

## Separar clases de evidencia

| Insumo | Papel posible | No debe confundirse con |
|---|---|---|
| Casos JSON versionados | Demostración sintética y comprobación de la API | Ensayo observado |
| Soluciones analíticas y referencias discretas | Verificación numérica con IC/BC compatibles | Validación experimental |
| Salidas de otro software | Comparación tras alinear modelos y unidades | Mediciones independientes |
| Observaciones autorizadas y metadatos completos | Ajuste o validación según partición previa | Datos validados por estar descargados |

El [catálogo de fuentes](../benchmarks/data_catalog/DATASET_REGISTRY.json) y la
[preparación de datos candidatos](../benchmarks/data_catalog/DATASET_READINESS.md)
mantienen **0 curvas listas** para validación física; E04 permanece BLOCKED_METADATA.
Los originales de `datasets_benchmark_pyfast/` son una colección separada y no deben
modificarse para hacer pasar una prueba.

Particione por ensayo/condición completos antes de evaluar predicciones, conservando
réplicas y lotes. Repartir tiempos de la misma curva entre ajuste y validación produce
dependencia entre conjuntos. Consulte el [protocolo experimental](../PAPER_ENVSOFT/EXPERIMENTAL_VALIDATION.md).

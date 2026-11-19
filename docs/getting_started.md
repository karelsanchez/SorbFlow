# Primeros pasos

[Inicio](index.md) · [Datos](data_preparation.md) · [Estado científico](scientific_status.md)

## Entorno

Trabaje desde la raíz del repositorio con **Python 3.11 o superior**. Los comandos
`python -m` de esta guía suponen un entorno virtual activado; compruebe el ejecutable
en lugar de confiar en el Python global. En PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable); print(sys.version)"
python -m pip check
python -m pyfast --help
```

Para una instalación nueva en un entorno compatible:

```powershell
python -m pip install -e .
```

Los extras `[dev]`, `[optimize]` y `[parquet]` añaden herramientas de desarrollo,
NSGA-II y PyArrow respectivamente. Por ejemplo, para desarrollar y probar esas
opciones: `python -m pip install -e ".[dev,optimize,parquet]"`. El núcleo de simulación
no necesita el ejecutable FAST ni una extensión comercial.

## Ejecutar casos sintéticos

Estos tres archivos están versionados y **no contienen observaciones experimentales**:

- [Batch lineal LDF](../examples/batch_ldf.json).
- [Columna Langmuir/LDF](../examples/column_ldf.json).
- [Columna Langmuir/HSDM](../examples/column_hsdm.json).

```powershell
python -m pyfast batch examples/batch_ldf.json --output runs/primer_batch
python -m pyfast column examples/column_ldf.json --output runs/primera_columna --cells 40
python -m pyfast column examples/column_hsdm.json --output runs/primera_hsdm --cells 40 --radial-cells 12
```

Cada carpeta de salida debe ser nueva: no se sobrescribe una simulación anterior.
Esas mallas son ejemplos de uso, no una resolución suficiente para toda decisión.
Refine mallas y tolerancias según el [plan de validación](../VALIDATION_PLAN.md).

## Leer los resultados

Cada simulación exporta:

- `result.json`: configuración SI, opciones, perfiles, manifiesto y diagnósticos.
- `timeseries.csv`: salida e inventario/entradas/salidas/residuo de masa, con unidades.
- `files.sha256.json`: integridad de esos archivos exportados.

El resultado de columna representa celdas finitas; HSDM conserva además los perfiles
radiales. Un balance cerrado o un integrador exitoso no demuestra precisión espacial
ni validez experimental. Consulte los límites en [estado científico](scientific_status.md).
La [API](../API_REFERENCE.md) explica cómo usar resultados y cantidades desde Python.

Para la interfaz de navegador, vea [interfaz web](web_interface.md). Su entrada es
opcional y usa los mismos esquemas y modelos; no cambia las hipótesis físicas.

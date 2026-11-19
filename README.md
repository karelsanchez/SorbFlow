# PyFAST

Biblioteca independiente para futura modelación de adsorción en lecho fijo.
**Fundación 0.1.0.dev0: unidades y contratos de datos. No incluye solver. No está
validada para simulación, dimensionamiento o predicción experimental.**

El repositorio no contiene código ni ejecutables FAST y no está afiliado a sus autores.
El ZIP experimental original permanece intacto en Descargas.

## Inicio en Windows

Python >=3.11 (el `python` global de este equipo es 3.7 y no es adecuado).
Desde `D:\PyFAST`, usando el intérprete 3.11 instalado o uno compatible:

```powershell
& 'C:\Users\Karel\AppData\Local\Programs\Python\Python311\python.exe' -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e '.[dev]'
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe examples\configuration.py
```

El entorno local ya preparado evita modificar Python global. Si el launcher `py`
selecciona Python 2.7 en este equipo, usar explícitamente el ejecutable 3.11.
La API inicial se documenta en [API_REFERENCE.md](API_REFERENCE.md).

## Diseño y evidencia

- [Arquitectura](ARCHITECTURE.md)
- [Modelo matemático](MODEL_SPECIFICATION.md)
- [Plan de validación](VALIDATION_PLAN.md)
- [Auditoría IP/licencias](IP_LICENSE_AUDIT.md)
- [Roadmap](DEVELOPMENT_ROADMAP.md)
- [Hallazgos y estado de entrega](AUDIT_REPORT.md)

`audit/fast_inventory.json` registra hashes e inventario de metadatos. Los esquemas
contienen parámetros de Langmuir/Freundlich y LDF/HSDM, sin calcular esos modelos.
`examples/configuration.py` contiene datos sintéticos, sin resultados experimentales.
Los módulos científicos futuros están reservados y sin algoritmos.

## Calidad

```powershell
& .\.venv\Scripts\python.exe -m pytest --cov=pyfast --cov-report=term-missing --cov-fail-under=90
& .\.venv\Scripts\python.exe -m ruff check .
& .\.venv\Scripts\python.exe -m mypy
& .\.venv\Scripts\python.exe -m build
```

La matriz CI propuesta todavía necesita ejecutarse en un remoto. El snapshot local
en `audit/requirements-local.txt` fija las versiones instaladas, pero no sustituye
un lock multiplataforma con hashes para una publicación reproducible.

## Licencia

Pendiente de decisión del titular para código nuevo; propuesta BSD-3-Clause.
El metadato `LicenseRef-Proprietary` refleja que aún no existe una concesión pública.
Véase LICENSE.md. No publicar en PyPI ni redistribuir recursos FAST antes de resolver
los requisitos correspondientes. El nombre de distribución es provisional.

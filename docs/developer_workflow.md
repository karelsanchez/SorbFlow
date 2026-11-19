# Desarrollo y comprobaciones

[Inicio](index.md) · [Primeros pasos](getting_started.md) · [Estado científico](scientific_status.md)

## Trabajar en el repositorio

Use el entorno virtual activado y comandos relativos desde la raíz. Mantenga código,
datos originales, resultados y componentes comerciales separados. No ejecute código
descargado ni altere simulaciones ajenas para completar un benchmark.

```powershell
python -m pip check
python -m pytest
python -m ruff check .
python -m mypy
python -m scripts.check_doc_links
python -m build
```

El [comprobador de documentación](../scripts/check_doc_links.py) verifica destinos
locales de `docs/`, incluidas imágenes y nombres codificados. No hace solicitudes
de red ni valida fragmentos. Excluye datos raw, scratch/runs y árboles históricos;
primero rechaza cualquier escape fuera del repositorio. No recorre ni reescribe
los documentos originales descargados. Sus [pruebas](../tests/test_doc_links.py)
usan repositorios de ejemplo pequeños.

El [flujo de comprobación del proyecto](../scripts/project_checks.py) reúne las
comprobaciones de ingeniería. Consulte su ayuda y las instrucciones locales del
repositorio antes de cambiar el flujo:

```powershell
python -m scripts.project_checks --help
python -m scripts.project_checks --output runs/comprobacion_nueva
```

## Añadir modelos o capacidades

1. Fijar ecuaciones, unidades, dominio e IC/BC antes de implementar.
2. Mantener contratos públicos y esquemas versionados; no añadir parámetros de una
   materia prima como constantes universales del solver.
3. Añadir referencias independientes y pruebas de límites/conservación/convergencia
   apropiadas. Una prueba que solo repite la implementación no verifica su física.
4. Registrar los fallos con mensajes explícitos; no ocultar pérdida de masa mediante
   clipping ni promover un ajuste no convergente a resultado exitoso.
5. Actualizar [API](../API_REFERENCE.md), [modelo](../MODEL_SPECIFICATION.md),
   [validación](../VALIDATION_PLAN.md) y documentación de uso cuando cambie el contrato.
6. Conservar configuraciones y evidencias que permitan repetir la evaluación.

## Smoke frente a experimento confirmatorio

El [arnés de smoke](../PAPER_ENVSOFT/reproduce_smoke.py) reproduce referencias/demos
sintéticos. Puede ejecutar sus dos tareas independientes y reutilizar tareas
completadas solo cuando coincidan fuentes, entorno y hashes:

```powershell
python -m PAPER_ENVSOFT.reproduce_smoke --output runs/docs_smoke --jobs 2
python -m PAPER_ENVSOFT.reproduce_smoke --output runs/docs_smoke --jobs 2 --resume
```

El destino nuevo es obligatorio en la primera ejecución. `--resume` no es un checkpoint
del integrador ni ejecución distribuida; un reintento conserva datos anteriores.
Esto no cierra E01 ni ejecuta E02–E05. Los estudios confirmatorios requieren congelar
el [protocolo](../PAPER_ENVSOFT/BENCHMARK_PROTOCOL.md), los datos/particiones y los criterios
antes de evaluar éxito.

## Entregas reproducibles

Registre revisión Git, versiones, configuración, mallas/tolerancias, semillas, escenarios,
unidades, hashes y logs. Use carpetas nuevas bajo `runs/`; no versione entornos ni
resultados voluminosos como parte del paquete. Compruebe la instalación desde wheel
fuera del checkout antes de una release.

Consulte [licencias](../IP_LICENSE_AUDIT.md), [reproducibilidad del artículo](../PAPER_ENVSOFT/REPRODUCIBILITY_CHECKLIST.md)
y [roadmap](../DEVELOPMENT_ROADMAP.md). No publique licencias, DOI o resultados todavía
no otorgados/producidos. El estado científico debe reflejar la evidencia, incluso
cuando todas las comprobaciones de software pasen.

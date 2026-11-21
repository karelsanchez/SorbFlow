# Preparación técnica para una revisión futura

Este directorio reúne una descripción del software y una herramienta de inventario.
No presenta una solicitud, determina derechos, acredita originalidad completa ni
ofrece instrucciones jurídicas para una jurisdicción. No se ha enviado información
a ninguna entidad. Autoría, titularidad y jurisdicción siguen sin determinarse.

## Material de revisión

- [Descripción técnica](TECHNICAL_DESCRIPTION.md): arquitectura y alcance implementado.
- [Campos pendientes](REVIEW_FIELDS.json): valores nulos que debe resolver la revisión humana.
- [Herramienta](../scripts/software_manifest.py): inventario reproducible de texto seleccionado.
- [Auditoría existente](../IP_LICENSE_AUDIT.md) y [licencia actual](../LICENSE.md).
- [Estado científico](../docs/scientific_status.md): evidencia y pendientes separados.

## Preparar una instantánea local

Desde la raíz del repositorio, utilice su entorno Python 3.11 o posterior:

```powershell
New-Item -ItemType Directory -Force .work/registration_review
.venv/Scripts/python.exe scripts/software_manifest.py --output .work/registration_review/snapshot_01.json
.venv/Scripts/python.exe -m pytest tests/test_software_manifest.py
```

El directorio padre debe existir; el archivo de salida debe ser nuevo. La herramienta
no sobrescribe archivos, no altera fuentes o datos y no publica ni registra nada.
Use otro nombre para una nueva instantánea. La salida no puede estar en carpetas de
fuentes, documentación, datos, recursos, dependencias o control de versiones.

`content` es determinista para el mismo texto seleccionado, metadatos y estado Git.
`content_sha256` usa JSON UTF-8 canónico con claves ordenadas, sin espacios y
`ensure_ascii=False`. `generation` contiene fecha UTC y versión de Python/plataforma;
queda fuera de esa huella. Los archivos se registran con ruta relativa, bytes y SHA-256.
No se importan módulos del proyecto ni se vuelcan entornos, secretos, remotos o
configuraciones. Git registra HEAD y si hay cambios seguidos; no consulta archivos
sin seguimiento. El inventario sí incluye textos elegibles sin seguimiento.

La selección usa raíces/extensiones explícitas y excluye enlaces/junctions, datos
CSV, binarios, recursos, descargas, auditorías generadas, resultados y entornos.
Por ello **no constituye una copia completa, SBOM, prueba de autoría o archivo de
preservación**. Un texto elegible puede contener material de procedencia pendiente:
su inclusión no lo convierte en propiedad de SorbFlow. No modificar entradas mientras
se genera el inventario; no existe una instantánea atómica del sistema de archivos.

Antes de cualquier presentación futura, una persona responsable debe revisar los
archivos seleccionados, procedencia, contribuciones, contratos, datos, dependencias,
avisos y campos nulos. La revisión de derechos y los requisitos formales quedan
fuera de esta herramienta. Conservar el manifiesto junto al commit y la evidencia
de pruebas correspondiente; un hash identifica bytes, no acredita sus derechos.

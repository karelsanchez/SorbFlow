# Documentación navegable y publicación

[Inicio](index.md) · [Desarrollo](developer_workflow.md)

El sitio utiliza MkDocs con tema Read the Docs, búsqueda y navegación por tareas.
El contenido mantenido sigue siendo Markdown versionado. No se copian manualmente
dos versiones de las ecuaciones ni de la API.

## Construir y consultar localmente

Desde la raíz del repositorio:

```powershell
python -m pip install -r docs/requirements.txt
python scripts/build_docs.py
```

Abrir `.work/site/index.html` o servir `.work/site` mediante un servidor local.
Para un destino distinto: `python scripts/build_docs.py --output RUTA_NUEVA`.
La configuración usa enlaces HTML compatibles con lectura local.
Para utilizar también la búsqueda, servir el sitio por HTTP:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory .work/site
```

Abrir `http://127.0.0.1:8765` mientras ese proceso está activo. El servidor queda
limitado a este equipo; la búsqueda puede estar restringida por el navegador
cuando se abre un archivo HTML directamente.

El constructor prepara un árbol temporal que conserva las rutas relativas de
documentos y recursos. Solo copia archivos indexados en Git; las páginas nuevas
deben añadirse al índice antes de previsualizarlas. Excluye entornos, runs y
datasets externos. Las advertencias de construcción y enlaces detienen el build.

## Comprobación automática

`.github/workflows/documentation.yml` construye el sitio en pushes y pull requests
y lo guarda como artefacto. No publica en GitHub Pages ni cambia la visibilidad.
La ejecución remota solo se considera aprobada después de observarla en GitHub.

## Read the Docs

`.readthedocs.yaml` instala las dependencias y prepara las fuentes antes de
construir con `mkdocs.yml`. Tras conectar el repositorio al servicio, sus builds
pueden seguir ramas y versiones. La configuración local no crea una cuenta,
proyecto ni URL remota, ni garantiza compatibilidad del plan con repositorios privados.

La primera etapa de SorbFlow es privada: revisión de documentación como artefacto
o sitio local. La publicación abierta de código y sitio requiere que el titular
defina la licencia y la visibilidad. La versión experimental y sus límites
científicos deben mantenerse visibles en cualquier publicación.

## Qué subir al repositorio

Subir el checkout de SorbFlow mediante Git, conservando su historial. No cargar el
directorio padre completo: contiene entornos de prueba, datasets y resultados.
Los paquetes wheel/sdist se adjuntan a una release cuando se decida publicarla;
las salidas masivas se conservan como artefactos seleccionados, no como fuente.

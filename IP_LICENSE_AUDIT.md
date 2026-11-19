# Auditoría de propiedad intelectual y licencias

Fecha de revisión: 2026-11-18. Alcance técnico y de procedencia; quedan decisiones
de titularidad y autorización para revisión por los titulares y asesoría competente.

## Evidencia local

Origen: `C:\Users\Karel\Downloads\FAST2.1beta.zip`, 1,207,065 bytes.
SHA-256: `535519e5388cb74728e8cb4c3c33c230d04a4c17cc99ac36fb58c46102589f23`.
El inventario recursivo del archivo se conserva como metadatos en `audit/fast_inventory.json`.
Contiene 49 entradas: cuatro EXE, tres imágenes en bin y 42 GIF de ayuda.
No contiene fuente, LICENSE/README textual, entradas experimentales ni resultados.
La ayuda `Info.gif` se inspecciona como evidencia adicional; sus afirmaciones se
distinguen del contrato de licencia publicado. No descompilar ni extraer lógica ejecutable.

## Fuentes públicas consultadas

- [FAQ oficial](https://www.fast-software.de/faq.html): identifica CC BY-NC-ND 3.0
  y uso privado/académico; remite usos comerciales a los autores.
- [Descarga oficial](https://www.fast-software.de/download.html): declara la misma
  licencia y anuncia FAST 2.1 beta de septiembre de 2011.
- [Texto legal CC BY-NC-ND 3.0](https://creativecommons.org/licenses/by-nc-nd/3.0/legalcode):
  regula reproducción, distribución, atribución y restricción no comercial; no concede
  distribución de adaptaciones como una licencia permisiva de software.
- [Contacto oficial](https://www.fast-software.de/contact.html): autores Sebastian
  Schimmelpfennig y Alexander Sperlich. No se les ha contactado en esta tarea.

Se considera provisionalmente que la declaración web corresponde al ZIP con nombre
2.1 beta; no hay firma ni manifiesto de licencia local para autenticar ese vínculo.
No se debe tratar disponibilidad gratuita como permiso open source ni comercial.
La ausencia de aviso textual dentro del ZIP no elimina derechos.

## Decisiones para PyFAST

| Activo | Decisión actual | Pendiente |
|---|---|---|
| EXE de FAST | Permanecen en Descargas, sin copiar al repo o distribución | Permiso específico si se propone redistribución |
| Imágenes, ayuda y diseño FAST | Solo inspección, sin incluir recursos originales | Autorización para cualquier reutilización |
| Algoritmos internos | No accesibles; no afirmar auditoría o equivalencia | Fuente y autorización si se plantea revisarlos |
| Balances científicos generales | Formular independientemente y citar literatura | Completar bibliografía primaria para artículo |
| Datos experimentales | No suministrados en el ZIP | Titularidad, uso, anonimización y permiso de publicación |
| Adaptador opcional | Solo diseño, sin binarios ni invocaciones | Contrato I/O, permisos aplicables y pruebas aisladas |
| Código nuevo PyFAST | Original de esta tarea, sin derivación del binario | Titular y licencia de publicación por confirmar |

Se propone BSD-3-Clause para el core por compatibilidad con extensiones comerciales,
pero no se concede licencia en nombre de un titular aún no definido. LICENSE.md deja
esta situación explícita. El paquete se prepara técnicamente para pip; publicación y
licencia abierta definitiva son hitos posteriores. No registrar como BSD código ajeno.
Separar servicio comercial, plugins y branding del core y de datos privados.
PyFAST no afirma afiliación con FAST; revisar nombre, marca y distribución antes de publicar.

## Dependencias

Pint es la única dependencia runtime inicial; pytest/pytest-cov, Ruff, mypy, build,
setuptools y herramientas transitivas son dependencias de desarrollo o empaquetado.
Registrar versiones instaladas y metadatos de licencia en `audit/dependency_metadata.json`;
metadatos son una primera revisión, no una auditoría exhaustiva de todas las licencias
incluidas en cada wheel. No vender ni redistribuir wheels de terceros como activos propios.
NumPy, SciPy y librerías futuras deben pasar revisión de versión, licencia y mantenimiento
antes de añadirse. Mantener avisos exigidos y SBOM por cada distribución publicada.

## Riesgos abiertos y controles

1. Restricciones NC/ND: excluir activos FAST del repositorio y del sdist/wheel.
2. Identidad/versionado local no autenticado: conservar hashes y no inferir condiciones
   de licencia de otra versión. Verificar la licencia con titulares antes de uso comercial.
3. Interfaz no documentada: no prometer automatización FAST ni compatibilidad exacta.
4. Titularidad del nuevo core: resolver antes de publicación o colaboración externa.
5. Derechos sobre datasets y referencias: inventario separado; citar no equivale a
   permiso para copiar figuras, tablas o datos de terceros.

El ZIP original se verifica por hash al finalizar; no se mueve, modifica ni ejecuta.

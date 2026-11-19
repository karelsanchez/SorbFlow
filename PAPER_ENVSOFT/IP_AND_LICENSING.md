# Propiedad intelectual, disponibilidad científica y separación Open Core

Versión 0.1, consulta 2026-11-18. Registro técnico de procedencia y decisiones;
no determina titularidad universitaria ni sustituye revisión jurídica aplicable.
Fuente de la auditoría local: IP_LICENSE_AUDIT.md y audit/fast_inventory.json en la raíz.

## 1. Decisión de proyecto y condición de publicación

Estrategia propuesta por el usuario: **Apache-2.0 para el núcleo científico** y una
distribución independiente, p.ej. `pyfast-design-pro`, para capacidades empresariales.
Antes de conceder/publicar la licencia: identificar titulares, contratos universitarios,
financiación, aportaciones externas, cesiones y permisos sobre código/datos. El
metadato actual LicenseRef-Proprietary refleja que no se ha otorgado aún esa concesión;
no equivale al objetivo final ni impide seguir la investigación técnica.

El término *open* del título permanece provisional hasta que exista acceso efectivo
y licencia válida. Cambiar LICENSE y metadatos juntos, conservar autoría/avisos y
documentar la decisión. Consultar el [texto oficial Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)
para sus condiciones; no otorgar derechos que no pertenezcan al proyecto.

**Ningún algoritmo, configuración, dataset autorizado, interfaz o script indispensable
para reproducir los resultados del artículo se reservará detrás de la edición
comercial.** Los resultados principales deben correr con el core y extras abiertos
declarados. CAD empresarial, administración de proyectos y documentación técnica
pueden estar separados si no son necesarios para las afirmaciones del artículo.
Si una figura necesita un módulo comercial, modificar la frontera o el alcance
del paper, no llamar completamente abierta a la reconstrucción.

## 2. FAST original: insumo separado

El ZIP FAST 2.1 beta permanece en Descargas, sin ejecutar, copiar al repositorio ni
modificar. Su hash auditado:
`535519e5388cb74728e8cb4c3c33c230d04a4c17cc99ac36fb58c46102589f23`.
Contiene ejecutables y ayuda gráfica, no fuentes ni datos de comparación.

La [FAQ oficial](https://www.fast-software.de/faq.html) y
[descarga oficial](https://www.fast-software.de/download.html) declaran CC BY-NC-ND 3.0;
el ZIP no trae una licencia textual autónoma que autentique su procedencia/alcance.
No tratar gratuidad como permiso open source o comercial. El
[texto legal CC BY-NC-ND 3.0](https://creativecommons.org/licenses/by-nc-nd/3.0/legalcode)
no es una autorización general para adaptar/redistribuir comercialmente software.

El solver PyFAST es independiente. El adaptador FAST sigue pendiente de contrato
I/O real, versión/hash e instalación legal aportada por el usuario, condiciones
compatibles y directorios de trabajo aislados. No automatizar clics ni ejecutar
simulaciones originales para llenar una tabla de benchmarking. No redistribuir
EXE, imágenes, código o archivos de terceros como parte de PyFAST.
Si el benchmark no puede realizarse legal/técnicamente, declararlo NOT_RUN con causa;
no inventar concordancia ni presentar FAST como verdad única de validación.

## 3. Dependencias y alcance de la revisión

| Componente | Uso actual/propuesto | Obligación de preparación |
|---|---|---|
| NumPy/SciPy/Pint | Arrays, integradores y unidades del core | Versiones/licencias/avisos de cada distribución y componentes incluidos |
| pymoo | Extra opcional NSGA-II, licencia principal Apache-2.0 | No afirmar que el algoritmo sea original de PyFAST; citarlo y revisar transitivas |
| moocore | Transitiva de pymoo, LGPL-2.1-or-later declarada | Revisar condiciones de empaquetado/redistribución de la edición elegida; no omitirla del SBOM |
| PyArrow | Extra Parquet, licencia principal Apache-2.0 | Revisar avisos incluidos y declarar extra/versión |
| ezdxf | Verificación de desarrollo, MIT | No atribuir al exportador una validación mecánica por leer DXF correctamente |
| FAST y otros motores | No incorporados; comparación futura condicionada | Permisos y procedencia por separado |

Los metadatos locales están en audit/dependency_metadata.json. Son inventario inicial,
no una auditoría legal completa de todos los componentes de wheels. Para release,
crear SBOM reproducible, revisar archivos LICENSE/NOTICE efectivamente distribuidos,
conservar avisos y verificar que el modo de empaquetar componentes comerciales cumple
las condiciones aplicables. No describir todo el árbol opcional como permisivo.
Fuente primaria de licencia transitiva: [moocore](https://pypi.org/project/moocore/).

No se han descargado/copiado fuentes de competidores para construir PyFAST. Consultar
documentación o citar un paper no autoriza reproducir sus figuras, tablas o datasets.
Los balances y métodos generales se formulan y citan independientemente; una publicación
no otorga exclusividad sobre ecuaciones/métodos ni acredita una patente o marca.

## 4. Datos, colaboradores y artículos

Mantener por activo: titular/proveedor, licencia/permiso, restricciones de uso/publicación,
versión, hash y responsable. No asignar a datos universitarios una licencia elegida
solo para el código. Revisar también privacidad de metadatos y acuerdos con terceros.
Los datasets sintéticos deben etiquetarse y preservar generador/semillas; no sustituir
datos reales ausentes con simulaciones presentadas como experimentales.

Definir contribuciones humanas, revisión, atribución y política de aportaciones
antes de abrir contribuciones externas. Preparar declaraciones de financiación,
intereses y relación entre artículo metodológico/experimental con información real.
No inventar autores, afiliaciones, aprobación universitaria, DOI o permisos concedidos.

## 5. Gate de release/sumisión

No publicar un paquete descrito como Apache-2.0/open hasta resolver derechos y avisos.
No incluir FAST sin autorización compatible. No depender de un módulo comercial
para reproducir resultados centrales. No marcar acceso/DOI como disponible antes
del depósito. Estas condiciones no requieren detener formulación, pruebas o preparación
de artefactos: separan trabajo técnico autorizado de concesiones/publicación futuras.
La guía específica EnvSoft y políticas vigentes se revalidan al enviar; no se afirma
que Apache-2.0 sea una licencia exigida por la revista.

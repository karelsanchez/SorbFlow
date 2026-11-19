# Descripción técnica de PyFAST para revisión

[Preparación](README.md) · [Arquitectura](../ARCHITECTURE.md) ·
[Ecuaciones](../MODEL_SPECIFICATION.md) · [API](../API_REFERENCE.md)

PyFAST es un prototipo modular Python para adsorción acuosa en batch y columnas de
lecho fijo. Especie, adsorbente y proporciones son datos configurables; el núcleo
no fija los cuatro materiales del estudio inicial. La configuración tipada utiliza
unidades físicas SI, convenciones de masa seca y distinción entre velocidad
superficial e intersticial. El sistema de unidades convierte cantidades explícitas;
la configuración numérica requiere valores SI según su esquema.

## Componentes implementados

- `pyfast.equilibrium`: modelos lineal, Langmuir y Freundlich normalizado.
- `pyfast.simulate`: batch LDF y columna LDF/HSDM; discretización conservativa,
  dispersión axial, película y condiciones Danckwerts; integración mediante SciPy.
- `pyfast.fit`, `uncertainty` y `optimize`: ajuste, diagnósticos locales de
  identificabilidad, muestreo reproducible y NSGA-II opcional mediante pymoo.
- `pyfast.design`: geometría, Ergun, EBCT, potencia/costo parcial y exportación DXF
  de proceso. No constituye certificación mecánica.
- `pyfast.io` y `validate`: configuración, resultados y controles de balance;
  CSV/JSON y Parquet opcional para series temporales.
- API Python, CLI `pyfast` e interfaz web local opcional stdlib. La GUI utiliza
  el mismo núcleo, impone límites de recursos y crea resultados en carpetas nuevas.

El motor propio utiliza NumPy/SciPy/Pint como dependencias declaradas. Los extras
separan optimización y Parquet. No incluye ejecutables ni recursos FAST. Un adaptador
externo sigue pendiente de contrato de intercambio y condiciones compatibles.
La arquitectura prevé separar un núcleo científico y posibles extensiones comerciales;
ello no concede licencias ni determina titularidad.

## Evidencia y pendientes

Las pruebas automatizadas verifican comportamientos concretos, unidades, esquemas,
balances y referencias numéricas. [E01-A](../benchmarks/e01/README.md) documenta su
alcance y resultados; el [estado científico](../docs/scientific_status.md) distingue
ese subestudio de la verificación integral y validación experimental pendientes.
La referencia continua [E01-B](../benchmarks/e01b/README.md) añade transporte a Pe
finito. Los perfiles gaussianos de sigma conocida y el objetivo batch compartido
son API experimentales; su demostración no ejecuta el estudio confirmatorio E02.
No se afirma equivalencia con FAST, superioridad sobre otros programas, originalidad
absoluta ni validez universal a partir de una suite satisfactoria.

Continúan pendientes la validación externa con datos completos, ampliación de
referencias, estudios confirmatorios inversos y robustos, multicomponente/térmico,
condiciones variables y diseño mecánico avanzado. Los estados vivos se consultan
en el [registro de experimentos](../PAPER_ENVSOFT/EXPERIMENT_REGISTRY.csv).

## Procedencia y alcance del inventario

El manifiesto técnico registra bytes de fuentes/documentos seleccionados y metadatos
de dependencias declaradas, sin copiar sus distribuciones. Los avisos y auditorías
locales son referencias pendientes de revisión humana; no se infiere permiso por
disponibilidad ni por interoperabilidad. La [auditoría de licencias](../IP_LICENSE_AUDIT.md)
contiene evidencia histórica y debe leerse junto a metadatos actuales, sin asumir
que todas sus secciones describen la versión instalada hoy.

Autoría, titularidad, jurisdicción y decisiones de licencia permanecen en
[campos nulos](REVIEW_FIELDS.json) hasta revisión por quienes correspondan.

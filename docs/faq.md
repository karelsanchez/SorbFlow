# Preguntas frecuentes

## ¿Para qué sistemas sirve SorbFlow?

Para la adsorción de solutos en agua sobre cualquier adsorbente: carbones activados,
biocarbones, resinas, residuos agroindustriales u otros materiales. El soluto y el
material se definen en la configuración con sus parámetros. Ver
[configuraciones](configurations.md).

## ¿Qué modelos puedo usar?

Isotermas lineal, Langmuir y Freundlich; cinética LDF o HSDM con película; reactor
batch o columna de lecho fijo con dispersión axial. Se combinan libremente desde la
configuración.

## ¿Necesito otro programa de simulación?

No. SorbFlow incluye su propio motor numérico y solo requiere Python 3.11 o superior
con Pint, NumPy y SciPy, que se instalan automáticamente.

## ¿Cómo uso mis datos de laboratorio?

Con `sorbflow.io.load_breakthrough_csv`, indicando columnas y unidades. El archivo
original no se modifica y su huella SHA-256 queda registrada. Ver
[preparación de datos](data_preparation.md).

## ¿Cómo elijo la malla?

Empiece con 40–100 celdas axiales y repita con el doble. Si el indicador de interés no
cambia de forma apreciable, la malla es suficiente. Para mallas finas active el
Jacobiano analítico y el modo streaming ([rendimiento](performance.md)).

## ¿Por qué el programa se detiene con `SimulationError`?

Porque el integrador no alcanzó la tolerancia o el balance de masa no cerró. SorbFlow
no entrega resultados corregidos en silencio: refine la malla, ajuste `rtol` o pruebe
`Radau`.

## ¿Puedo usarlo sin programar?

Sí: la interfaz web local (`python -m sorbflow.web`) permite cargar ejemplos, editar
la configuración, simular y descargar resultados. Ver [interfaz local](web_interface.md).

## ¿Cómo reproduzco un resultado?

Cada carpeta de resultados guarda la configuración, las opciones, las versiones, la
revisión del código y las huellas SHA-256 de los archivos. Con la misma
configuración y versión se obtiene el mismo cálculo.

## ¿Cómo cito SorbFlow?

Ver [cómo citar](citation.md).

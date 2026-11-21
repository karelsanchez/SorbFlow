# Interfaz web local

La GUI opcional usa exclusivamente la biblioteca estándar para servir la interfaz;
el cálculo invoca las API científicas existentes de SorbFlow. No añade otro solver,
no usa FAST y no incorpora librerías de interfaz o recursos externos.

Desde la raíz del repositorio, con el entorno del proyecto:

```powershell
& .\.venv\Scripts\python.exe -m sorbflow.web --host 127.0.0.1 --port 8765 --output runs/gui
```

Abrir la dirección local que imprime la consola. Solo se permite enlazar a
`127.0.0.1` (`localhost` es un alias aceptado), nunca a interfaces de red públicas.
Cerrar con Ctrl+C termina el servidor y, si existe, únicamente su propio trabajador
de simulación. No enumera ni detiene procesos ajenos.

## Flujo disponible

1. Cargar un ejemplo sintético de batch lineal LDF, columna LDF o columna HSDM.
2. Editar la configuración JSON completa. Los valores usan SI según el nombre de
   cada campo: concentración kg/m³, carga kg/kg de adsorbente seco y tiempo s.
   La GUI no adivina unidades de números copiados de una tabla.
3. Validar el esquema y los rangos de la GUI antes de calcular. La elección de
   parámetros y modelo corresponde al usuario según su sistema.
4. Simular mediante BDF/Radau y observar el estado del trabajo, la curva de salida
   y el residuo máximo de masa.
5. Descargar JSON completo, CSV temporal, resumen y registro por identificador de
   trabajo. Los perfiles completos permanecen en el JSON; la vista solo grafica salida.

La cabecera de la página resume el estado de cada resultado: simulación numérica
con unidades SI, balance de masa verificado y archivos trazables. Materiales y
contaminantes son datos configurables. Los ejemplos incluidos son sintéticos.

## Recursos de ejecución local

- Una simulación activa y un máximo de 50 trabajos por sesión. No hay cola ilimitada.
- Cuerpo HTTP máximo 64 KiB; 2–401 observaciones, 2–64 celdas axiales y 2–12 radiales.
- Integradores BDF/Radau y rtol entre 1e-9 y 1e-3; no se permite desactivar balances
  ni introducir opciones arbitrarias del integrador mediante JSON.
- Duración física máxima 172800 s y rangos de magnitudes limitados para esta GUI.
  Son controles de recursos, no un nuevo dominio físico validado. Ver `web/config.py`.
- Cada trabajo usa un proceso propio, con 30 s de límite de pared por defecto.
  Al agotar tiempo se informa `timed_out`; no se entrega un resultado exitoso.
  Ejecuciones grandes o fuera de estos límites deben usar la API/CLI y verificarse.

Cada trabajo recibe una carpeta UUID nueva bajo la raíz de salida. No se sobrescriben
otros trabajos ni se leen ficheros de datos experimentales. La validación de un JSON
no crea carpetas. El cliente no puede indicar rutas de escritura, comandos o archivos
del servidor. Los destinos protegidos `src`, `.git` y `datasets_benchmark_pyfast`, y
rutas enlazadas/reparse points, se rechazan como raíz de salida.

La sesión mantiene su lista de trabajos en memoria; reiniciar el servidor conserva
los ficheros, pero no importa automáticamente el historial anterior. No se implementan
usuarios, autenticación empresarial, TLS o exposición de red. El servidor estándar
de Python no se presenta como servicio de producción.

## Protección del navegador y API local

Las solicitudes comprueban el Host local exacto. POST exige Origin coincidente y
un token aleatorio de sesión enviado en cabecera; las API de lectura y descarga
también exigen token. No se colocan tokens en URL ni se habilita CORS. Se aplican
CSP con nonce, `nosniff`, bloqueo de frames y `no-store`. La interfaz escribe datos
variables con `textContent`, nunca como HTML. No usa CDN, fuentes remotas ni telemetría.

Los identificadores UUID y nombres de descarga se validan contra rutas fijas; no hay
servidor genérico de archivos. Estos controles reducen riesgos de CSRF, rebinding y
XSS en el uso local; no sustituyen los permisos del sistema operativo frente a un
usuario con acceso al mismo sistema de archivos.

Las rutas principales son `GET /`, `/api/info`, `/api/examples`, `/api/jobs`,
`/api/jobs/<id>`, `/api/jobs/<id>/files/<nombre>`, `POST /api/validate` y `POST /api/jobs`.
El cuerpo POST admite solo `reactor`, `config_json`, `options` y `samples`; `config_json`
es texto para preservar la detección de claves duplicadas del JSON físico.

## Comprobación de desarrollo

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_web.py
```

Las pruebas realizan HTTP en un puerto de loopback efímero y simulan batch/columna
pequeños mediante el motor existente. Comprueban descargas, metadatos, payload máximo
de vista previa, no sobrescritura, límites, errores, token/origen/Host, timeout y
preservación de un dataset centinela. No ejecutan una simulación HSDM costosa ni un
benchmark confirmatorio del artículo.

[Índice de documentación](index.md) · [Estado científico](scientific_status.md) ·
[Primeros pasos](getting_started.md)

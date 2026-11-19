# Informe histórico de auditoría y fundación PyFAST 0.1

Fecha: 2026-11-18, contexto del usuario America/Bogota.
Este informe conserva el estado de la entrega 0.1. El estado actual 0.2 y sus algoritmos se documentan en NUMERICAL_VERIFICATION.md y README.md.
Repositorio independiente: `D:\PyFAST`. No se modificó el proyecto experimental.

## Insumo localizado y alcance real

La carpeta de chat original solo contenía directorios vacíos `work` y `outputs`.
La búsqueda recursiva por nombres en carpetas de trabajo de D: no identificó un
proyecto de adsorción. Tras la indicación del usuario se localizó y recorrió por
completo `C:\Users\Karel\Downloads\FAST2.1beta.zip`. También se buscaron nombres
FAST/adsorción/isotermas/cinética en Descargas; documentos personales no vinculados
no se trataron como datos experimentales. Las carpetas protegidas del sistema en D:
no se inspeccionaron. No se afirma haber auditado todos los archivos del disco.

ZIP de 1,207,065 bytes, 49 entradas, CRC válido: cuatro EXE (interfaz, HSDM, LDF,
DCBR), dos JPG y 43 GIF (42 en help). Las 42 ayudas se inspeccionaron visualmente
en memoria. No se extrajeron recursos del proveedor al repositorio ni se ejecutaron
binarios. El inventario incluye tamaños, hashes de cada entrada y cabeceras PE,
sin descompilar. No contiene fuentes, archivos de configuración, curvas calculadas,
ensayos experimentales ni rutinas de optimización accesibles.

Las cuatro cabeceras PE identifican x86 de 32 bits (`0x014c`). La interfaz importa
DLL de Windows; los tres motores solo declaran KERNEL32 en su tabla estática de
importación. Esto no descarta dependencias cargadas dinámicamente ni prueba ejecución
correcta en Windows de 64 bits. No se comprobó disponibilidad del runtime original.

La consulta inicial no mostró procesos FAST/HSDM/LDF/DCBR activos; no se detuvo ni
reinició ningún proceso. El SHA-256 del ZIP antes y después debe coincidir con
`535519e5388cb74728e8cb4c3c33c230d04a4c17cc99ac36fb58c46102589f23`.
Ver `audit/fast_inventory.json` y el registro final de verificación.

## Hallazgos científicos

| Componente | Evidencia disponible | Reutilización permitida en esta entrega |
|---|---|---|
| HSDM esférico y LDF | Ayuda gráfica y nombres de ejecutables | Conceptos reformulados independientemente; ningún código |
| Freundlich y Langmuir | Ambas ayudas locales; n aparece como exponente directo | Contratos propios; no copiar recursos ni inferir equivalencia |
| Columnas y batch | Ayuda BTC/DCBR | Especificar balances independientes |
| Parámetros y unidades | EBCT, masa, porosidad, densidades, tamaño, entrada, Q, película y difusión | Mapeo conceptual SI documentado |
| Variación de parámetros | Ayuda multi-run, un parámetro cada vez | No equivale a optimización o inferencia estadística |
| Salida | Ayuda anuncia archivos CSV con nombres variables | Sin ejemplo real no se puede fijar parser o columnas |
| Solver interno | Solo binarios | Integrador, malla, tolerancias y conservación no auditables |

FAST documenta entrada y caudal constantes. Su ayuda acepta masas secas o húmedas
si se mantiene coherencia; PyFAST v1 de esquema restringe masa seca explícita.
La documentación web antigua menciona solo Freundlich; 2.1 beta incluye Langmuir
en la ayuda. La ayuda de película `nofilm` muestra un signo negativo para gradiente
radial que, bajo radio creciente hacia afuera y carga interna creciente hacia la
superficie, requiere aclaración. Esto es una discrepancia documental: no prueba un
error en el ejecutable. PyFAST fija su convención por balance conservativo.
El supuesto de desviación máxima de 3% de la opción HSDM rápida figura en la ayuda,
pero no hay ensayos aquí que lo demuestren y no se adopta como garantía.

Bi, St y Dg dependen de definiciones y capacidades de referencia; no importarlos como
números intercambiables con grupos convencionales. K_F depende de las unidades y
del exponente. La referencia normalizada q_ref/c_ref evita transportar una constante
con dimensiones implícitas. No confundir EBCT con residencia líquida ni k_L con tasa LDF.

## IP y reutilización

La [FAQ oficial](https://www.fast-software.de/faq.html) y la
[página de descarga](https://www.fast-software.de/download.html) declaran CC BY-NC-ND
3.0. El ZIP no incluye licencia textual autónoma. No se incorpora ningún activo FAST.
La interfaz opcional queda diseñada, sin implementar ni habilitar ejecución.
La licencia abierta definitiva del nuevo core y la titularidad se resolverán antes
de publicar; se propone BSD-3-Clause. Detalle en IP_LICENSE_AUDIT.md.

## Entrega inicial

Los cinco documentos solicitados se generaron antes del código del paquete.
Paquete Python >=3.11 con Pint, campos SI, modelos de datos inmutables y discriminados,
JSON estricto/canónico, SHA-256 de configuración, observaciones y manifiestos de
procedencia. Los módulos científicos están reservados sin algoritmos. La API se
documenta y se incluye ejemplo sintético y matriz CI propuesta.
Los resultados de pytest, tipos, lint y empaquetado se registran después de ejecutarlos
en `audit/verification.txt`. No anticipar éxito a partir de la existencia de pruebas.

Dependencia runtime efectiva: Pint 0.25.3 y sus dependencias declaradas. Entorno local:
Python 3.11.2, pytest 9.2.0, pytest-cov 7.1.0, Ruff 0.17.5, mypy 1.20.2 y build 1.6.1.
El snapshot exacto y los metadatos de licencia están en `audit/requirements-local.txt`
y `audit/dependency_metadata.json`. La instalación requirió evitar una consulta al
registro MIME de Windows denegada por el sandbox mediante un wrapper temporal de pip;
no se modificaron la biblioteca estándar ni el registro. Las dependencias descargadas
permanecen fuera del código fuente versionado.

## Riesgos y prioridades

1. Sin fuentes ni resultados: auditoría de algoritmos y validación física pendientes.
2. Licencia NC/ND: no integrar ni comercializar activos FAST como parte del core.
3. Parámetros ambiguos: definir base seca, concentración másica y densidad aparente.
4. Identificabilidad k_f/D_s: requiere varios ensayos y análisis de sensibilidad/perfiles.
5. Rigidez, límites de Freundlich y conservación: cerrar pruebas V1 antes de calibrar.
6. Entorno: `python` global es 3.7 y `py` registrado selecciona 2.7; se usa Python 3.11.2
   mediante ruta explícita, con entorno aislado local. No se alteró Python global.
7. API pre-alpha: contrato 0.1 documentado; estabilidad científica y API 1.0 pendientes.

La siguiente etapa es revisar ecuaciones y construir isotermas/batch LDF con referencias
analíticas. Después: columna propia, HSDM, calibración identificable, incertidumbre,
optimización y validación experimental. No existe solver implementado ni validado hoy.

## Resultados verificados de la fundación

| Comprobación local (Windows, Python 3.11.2) | Resultado |
|---|---|
| pytest desde entorno de desarrollo | 101/101 pasan |
| Cobertura de líneas del código actual | 100%; no mide corrección científica del solver |
| Ruff lint y formato | Pasan |
| mypy estricto | Pasa, 12 archivos de fuente |
| pip check | Sin incompatibilidades declaradas |
| Ejemplo sintético JSON/SHA-256 | Pasa |
| Construcción wheel y sdist | Pasa |
| Instalación de wheel en entorno separado | Pasa; importación fuera del checkout confirmada |
| pytest contra wheel instalado | 101/101 pasan |
| Exclusión de recursos FAST en wheel/sdist | Confirmada |
| SHA-256 del ZIP original al terminar | Sin cambios |
| CI Linux y otras versiones Python | Configurada; no ejecutada |
| Conservación, convergencia y validación experimental | PENDIENTES; no hay solver |

El registro detallado y las huellas de distribuciones acompañan la entrega en
`audit/verification.txt` y `audit/distribution_hashes.json`; son evidencias externas
a los paquetes pip. Las pruebas y su cobertura solo corresponden a unidades/esquemas.

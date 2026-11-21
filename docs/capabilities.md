# Qué es SorbFlow

SorbFlow es una herramienta en Python para **modelar, simular, calibrar y diseñar
procesos de adsorción en fase acuosa**, en reactores por lotes (batch) y en columnas
de lecho fijo. Reúne en una sola biblioteca el equilibrio, la cinética, el transporte
en columna, el ajuste de parámetros, la incertidumbre y el dimensionamiento, con
unidades SI explícitas y resultados trazables.

## Capacidades

| Área | Qué ofrece |
|---|---|
| Equilibrio | Isotermas lineal, Langmuir y Freundlich normalizado, con derivadas analíticas |
| Cinética | Fuerza impulsora lineal (LDF) y difusión superficial homogénea (HSDM) con resistencia de película |
| Reactores | Batch cerrado y columna de lecho fijo con dispersión axial y entrada de Danckwerts |
| Numérica | Volúmenes finitos conservativos, integradores rígidos BDF y Radau, Jacobiano analítico disperso y modo *streaming* de bajo consumo de memoria |
| Calibración | Ajuste de isotermas y constantes LDF, SVD y covarianza local, perfiles de verosimilitud y objetivos multiensayo |
| Incertidumbre | Monte Carlo reproducible con semilla y sensibilidad local |
| Diseño | EBCT, tiempo de residencia, masa de lecho, pérdida de carga de Ergun, potencia, costo de operación y envolvente DXF |
| Optimización | NSGA-II multiobjetivo con restricciones y reevaluación de cada solución |
| Datos | Lectura de CSV con unidades declaradas y huella SHA-256; exportación JSON, CSV y Parquet |
| Interfaces | API Python, comando `sorbflow` e interfaz web local, todas sobre el mismo motor |

## Una herramienta general

- **Cualquier soluto y cualquier adsorbente.** Especies, materiales y recetas son datos
  de configuración: el mismo programa sirve para colorantes, metales, compuestos
  orgánicos u otros solutos, con los parámetros de cada sistema.
- **Mezclas de N componentes** con `AdsorbentBlend` y fracciones de masa seca.
- **Modelos intercambiables.** Cambiar de LDF a HSDM o de Langmuir a Freundlich es
  cambiar un campo del archivo de configuración.
- **Unidades seguras.** Entradas en mg/L, min, cm o g se convierten explícitamente a SI.
- **Resolución a medida.** Celdas axiales y radiales, tolerancias, integrador e
  instantes de salida los fija el usuario. Ver [configuraciones](configurations.md).

## Casos de uso

- Simular curvas de ruptura y estimar el tiempo de servicio de una columna.
- Comparar adsorbentes o recetas de mezcla con el mismo flujo de trabajo.
- Ajustar isotermas y constantes cinéticas a ensayos batch o de columna.
- Propagar la incertidumbre de parámetros a indicadores de diseño.
- Dimensionar lechos (EBCT, pérdida de carga, potencia, costo) y buscar diseños
  robustos con optimización multiobjetivo.
- Enseñar modelación de adsorción con ejemplos reproducibles y una interfaz de navegador.

## Calidad

585 pruebas automatizadas, integración continua en Windows y Linux con Python 3.11,
3.12 y 3.13, tipado estático estricto y verificación numérica frente a soluciones de
referencia. Detalle en [benchmarks](benchmark_results.md) y [rendimiento](performance.md).

## Siguiente paso

[Instalar y ejecutar el primer caso](getting_started.md) ·
[Galería de ejemplos](examples_gallery.md) · [Preguntas frecuentes](faq.md)

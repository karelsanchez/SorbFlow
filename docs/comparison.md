# SorbFlow frente a otras herramientas

[Inicio](index.md) · [Qué es SorbFlow](capabilities.md) · [Trabajos relacionados](../RELATED_WORK.md)

Esta comparación sitúa a SorbFlow entre herramientas conocidas de adsorción según las
**funciones que cada una documenta oficialmente**. No compara exactitud ni velocidad:
esas propiedades dependen del caso y no se midieron en paralelo. "n. d." significa
que la función no aparece documentada en la fuente consultada, no que no exista.
Consulta de fuentes: 2026-11-18 y 2026-11-21.

| Herramienta | Plataforma | Licencia | Fase / aplicación | Lecho fijo | Batch | LDF | Difusión intrapartícula | Multicomponente | Calibración / incertidumbre | Optimización | API programable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **SorbFlow** | Python ≥3.11 (Windows, Linux) | Apache-2.0 | Líquida, tratamiento de agua | Sí | Sí | Sí | HSDM | Hoja de ruta | Sí (ajuste, perfiles, Monte Carlo) | Sí (NSGA-II) | Sí (API, CLI, web local) |
| FAST 2.1 | Windows (ejecutable) | CC BY-NC-ND 3.0 | Simulación de lecho fijo | Sí | n. d. | Sí | HSDM | n. d. | n. d. | n. d. | n. d. |
| AdDesignS (ETDOT, EPA / Michigan Tech) | Windows | Gratuito (EPA) | Carbón activado granular, agua | Sí | n. d. | n. d. | n. d. | n. d. | n. d. | n. d. | n. d. |
| Aspen Adsorption | Windows, comercial | Propietaria | Gas y líquido, industrial | Sí | n. d. | Sí (resistencia agrupada) | Sí (micro/macroporo, modelo general) | Sí | n. d. | Sí | Simulador de diagramas de flujo |
| CADET | Núcleo C++, herramientas Python | GPL-3.0 | Cromatografía líquida | Sí | n. d. | n. d. | Sí (variantes del modelo general de velocidad) | Sí | Ajuste en CADET-Match | Sí (CADET-Process) | Sí |
| pysorb | Python (PyPI) | MIT | Ajuste, mezclas, ruptura | Sí | n. d. | n. d. | Captación de Crank | Sí (mezclas) | Ajuste de isotermas | n. d. | Sí |
| RUPTURA | Código abierto | MIT | Ruptura de gases | Sí | n. d. | n. d. | n. d. | Sí (IAST) | n. d. | n. d. | n. d. |
| pyGAPS | Python (PyPI) | Ver repositorio | Análisis de isotermas de gases | n. d. | n. d. | n. d. | n. d. | IAST | Ajuste de isotermas | n. d. | Sí |

## Cómo leer la tabla

- **Dónde encaja SorbFlow**: adsorción en fase líquida para tratamiento de agua, en
  batch y en columna, con calibración, incertidumbre, diseño hidráulico y
  optimización en una sola biblioteca de Python con unidades SI y resultados trazables.
- **Qué ofrecen otras herramientas que SorbFlow aún no tiene**: sistemas
  multicomponente (Aspen Adsorption, CADET, RUPTURA, pysorb), efectos térmicos y
  procesos cíclicos PSA/TSA (Aspen Adsorption) y modelos de cromatografía
  (CADET). Están en la [hoja de ruta](../DEVELOPMENT_ROADMAP.md) o fuera de su alcance.
- **Relación con FAST**: SorbFlow es un desarrollo independiente; no contiene código,
  ejecutables ni recursos de FAST y no afirma equivalencia numérica con él.

## Fuentes

| Herramienta | Fuente oficial consultada |
|---|---|
| FAST 2.1 | [FAQ](https://www.fast-software.de/faq.html), [descarga](https://www.fast-software.de/download.html) y [documentación](https://www.fast-software.de/documentation.html) (2026-11-18; ver auditoría de licencias) |
| AdDesignS | [EPA — Environmental Technologies Design Option Tool (ETDOT)](https://www.epa.gov/water-research/environmental-technologies-design-option-tool-etdot) |
| Aspen Adsorption | [AspenTech — Aspen Adsorption](https://www.aspentech.com/ja/products/pages/aspen-adsorption) |
| CADET | [Repositorio CADET](https://github.com/modsim/cadet) y [documentación](https://cadet.github.io) |
| pysorb | [PyPI — pysorb](https://pypi.org/project/pysorb/) |
| RUPTURA | [iRASPA — RUPTURA](https://iraspa.org/ruptura/) |
| pyGAPS | [Documentación](https://pygaps.readthedocs.io/) y [PyPI](https://pypi.org/project/pygaps/) |

Las descripciones resumen lo que cada fuente declara en la fecha de consulta y pueden
cambiar con nuevas versiones. Si detecta una inexactitud, abra un *issue*.

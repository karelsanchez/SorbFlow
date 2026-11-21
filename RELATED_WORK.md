# Antecedentes y trabajos relacionados

Consulta de fuentes primarias: 2026-11-18, ampliada el 2026-11-21. No se descargó ni
incorporó código de estas herramientas. La comparación por funciones está en
[SorbFlow frente a otras herramientas](docs/comparison.md).

| Proyecto | Lo que declara su fuente oficial | Relación con SorbFlow |
|---|---|---|
| [FAST 2.1](https://www.fast-software.de/documentation.html) | Simulación de lecho fijo con HSDM/LDF; ejecutable Windows; CC BY-NC-ND 3.0 | Herramienta independiente de referencia en el área; SorbFlow no contiene ni deriva de su código |
| [AdDesignS (ETDOT)](https://www.epa.gov/water-research/environmental-technologies-design-option-tool-etdot) | Diseño de adsorción con carbón activado granular para Windows, distribuido gratuitamente por la EPA (desarrollo de Michigan Tech) | Mismo dominio de tratamiento de agua; SorbFlow aporta API Python, calibración e incertidumbre |
| [Aspen Adsorption](https://www.aspentech.com/ja/products/pages/aspen-adsorption) | Simulador comercial de procesos de adsorción de gas y líquido, cinéticas agrupadas y de modelo general, PSA/TSA, optimización | Cubre procesos industriales cíclicos y multicomponente fuera del alcance actual de SorbFlow |
| [CADET](https://github.com/modsim/cadet) | Solucionador del modelo general de velocidad para cromatografía líquida; GPL-3.0; herramientas Python (CADET-Process, CADET-Match) | Cromatografía en lugar de tratamiento de agua; inspira la separación entre núcleo numérico y flujos de calibración |
| [pysorb](https://pypi.org/project/pysorb/) | Ajuste, mezclas, ruptura y difusión; MIT | Otra biblioteca Python de adsorción: SorbFlow no alega primacía por ser Python |
| [RUPTURA](https://iraspa.org/ruptura/) | Ruptura de gases, IAST e isotermas; MIT | Orientado a gases; SorbFlow se centra en fase acuosa |
| [pyGAPS](https://pygaps.readthedocs.io/) | Análisis y ajuste de isotermas de gases, IAST | Complementario para caracterización de materiales |
| [pyAPEP](https://sebygaa.github.io/pyAPEP/build/html/index.html) | Isotermas y procesos PSA; MIT | Antecedente de evaluación de adsorbentes y simulación de procesos |
| [pyDAC](https://github.com/process-intensification-lab/pyDAC) | Captura directa de CO2, balances y NSGA-II; MIT | La optimización multiobjetivo por sí sola tampoco es diferencial |

## Posicionamiento

SorbFlow integra, para adsorción en fase líquida, un flujo completo en una biblioteca
abierta de Python: configuración tipada con unidades SI, simulación batch y de
columna LDF/HSDM con control de balance, calibración con diagnósticos de
identificabilidad, propagación de incertidumbre, diseño hidráulico y optimización
robusta, con resultados trazables. Es una integración de métodos conocidos; las
ecuaciones no se reclaman como originales.

La exportación DXF describe la envolvente del lecho; un adaptador CAD/STEP con cotas
constructivas está en la hoja de ruta.

## Ampliación para EnvSoft

El análisis de SWAT-UQ, Optienv, UQPyL y marcos de decisión robusta, además de
software de adsorción, se detalla en PAPER_ENVSOFT/NOVELTY_MATRIX.md. Ninguno de esos
comparadores se ejecutó en los estudios actuales.

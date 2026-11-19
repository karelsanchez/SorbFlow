# Antecedentes y contribución candidata

Consulta de fuentes primarias: 2026-11-18. No se descargó ni incorporó código de
estas herramientas. Una descripción de funcionalidad no prueba su exactitud científica.

| Proyecto | Lo que declara su fuente oficial | Implicación para PyFAST |
|---|---|---|
| [pysorb](https://pypi.org/project/pysorb/) | Ajuste, mezclas, ruptura y difusión; MIT | No alegar novedad por ser una biblioteca Python de adsorción |
| [RUPTURA](https://iraspa.org/ruptura/) | Ruptura para gases, IAST e isotermas; MIT | Distinguir transporte acuoso y validar, sin reclamar primacía del motor |
| [pyAPEP](https://sebygaa.github.io/pyAPEP/build/html/index.html) | Isotermas y procesos PSA; MIT | Hay antecedentes de evaluación de adsorbentes y simulación de procesos |
| [pyDAC](https://github.com/process-intensification-lab/pyDAC) | Captura directa de CO2, balances y NSGA-II; MIT | Multiobjetivo por sí solo tampoco constituye novedad |

Contribución candidata: flujo verificable para columnas de tratamiento de agua que
integre identificabilidad, incertidumbre, diseño robusto e hidráulica/mecánica con
exportación CAD. Es una hipótesis de diferenciación, no una novedad científica
demostrada. Requiere revisión bibliográfica sistemática y comparación reproducible.
DXF/STEP se delegarán en un adaptador CAD optativo, con unidades, cotas y alcance
constructivo explícitos. No generar planos de fabricación certificados a partir de
un dimensionamiento hidráulico sin ingeniería mecánica y revisión aplicable.

## Ampliación para EnvSoft

El análisis de SWAT-UQ, Optienv, UQPyL y frameworks de decisión robusta, además de software de adsorción, se detalla en PAPER_ENVSOFT/NOVELTY_MATRIX.md. Distingue hechos documentales, integración, aplicación y metodología candidata; cada claim C01–C08 tiene prueba y refutación posibles. Ninguno de esos comparadores fue ejecutado en el estudio actual.

# Cómo citar SorbFlow

Si SorbFlow contribuye a un trabajo publicado, cite la versión utilizada:

```text
Sanchez Hernandez, K. A., Rodriguez Saiz, D. E., Cabrera Obando, D. X. y
Romo Cadena, G. J. (2026). SorbFlow: modelación configurable de adsorción en fase
acuosa (versión 0.3.0) [Software]. https://github.com/karelsanchez/SorbFlow
```

BibTeX:

```bibtex
@software{sorbflow_2026,
  author  = {Sanchez Hernandez, Karel Aldrin and Rodriguez Saiz, David Esteban and
             Cabrera Obando, Dayana Ximena and Romo Cadena, Gabriela Johana},
  title   = {SorbFlow: modelación configurable de adsorción en fase acuosa},
  version = {0.3.0},
  year    = {2026},
  url     = {https://github.com/karelsanchez/SorbFlow},
  license = {Apache-2.0}
}
```

Los metadatos en formato estándar están en
[`CITATION.cff`](https://github.com/karelsanchez/SorbFlow/blob/main/CITATION.cff);
GitHub los usa para el botón *Cite this repository*.

## Autores

| Orden | Autor | Contribución |
|---|---|---|
| 1 | Karel Aldrin Sanchez Hernandez (K. A. Sanchez Hernandez) | Concepción, diseño, desarrollo y documentación |
| 2 | David Esteban Rodriguez Saiz | Pruebas del software |
| 3 | Dayana Ximena Cabrera Obando | Pruebas del software |
| 4 | Gabriela Johana Romo Cadena | Validación técnica de los fenómenos químicos |

## Reproducibilidad

Indique también la revisión exacta del código. Cada resultado la guarda en su
manifiesto (`code_revision`), junto con las versiones de las dependencias y la
huella `numerical_sha256` del cálculo. La versión instalada se consulta con
`python -c "import sorbflow; print(sorbflow.__version__)"`.

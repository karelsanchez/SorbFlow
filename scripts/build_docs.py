"""Stage tracked documentation/resources and build a strict, offline-capable site."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LANDING = """# SorbFlow

Herramienta en Python para **modelar, simular, calibrar y diseñar procesos de
adsorción acuosa** en reactores batch y columnas de lecho fijo: isotermas lineal,
Langmuir y Freundlich; cinética LDF y HSDM; calibración, incertidumbre, diseño
hidráulico y optimización multiobjetivo, con unidades SI y resultados trazables.

Versión **0.3.0.dev0**. Cualquier soluto, adsorbente o mezcla se describe como
configuración; los modelos se intercambian sin tocar código.

## Empezar

1. [Qué es SorbFlow](docs/capabilities.md): capacidades y casos de uso.
2. [Instalar y ejecutar el primer caso](docs/getting_started.md).
3. [Seguir los tutoriales](docs/tutorials.md) y la [galería de ejemplos](docs/examples_gallery.md).
4. [Configuraciones disponibles](docs/configurations.md): modelos y opciones numéricas.
5. [Consultar la API](API_REFERENCE.md), la [referencia generada](docs/api_generated.md)
   y las [ecuaciones](MODEL_SPECIFICATION.md).

## Calidad y rendimiento

[Rendimiento medido](docs/performance.md): Jacobiano analítico 2,2 veces más
rápido y modo streaming con 41 % menos memoria. [Benchmarks](docs/benchmark_results.md)
de verificación numérica, calibración y diseño robusto, y
[reproducción](benchmarks/reproduction_20261120/README.md).

## Trabajar con resultados

Cada simulación conserva configuración, opciones, versiones y huellas SHA-256.
La [preparación de datos](docs/data_preparation.md) explica unidades y procedencia.
La [interfaz local](docs/web_interface.md) usa el mismo motor desde el navegador.
[Preguntas frecuentes](docs/faq.md) · [Cómo citar](docs/citation.md) ·
[Licencia actual](LICENSE.md).
"""


def prepare(repo: Path) -> Path:
    """Copy only indexed files; never sweep a workspace or external datasets."""
    repo = repo.resolve()
    work = (repo / ".work").resolve()
    stage = (work / "docs_source").resolve()
    if stage == work or not stage.is_relative_to(work) or not work.is_relative_to(repo):
        raise ValueError("Documentation staging escaped the repository work directory")
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True, check=True,
    )
    names = result.stdout.decode("utf-8").split("\0")
    allowed = {".md", ".json", ".csv", ".txt", ".py", ".toml", ".yaml", ".yml",
               ".png", ".zip", ".cmd", ".in"}
    forbidden = {".venv", ".git", ".work", "runs", "datasets_benchmark_pyfast"}
    selected: list[tuple[Path, Path]] = []
    for name in filter(None, names):
        if name == "README.md":
            continue  # MkDocs maps README and index to the same landing URL.
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe indexed path: {name}")
        if forbidden.intersection(relative.parts) or relative.suffix.lower() not in allowed:
            continue
        source = (repo / relative).resolve()
        if not source.is_relative_to(repo) or (repo / relative).is_symlink():
            raise ValueError(f"Indexed source escaped the repository: {name}")
        if not source.is_file():
            raise ValueError(f"Indexed source missing: {name}")
        selected.append((source, stage / relative))
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for source, destination in selected:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    (stage / "index.md").write_text(LANDING, encoding="utf-8")
    return stage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    prepare(repo)
    if args.prepare_only:
        return 0
    command = [sys.executable, "-m", "mkdocs", "build", "--strict", "--config-file",
               str(repo / "mkdocs.yml")]
    if args.output:
        command += ["--site-dir", str(args.output.resolve())]
    return subprocess.run(command, cwd=repo, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

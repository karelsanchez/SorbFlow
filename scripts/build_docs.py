"""Stage tracked documentation/resources and build a strict, offline-capable site."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LANDING = """# SorbFlow

Framework Python para modelación reproducible de adsorción acuosa: equilibrio,
batch, columnas LDF/HSDM, calibración, incertidumbre y diseño multiobjetivo.

La versión **0.2.0.dev0** es experimental. Sus
[benchmarks ejecutados](docs/benchmark_results.md) delimitan la evidencia disponible.
Materiales y especies son configurables; no se limita al caso inicial de aplicación.

## Empezar

1. [Instalar y ejecutar el primer caso](docs/getting_started.md).
2. [Seguir los tutoriales](docs/tutorials.md).
3. [Consultar la API](API_REFERENCE.md) y las [ecuaciones](MODEL_SPECIFICATION.md).
4. [Reproducir los benchmarks](benchmarks/reproduction_20261120/README.md).

## Trabajar con resultados

Las configuraciones usan SI y masa seca. Cada simulación conserva configuración,
opciones, versiones y huellas. La [preparación de datos](docs/data_preparation.md)
explica procedencia y unidades; el [estado científico](docs/scientific_status.md)
separa capacidades, evidencia y extensiones pendientes.

La [interfaz local](docs/web_interface.md) utiliza el mismo núcleo científico.
No se requiere FAST. La [licencia actual](LICENSE.md) permanece provisional;
la documentación local no implica publicación ni autorización de redistribución.
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

"""Run local project checks and preserve logs; never run scientific benchmarks implicitly."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path

INPUT_DIRS = ("src", "tests", "examples", "scripts", "docs", "PAPER_ENVSOFT", "benchmarks",
              "REGISTRATION_PREPARATION")
SUFFIXES = {".py", ".json", ".csv", ".md", ".toml", ".yml", ".yaml", ".html", ".js", ".css"}


def source_snapshot(repo: Path) -> dict[str, str]:
    metadata = {repo / name for name in ("pyproject.toml", "MANIFEST.in", ".gitignore",
                                         ".gitattributes", "INICIAR_GUI.cmd")}
    files = set(repo.glob("*.md")) | metadata
    files.update((repo / ".github/workflows").glob("*.yml"))
    for directory in INPUT_DIRS:
        files.update((repo / directory).rglob("*"))
    return {
        path.relative_to(repo).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(files)
        if path.is_file() and not path.is_symlink()
        and (path.suffix in SUFFIXES or path in metadata)
        and "__pycache__" not in path.parts
    }


def check_version(repo: Path) -> str:
    project_version = tomllib.loads((repo / "pyproject.toml").read_text())["project"]["version"]
    tree = ast.parse((repo / "src/pyfast/_version.py").read_text())
    versions = [ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "VERSION"
                        for target in node.targets)]
    if versions != [project_version]:
        raise ValueError("Runtime VERSION and pyproject project.version differ")
    return str(project_version)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True, help="New directory for logs")
    parser.add_argument("--quick", action="store_true", help="Skip pytest; keep static checks")
    parser.add_argument("--build", action="store_true", help="Also build wheel and sdist offline")
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    protected = {".git", ".venv", "datasets_benchmark_pyfast"}
    if any(part.casefold() in protected for part in output.parts):
        parser.error("Reports must stay outside .git, .venv and raw datasets")
    if any(output.is_relative_to(repo / directory) for directory in INPUT_DIRS):
        parser.error("Put reports in runs/ or outside the input directories")
    if output == repo or output.exists():
        parser.error("--output must be a new directory")
    if not (repo / "pyproject.toml").is_file():
        parser.error("--repo must contain pyproject.toml")
    output.mkdir(parents=True)
    before = source_snapshot(repo)
    checks: list[dict[str, object]] = []
    try:
        version = check_version(repo)
        checks.append({"name": "version_consistency", "returncode": 0, "version": version})
    except (OSError, ValueError, KeyError) as exc:
        checks.append({"name": "version_consistency", "returncode": 1, "error": str(exc)})
    commands = [
        ("ruff", ["-m", "ruff", "check", "src", "tests", "examples", "scripts",
                  "docs", "PAPER_ENVSOFT", "benchmarks"]),
        ("mypy", ["-m", "mypy"]),
        ("documentation_links", ["scripts/check_doc_links.py"]),
        ("readiness_report", ["benchmarks/data_catalog/check_benchmark_readiness.py",
                              "--repo", "."]),
    ]
    if not args.quick:
        commands.append(("pytest", ["-m", "pytest", "--cov=pyfast", "--cov-report=term",
                                    "--cov-fail-under=90"]))
    if args.build:
        commands.append(("build", ["-m", "build", "--no-isolation", "--outdir",
                                    str(output / "dist")]))
    for name, arguments in commands:
        command = [sys.executable, *arguments]
        started = time.perf_counter()
        environment = os.environ.copy()
        if name == "build":
            # The build frontend creates unique children; a short base avoids MAX_PATH.
            build_temp = repo / ".work"
            build_temp.mkdir(parents=True, exist_ok=True)
            environment.update(TEMP=str(build_temp), TMP=str(build_temp), TMPDIR=str(build_temp))
        try:
            result = subprocess.run(command, cwd=repo, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", check=False,
                                    env=environment)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except OSError as exc:
            code, stdout, stderr = 1, "", str(exc)
        (output / f"{name}.stdout.txt").write_text(stdout, encoding="utf-8")
        (output / f"{name}.stderr.txt").write_text(stderr, encoding="utf-8")
        checks.append({"name": name, "command": command, "returncode": code,
                       "elapsed_s": time.perf_counter() - started})
        print(f"{name}: {'PASS' if code == 0 else 'FAIL'}", flush=True)
        if code:
            print(stdout)
            print(stderr, file=sys.stderr)
    stable = before == source_snapshot(repo)
    passed = stable and all(check["returncode"] == 0 for check in checks)
    record = {"status": "PASS" if passed else "FAIL", "quick": args.quick,
              "utc": datetime.now(UTC).isoformat(), "repo": str(repo),
              "python_executable": sys.executable, "checks": checks,
              "python_version": sys.version, "platform": platform.platform(),
              "packages": dict(sorted((d.metadata["Name"], d.version)
                                      for d in importlib.metadata.distributions()
                                      if d.metadata["Name"])),
              "source_stable_during_checks": stable, "source_sha256": before,
              "scientific_benchmarks_run": False, "scientific_validation_claimed": False}
    (output / "quality.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"{record['status']}: {output / 'quality.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

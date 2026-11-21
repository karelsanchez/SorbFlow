"""Reproduce selected synthetic references/demos, not confirmatory paper benchmarks.

Run with the SorbFlow environment, --output NEW_DIR and --jobs 1/2. --resume only
reuses intact artifacts at a matching source/environment fingerprint, not integrator
checkpoints or distributed execution.
E01 completo PENDIENTE (solo referencias seleccionadas); E02-E05 pendientes.
No experimental validation is claimed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

Record = dict[str, Any]
PENDING = "E01 completo PENDIENTE (solo referencias seleccionadas); E02-E05 pendientes"
DEMO_REQUIRED = ("demo/report.json", "demo/ldf/result.json", "demo/hsdm/result.json")
TASKS = {
    "numerical_references": ("examples/numerical_benchmarks.py", "metrics.json", ("metrics.json",)),
    "synthetic_demo": ("examples/scientific_demo.py", "demo", DEMO_REQUIRED),
}
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot(repo: Path, env: dict[str, str]) -> Record:
    """Hash relevant source and safe environment metadata, never credential variables."""
    files = sorted(set((repo / "src").rglob("*.py")) | set((repo / "examples").rglob("*.py")))
    files += [repo / "pyproject.toml"]
    source = {str(path.relative_to(repo)): file_hash(path) for path in files}
    source["runner"] = file_hash(Path(__file__).resolve())
    packages = {d.metadata["Name"]: d.version for d in distributions() if d.metadata["Name"]}
    context = {
        "source_sha256": source,
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "packages": packages,
            "threads": {key: env[key] for key in THREAD_ENV},
            "PYTHONHASHSEED": env.get("PYTHONHASHSEED"),
        },
    }
    context["fingerprint"] = hashlib.sha256(
        json.dumps(context, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return context


def save_manifest(path: Path, data: Record) -> None:
    """Only the coordinator writes this file; replace atomically on the same volume."""
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def artifacts(folder: Path) -> dict[str, str]:
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            if not path.resolve().is_relative_to(folder.resolve()):
                raise ValueError("Artifact escapes its attempt directory")
            result[path.relative_to(folder).as_posix()] = file_hash(path)
    return result


def reusable(attempt: Record, output: Path, fingerprint: str, required: tuple[str, ...]) -> bool:
    if attempt.get("status") != "completed" or attempt.get("fingerprint") != fingerprint:
        return False
    folder = (output / attempt["directory"]).resolve()
    expected = attempt.get("artifacts", {})
    if (
        not folder.is_relative_to(output)
        or not expected
        or not all(name in expected for name in required)
    ):
        return False
    try:
        return bool(artifacts(folder) == expected)
    except (OSError, ValueError):
        return False


def execute(
    attempt: Record, output: Path, repo: Path, env: dict[str, str], required: tuple[str, ...]
) -> Record:
    result = dict(attempt, started_utc=datetime.now(UTC).isoformat())
    folder = output / attempt["directory"]
    started = time.monotonic()
    try:
        with (folder / "stdout.txt").open("x", encoding="utf-8") as stdout:
            with (folder / "stderr.txt").open("x", encoding="utf-8") as stderr:
                command = attempt["command"]
                process = subprocess.run(
                    command,
                    cwd=repo,
                    env=env,
                    shell=False,
                    stdout=stdout,
                    stderr=stderr,
                    check=False,
                )
        result["returncode"] = process.returncode
        if process.returncode != 0:
            raise RuntimeError(f"Subprocess returned {process.returncode}; see stderr.txt")
        if not all((folder / name).is_file() for name in required):
            raise RuntimeError("Subprocess returned zero but expected artifacts are missing")
        result["status"] = "completed"
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    result.update(
        finished_utc=datetime.now(UTC).isoformat(),
        elapsed_s=time.monotonic() - started,
        stdout="stdout.txt",
        stderr="stderr.txt",
    )
    try:
        result["artifacts"] = artifacts(folder)
    except (OSError, ValueError) as exc:
        result.update(status="failed", error=f"Artifact hashing failed: {exc}", artifacts={})
    return result


def run(repo: Path, output: Path, jobs: int, resume: bool) -> int:
    repo, output = repo.resolve(), output.resolve()
    for script, _, _ in TASKS.values():
        if not (repo / script).is_file():
            raise ValueError(f"Missing versioned script: {repo / script}")
    manifest_path = output / "manifest.json"
    if resume:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1 or set(manifest.get("tasks", {})) != set(TASKS):
            raise ValueError("Unsupported or incompatible smoke manifest")
    else:
        output.mkdir(parents=True, exist_ok=False)
        manifest = {
            "schema_version": 1,
            "created_utc": datetime.now(UTC).isoformat(),
            "runs": [],
            "scope": "SMOKE: selected synthetic references/demos, not confirmatory benchmarks",
            "protocol_status": PENDING,
            "experimental_validation": False,
            "tasks": {name: {"attempts": []} for name in TASKS},
        }
    manifest.update(protocol_status=PENDING, experimental_validation=False)
    env = os.environ.copy()
    for key in THREAD_ENV:
        env.setdefault(key, "1")
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = str(repo / "src")
    for variable, relative in (("MPLCONFIGDIR", "matplotlib"), ("TEMP", "tmp"), ("TMP", "tmp")):
        directory = output / ".runtime_cache" / relative
        directory.mkdir(parents=True, exist_ok=True)
        env[variable] = str(directory)
    context = snapshot(repo, env)
    fingerprint = context["fingerprint"]
    run_record = dict(context, started_utc=datetime.now(UTC).isoformat(), jobs=jobs, resume=resume)
    manifest["runs"].append(run_record)
    manifest.update(status="running", fingerprint=context["fingerprint"])
    save_manifest(manifest_path, manifest)
    pending: dict[Future[Record], tuple[str, int]] = {}
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for name, (script, destination, required) in TASKS.items():
            task = manifest["tasks"][name]
            candidates = reversed(task["attempts"])
            eligible = (a for a in candidates if reusable(a, output, fingerprint, required))
            previous = next(eligible, None)
            if previous is not None:
                task.update(status="reused", selected_attempt=previous["directory"])
                continue
            number = len(task["attempts"]) + 1
            folder = output / name / f"attempt_{number:04d}"
            while folder.exists():
                number += 1
                folder = output / name / f"attempt_{number:04d}"
            folder.mkdir(parents=True, exist_ok=False)
            script_path, target = str(repo / script), str(folder / destination)
            attempt = {
                "status": "running",
                "queued_utc": datetime.now(UTC).isoformat(),
                "directory": folder.relative_to(output).as_posix(),
                "fingerprint": context["fingerprint"],
                "command": [sys.executable, script_path, "--output", target],
            }
            task["attempts"].append(attempt)
            task.update(status="running", selected_attempt=attempt["directory"])
            save_manifest(manifest_path, manifest)
            future = executor.submit(execute, attempt, output, repo, env, required)
            pending[future] = (name, len(task["attempts"]) - 1)
        for future in as_completed(pending):
            name, index = pending[future]
            completed = future.result()
            manifest["tasks"][name]["attempts"][index] = completed
            manifest["tasks"][name]["status"] = completed["status"]
            save_manifest(manifest_path, manifest)
    stable = snapshot(repo, env)["fingerprint"] == context["fingerprint"]
    complete = all(task["status"] in ("completed", "reused") for task in manifest["tasks"].values())
    if not stable:
        manifest["error"] = "Source/environment changed during execution; rerun in fresh attempts"
        for task in manifest["tasks"].values():
            for attempt in task["attempts"]:
                if attempt.get("fingerprint") == context["fingerprint"]:
                    attempt["status"] = "invalidated"
    manifest.update(
        status="smoke_completed" if stable and complete else "failed",
        finished_utc=datetime.now(UTC).isoformat(),
    )
    save_manifest(manifest_path, manifest)
    print(f"{manifest['status']}: {manifest_path}")
    print(f"SMOKE only. {PENDING} No experimental validation.")
    return 0 if stable and complete else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True, help="New root (or --resume)")
    parser.add_argument("--jobs", type=int, choices=(1, 2), default=1)
    parser.add_argument("--resume", action="store_true", help="Reuse intact completed tasks only")
    args = parser.parse_args(argv)
    try:
        return run(args.repo, args.output, args.jobs, args.resume)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Smoke harness error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

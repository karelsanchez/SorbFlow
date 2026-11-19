"""Prepare a technical source inventory, without filing or determining ownership."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import stat
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SOURCE_DIRS = {
    "src",
    "tests",
    "scripts",
    "docs",
    "examples",
    "paper_envsoft",
    "benchmarks",
    "registration_preparation",
    ".github",
}
EXCLUDED = {
    ".git",
    ".venv",
    ".work",
    "build",
    "dist",
    "runs",
    "outputs",
    "audit",
    "datasets_benchmark_pyfast",
    "datasets",
    "data",
    "raw",
    "rawdatasets",
    "resources",
    "downloads",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".json", ".typed", ".in", ".cmd"}
ROOT_NAMES = {"pyproject.toml", "manifest.in", "iniciar_gui.cmd"}
AUDIT_REFERENCES = (
    "IP_LICENSE_AUDIT.md",
    "LICENSE.md",
    "audit/dependency_metadata.json",
    "PAPER_ENVSOFT/IP_AND_LICENSING.md",
)


def linked(path: Path) -> bool:
    """Also detect Windows junctions on Python 3.11."""
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def inventory(repo: Path) -> list[dict[str, object]]:
    """Hash allowlisted text sources only; never follow directory links."""
    records: list[dict[str, object]] = []
    for current, directories, filenames in os.walk(repo, followlinks=False):
        base = Path(current)
        directories[:] = sorted(
            name
            for name in directories
            if name.casefold() not in EXCLUDED
            and not linked(base / name)
            and (base != repo or name.casefold() in SOURCE_DIRS)
        )
        for name in sorted(filenames):
            path = base / name
            if linked(path) or path.suffix.casefold() not in SUFFIXES:
                continue
            if (
                base == repo
                and path.suffix.casefold() != ".md"
                and name.casefold() not in ROOT_NAMES
            ):
                continue
            # No binary assets disguised with an allowed extension.
            content = path.read_bytes()
            try:
                content.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            if b"\x00" in content:
                continue
            records.append(
                {
                    "path": path.relative_to(repo).as_posix(),
                    "size_bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
    return sorted(records, key=lambda record: str(record["path"]))


def git_state(repo: Path) -> dict[str, object]:
    """Record tracked state without exposing filenames, remotes or credentials."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        changes = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=no"],
            cwd=repo,
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "head": None, "tracked_dirty": None}
    return {
        "available": True,
        "head": head,
        "tracked_dirty": bool(changes),
        "untracked_state": "not_queried; allowlisted files included independently",
    }


def runtime_version(repo: Path) -> str | None:
    """Read the literal version; never import or execute inventoried source."""
    path = repo / "src/pyfast/_version.py"
    if not path.is_file() or any(linked(part) for part in (path, path.parent, path.parent.parent)):
        return None
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "VERSION" for target in node.targets
        ):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    return None


def prepare_manifest(repo: Path) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    metadata_path = repo / "pyproject.toml"
    if linked(metadata_path):
        raise ValueError("Linked project metadata is not accepted")
    project = tomllib.loads(metadata_path.read_text(encoding="utf-8"))["project"]
    content = {
        "schema_version": "pyfast.software-manifest/1",
        "scope": "technical source inventory; ownership and rights not determined",
        "identity": {
            "name": project["name"],
            "project_version": project["version"],
            "runtime_declared_version": runtime_version(repo),
            "authors": None,
            "rights_holder": None,
            "jurisdiction": None,
        },
        "git": git_state(repo),
        "files": inventory(repo),
        "selection": {
            "roots": sorted(SOURCE_DIRS),
            "excluded_directory_names": sorted(EXCLUDED),
            "suffixes": sorted(SUFFIXES),
            "links": "excluded, including junctions",
            "rights_classification": "pending human review; inclusion does not establish ownership",
        },
        "dependencies_and_notices": {
            "status": "pending_human_review",
            "declared_dependencies": project.get("dependencies", []),
            "declared_optional_dependencies": project.get("optional-dependencies", {}),
            "declared_project_license": project.get("license"),
            "local_references": [
                {"path": name, "present": (repo / name).is_file()} for name in AUDIT_REFERENCES
            ],
            "limitation": (
                "Metadata and existing audits only; no rights grant or transitive license audit"
            ),
        },
    }
    digest = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()
    return {
        "content": content,
        "content_sha256": digest,
        "generation": {
            "created_utc": datetime.now(UTC).isoformat(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.system(),
        },
    }


def write_manifest(repo: Path, destination: Path) -> Path:
    """Write an exclusive new file; do not create folders or alter inventoried inputs."""
    repo = repo.resolve(strict=True)
    lexical = Path(os.path.abspath(destination))
    for ancestor in (lexical, *lexical.parents):
        if ancestor.exists() or ancestor.is_symlink():
            if linked(ancestor):
                raise ValueError("Output path must not traverse links or junctions")
    if any(
        part.casefold() in SOURCE_DIRS | EXCLUDED - {".work", "outputs", "runs"}
        for part in lexical.parts
    ):
        raise ValueError("Output must stay outside source, data and protected directories")
    destination = lexical.resolve()
    if destination == repo or destination.parent == repo:
        raise ValueError("Use a separate output directory or a path outside the repository")
    if destination.exists():
        raise FileExistsError("Output already exists")
    manifest = prepare_manifest(repo)
    serialized = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output", type=Path, required=True, help="New JSON file; parent must exist"
    )
    args = parser.parse_args()
    try:
        destination = write_manifest(args.repo, args.output)
    except (OSError, ValueError, KeyError, SyntaxError) as exc:
        parser.exit(2, f"Manifest not written: {exc}\n")
    print(f"Technical inventory written: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

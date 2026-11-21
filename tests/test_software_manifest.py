"""Technical inventories must preserve source and exclude unrelated resources."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def manifest_tool() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts/software_manifest.py"
    spec = importlib.util.spec_from_file_location("software_manifest", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "project"
    (repo / "src/sorbflow").mkdir(parents=True)
    (repo / "pyproject.toml").write_text(
        '[project]\nname="test-package"\nversion="0.1.dev0"\n'
        'dependencies=["pint>=0.24"]\nlicense="LicenseRef-Proprietary"\n',
        encoding="utf-8",
    )
    (repo / "src/sorbflow/_version.py").write_text('VERSION = "0.1.dev0"\n', encoding="utf-8")
    (repo / "README.md").write_text("# Synthetic fixture\n", encoding="utf-8")
    return repo


def test_manifest_deterministic_content_and_null_rights(
    manifest_tool: ModuleType,
    repository: Path,
) -> None:
    first = manifest_tool.prepare_manifest(repository)
    second = manifest_tool.prepare_manifest(repository)
    assert first["content"] == second["content"]
    assert first["content_sha256"] == second["content_sha256"]
    canonical = json.dumps(
        first["content"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == first["content_sha256"]
    assert first["generation"]["created_utc"] != second["generation"]["created_utc"]
    identity = first["content"]["identity"]
    assert identity["authors"] is identity["rights_holder"] is identity["jurisdiction"] is None
    assert identity["runtime_declared_version"] == "0.1.dev0"
    assert first["content"]["dependencies_and_notices"]["status"] == "pending_human_review"
    serialized = json.dumps(first)
    assert str(repository) not in serialized


@pytest.mark.parametrize(
    "directory",
    [
        "datasets_benchmark_pyfast",
        ".git",
        ".venv",
        ".work",
        "runs",
        "build",
        "dist",
        "resources",
        "downloads",
        "audit",
        "examples/raw",
        "benchmarks/data",
        "docs/RESOURCES",
    ],
)
def test_excluded_directories(
    manifest_tool: ModuleType,
    repository: Path,
    directory: str,
) -> None:
    path = repository / directory / "sentinel.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"must remain unchanged")
    records = manifest_tool.inventory(repository)
    assert all(record["path"] != path.relative_to(repository).as_posix() for record in records)
    assert path.read_bytes() == b"must remain unchanged"


def test_binary_raw_and_unlisted_config_excluded(
    manifest_tool: ModuleType, repository: Path
) -> None:
    root = repository / "examples"
    root.mkdir()
    for name, content in {
        "binary.exe": b"MZ",
        "raw.csv": b"time,observation",
        "fake.md": b"x\x00x",
        "nonutf.md": b"\xff",
        "sample.py": b"# own text\n",
    }.items():
        (root / name).write_bytes(content)
    (repository / "secret.json").write_text('{"secret":"excluded"}', encoding="utf-8")
    paths = {record["path"] for record in manifest_tool.inventory(repository)}
    assert "examples/sample.py" in paths
    assert not any(
        name in paths
        for name in (
            "examples/binary.exe",
            "examples/raw.csv",
            "examples/fake.md",
            "examples/nonutf.md",
            "secret.json",
        )
    )


def test_source_hash_change_and_no_execution(manifest_tool: ModuleType, repository: Path) -> None:
    first = manifest_tool.prepare_manifest(repository)
    path = repository / "src/sorbflow/_version.py"
    path.write_text('VERSION = "0.1.dev0"\nraise RuntimeError("never execute")\n', encoding="utf-8")
    second = manifest_tool.prepare_manifest(repository)
    assert first["content_sha256"] != second["content_sha256"]
    assert first["content"]["files"] != second["content"]["files"]


def test_no_overwrite_or_source_mutation(
    manifest_tool: ModuleType,
    repository: Path,
    tmp_path: Path,
) -> None:
    before = manifest_tool.inventory(repository)
    destination = tmp_path / "new.json"
    assert manifest_tool.write_manifest(repository, destination) == destination
    content = destination.read_bytes()
    with pytest.raises(FileExistsError):
        manifest_tool.write_manifest(repository, destination)
    assert destination.read_bytes() == content
    assert manifest_tool.inventory(repository) == before


@pytest.mark.parametrize(
    "target",
    [
        "src/report.json",
        "tests/report.json",
        "docs/report.json",
        ".git/report.json",
        ".venv/report.json",
        "datasets_benchmark_pyfast/report.json",
        "README.md",
        "resources/report.json",
        "REGISTRATION_PREPARATION/report.json",
    ],
)
def test_output_guards(
    manifest_tool: ModuleType,
    repository: Path,
    target: str,
) -> None:
    path = repository / target
    with pytest.raises(ValueError):
        manifest_tool.write_manifest(repository, path)
    assert not path.exists() or path.name == "README.md"


def test_links_excluded_and_output_link_rejected(
    manifest_tool: ModuleType,
    repository: Path,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "external"
    outside.mkdir()
    (outside / "external.md").write_text("not ours", encoding="utf-8")
    link = repository / "docs"
    try:
        link.symlink_to(outside, target_is_directory=True)
        (repository / "src/linked.py").symlink_to(outside / "external.md")
    except OSError as exc:
        pytest.skip(f"OS does not permit creating symlinks: {exc}")
    assert all(
        "linked" not in record["path"] and not record["path"].startswith("docs/")
        for record in manifest_tool.inventory(repository)
    )
    with pytest.raises(ValueError, match="links"):
        manifest_tool.write_manifest(repository, link / "report.json")
    assert not (outside / "report.json").exists()


def test_git_absent_recorded_not_fabricated(manifest_tool: ModuleType, repository: Path) -> None:
    state = manifest_tool.git_state(repository)
    # A fixture can be nested under a git worktree; otherwise absence is explicit.
    assert isinstance(state["available"], bool)
    if not state["available"]:
        assert state["head"] is state["tracked_dirty"] is None


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior")
def test_windows_junction_excluded_and_output_guard(
    manifest_tool: ModuleType,
    repository: Path,
    tmp_path: Path,
) -> None:
    outside = tmp_path / "external"
    outside.mkdir()
    (outside / "private.md").write_text("external sentinel", encoding="utf-8")
    junction = repository / "docs"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        check=False,
    )
    if result.returncode and b"Access is denied" in result.stderr:
        pytest.skip("Windows sandbox denies junction creation")
    assert result.returncode == 0, result.stderr
    try:
        assert manifest_tool.linked(junction)
        assert all(
            not record["path"].startswith("docs/") for record in manifest_tool.inventory(repository)
        )
        with pytest.raises(ValueError, match="links"):
            manifest_tool.write_manifest(repository, junction / "new.json")
        assert not (outside / "new.json").exists()
    finally:
        # Remove the junction alone, never recurse into its target.
        junction.rmdir()
    assert (outside / "private.md").read_text(encoding="utf-8") == "external sentinel"


def test_windows_reparse_attribute_detection(
    manifest_tool: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda self: SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=0x400,
        ),
    )
    assert manifest_tool.linked(tmp_path / "junction")


def test_linked_tree_skipped_without_reading(
    manifest_tool: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    repository: Path,
) -> None:
    docs = repository / "docs"
    docs.mkdir()
    (docs / "external.md").write_text("do not hash", encoding="utf-8")
    original = manifest_tool.linked
    monkeypatch.setattr(manifest_tool, "linked", lambda path: path == docs or original(path))
    assert all(
        not record["path"].startswith("docs/") for record in manifest_tool.inventory(repository)
    )


def test_cli_new_file_and_refusal(
    manifest_tool: ModuleType, repository: Path, tmp_path: Path
) -> None:
    destination = tmp_path / "cli_manifest.json"
    arguments = [
        sys.executable,
        str(manifest_tool.__file__),
        "--repo",
        str(repository),
        "--output",
        str(destination),
    ]
    first = subprocess.run(arguments, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    assert json.loads(destination.read_text(encoding="utf-8"))["content_sha256"]
    before = destination.read_bytes()
    second = subprocess.run(arguments, capture_output=True, check=False)
    assert second.returncode == 2
    assert b"already exists" in second.stderr
    assert destination.read_bytes() == before

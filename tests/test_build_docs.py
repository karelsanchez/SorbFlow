"""Documentation staging must not publish untracked or escaped files."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "build_docs.py"
SPEC = importlib.util.spec_from_file_location("pyfast_build_docs", MODULE)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def test_indexed_only_and_staging_cleanup(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "guide.md").write_text("# Guide", encoding="utf-8")
    (tmp_path / "private.md").write_text("not indexed", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "guide.md"], check=True)
    stage = tmp_path / ".work" / "docs_source"
    stage.mkdir(parents=True)
    (stage / "obsolete.md").write_text("old", encoding="utf-8")
    sentinel = tmp_path / ".work" / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    result = BUILDER.prepare(tmp_path)
    assert result == stage
    assert (stage / "guide.md").read_text(encoding="utf-8") == "# Guide"
    assert not (stage / "private.md").exists()
    assert not (stage / "obsolete.md").exists()
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert (stage / "index.md").exists()


def test_reject_parent_escape_before_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage = tmp_path / ".work" / "docs_source"
    stage.mkdir(parents=True)
    sentinel = stage / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(
        BUILDER.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 0, b"../outside.md\0"),
    )
    with pytest.raises(ValueError, match="Unsafe indexed path"):
        BUILDER.prepare(tmp_path)
    assert sentinel.read_text(encoding="utf-8") == "keep"

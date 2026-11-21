"""Documentation staging must not publish untracked or escaped files."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "build_docs.py"
SPEC = importlib.util.spec_from_file_location("sorbflow_build_docs", MODULE)
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


ROOT = MODULE.parents[1]


def _nav_targets(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [t for value in node.values() for t in _nav_targets(value)]
    if isinstance(node, list):
        return [t for item in node for t in _nav_targets(item)]
    return []


def test_docs_requirements_are_exactly_pinned() -> None:
    lines = (ROOT / "docs" / "requirements.txt").read_text(encoding="utf-8").splitlines()
    pins = [x.strip() for x in lines if x.strip() and not x.lstrip().startswith("#")]
    assert pins, "documentation requirements must not be empty"
    for pin in pins:
        assert "==" in pin and not any(op in pin for op in (">", "<", "~=", "!=")), pin
    names = {p.split("==")[0].split("[")[0].lower() for p in pins}
    assert {"mkdocs", "mkdocs-material", "mkdocstrings", "mkdocstrings-python"} <= names


def test_every_nav_entry_is_a_tracked_page() -> None:
    yaml = pytest.importorskip("yaml")
    config = yaml.load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    targets = _nav_targets(config["nav"])
    assert "index.md" in targets and "docs/capabilities.md" in targets
    tracked = set(
        subprocess.run(
            ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True,
        ).stdout.splitlines()
    )
    missing = [t for t in targets if t != "index.md" and t not in tracked]
    assert not missing, f"nav entries not indexed in Git: {missing}"
    assert config["strict"] == "true"


def test_read_the_docs_installs_package_and_full_history() -> None:
    text = (ROOT / ".readthedocs.yaml").read_text(encoding="utf-8")
    assert "git fetch --unshallow" in text
    assert "--prepare-only" in text
    assert "method: pip" in text and "fail_on_warning: true" in text

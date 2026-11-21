"""Source provenance and release-version invariants of the local quality command."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "project_checks", Path(__file__).resolve().parents[1] / "scripts/project_checks.py"
)
assert SPEC and SPEC.loader
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


def test_quality_snapshot_excludes_external_data_and_generated_results(tmp_path: Path) -> None:
    for directory in ("src", "examples", "datasets_benchmark_pyfast", "runs"):
        (tmp_path / directory).mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="0.2.0.dev0"')
    source = tmp_path / "src/model.py"
    source.write_text("VALUE = 1")
    baseline = checks.source_snapshot(tmp_path)
    (tmp_path / "datasets_benchmark_pyfast/raw.csv").write_text("active download")
    (tmp_path / "runs/report.json").write_text("{}")
    assert checks.source_snapshot(tmp_path) == baseline
    source.write_text("VALUE = 2")
    assert checks.source_snapshot(tmp_path) != baseline
    source.write_text("VALUE = 1")
    (tmp_path / "examples/case.json").write_text('{"value": 1}')
    assert checks.source_snapshot(tmp_path) != baseline


def test_release_version_must_match_runtime(tmp_path: Path) -> None:
    (tmp_path / "src/sorbflow").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="0.2.0.dev0"')
    version = tmp_path / "src/sorbflow/_version.py"
    version.write_text('VERSION = "0.2.0.dev0"')
    assert checks.check_version(tmp_path) == "0.2.0.dev0"
    version.write_text('VERSION = "0.3.0.dev0"')
    with pytest.raises(ValueError, match="differ"):
        checks.check_version(tmp_path)


@pytest.mark.parametrize("directory", [".git", ".venv", "datasets_benchmark_pyfast"])
def test_quality_reports_cannot_enter_protected_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory: str
) -> None:
    output = tmp_path / directory / "report"
    monkeypatch.setattr("sys.argv", ["project_checks", "--repo", str(tmp_path),
                                    "--output", str(output)])
    with pytest.raises(SystemExit) as exc:
        checks.main()
    assert exc.value.code == 2
    assert not output.exists()

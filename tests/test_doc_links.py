import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def checker():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_doc_links.py"
    spec = importlib.util.spec_from_file_location("pyfast_doc_link_checker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repository(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "API_REFERENCE.md").write_text("# API\n")
    return tmp_path


def test_local_links_fragments_percent_encoding_angle_paths_and_titles(checker, repository):
    (repository / "docs" / "sub dir").mkdir()
    (repository / "docs" / "sub dir" / "a b.md").write_text("# Space\n")
    (repository / "docs" / "named(part).md").write_text("# Named\n")
    (repository / "docs" / "named#part.md").write_text("# Encoded fragment character\n")
    (repository / "docs" / "index.md").write_text(
        "[API](../API_REFERENCE.md#units)\n"
        "[Encoded](sub%20dir/a%20b.md)\n"
        '[Angle](<sub dir/a b.md> "title")\n'
        "[Parentheses](named(part).md)\n"
        '[Escaped](named\\(part\\).md "title")\n'
        "[Encoded filename hash](named%23part.md#an-anchor)\n"
        '[Reference][api]\n[api]: ../API_REFERENCE.md "API title"\n'
        "[Only anchor](#not-a-file)\n"
    )
    assert checker.check_doc_links(repository) == []


def test_missing_file_reports_document_line_and_destination(checker, repository):
    (repository / "docs" / "index.md").write_text("# Index\n\n[Missing](missing.md)\n")
    issues = checker.check_doc_links(repository)
    assert len(issues) == 1
    assert (issues[0].source, issues[0].line, issues[0].target) == (
        "docs/index.md",
        3,
        "missing.md",
    )
    assert "missing" in issues[0].reason


def test_code_urls_anchors_and_comments_do_not_become_file_checks(checker, repository):
    (repository / "docs" / "index.md").write_text(
        "[Web](https://example.invalid/missing) [Mail](mailto:test@example.invalid)\n"
        "[Remote host is not validated](https://[not-a-valid-host/page)\n"
        "[Anchor](#missing) [Network URL](//example.invalid/page)\n"
        "`[Inline example](missing.md)`\n"
        "```markdown\n[Code example](also-missing.md)\n```\n"
        "~~~markdown\n[Other fence](never-created.md)\n~~~\n"
        "<!-- [Comment](no-such-file.md) -->\n"
    )
    assert checker.check_doc_links(repository) == []


@pytest.mark.parametrize(
    "target",
    ["../../outside.md", "%2e%2e/%2e%2e/outside.md", "../../datasets_benchmark_pyfast/outside.md"],
)
def test_workspace_escapes_rejected_even_for_ignored_tree_names(checker, repository, target):
    outside = repository.parent / "outside.md"
    outside.write_text("# It exists outside scope\n")
    (repository / "docs" / "index.md").write_text(f"[Outside]({target})\n")
    issues = checker.check_doc_links(repository)
    assert len(issues) == 1 and "escapes" in issues[0].reason


def test_windows_and_file_absolute_destinations_are_rejected(checker, repository):
    (repository / "docs" / "index.md").write_text(
        "[Drive](C:/outside/file.md)\n[File](file:///C:/outside/file.md)\n"
    )
    issues = checker.check_doc_links(repository)
    assert len(issues) == 2
    assert all("absolute" in issue.reason for issue in issues)


def test_raw_historical_trees_ignored_without_scanning_them(checker, repository):
    raw = repository / "datasets_benchmark_pyfast"
    raw.mkdir()
    (raw / "README.md").write_text("[Historical location](D:/old/file.csv)\n")
    history = repository / "docs" / "history"
    history.mkdir()
    (history / "old.md").write_text("[Old](missing-historical-file.md)\n")
    (repository / "docs" / "index.md").write_text(
        "[Raw source](../datasets_benchmark_pyfast/optional-download.csv)\n"
        "[Archived snapshot](history/optional-old-file.md)\n"
    )
    assert checker.check_doc_links(repository) == []


def test_symlink_cannot_bypass_workspace_containment(checker, repository):
    outside = repository.parent / "outside-link-target.md"
    outside.write_text("[Do not read outside documents](unrelated-missing-file.md)\n")
    link = repository / "docs" / "linked.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symbolic-link creation is unavailable in this environment")
    (repository / "docs" / "index.md").write_text("[Escaping link](linked.md)\n")
    issues = checker.check_doc_links(repository)
    assert any("source escapes" in issue.reason for issue in issues)
    assert any("destination escapes" in issue.reason for issue in issues)
    assert not any(issue.target == "unrelated-missing-file.md" for issue in issues)


def test_cli_status_and_json_report(checker, repository, capsys):
    assert checker.main(["--root", str(repository), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    (repository / "docs" / "index.md").write_text("![Image](not-present.png)\n")
    assert checker.main(["--root", str(repository), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)[0]["target"] == "not-present.png"


def test_missing_documentation_tree_is_visible(checker, tmp_path):
    issues = checker.check_doc_links(tmp_path)
    assert len(issues) == 1 and issues[0].source == "docs"


def test_invalid_encoded_path_reports_issue_instead_of_crashing(checker, repository):
    (repository / "docs" / "index.md").write_text("[Invalid](bad%00name.md)\n")
    issues = checker.check_doc_links(repository)
    assert len(issues) == 1 and "invalid local" in issues[0].reason

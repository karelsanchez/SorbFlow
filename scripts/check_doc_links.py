"""Check local destinations in the maintained docs/ Markdown tree, without network I/O.

Inline links/images, angle-bracket destinations, percent encoding and reference
definitions are supported. Fragments and remote URLs are not checked. Raw datasets,
run/scratch artifacts and explicitly historical trees are excluded after containment
checks. This is a file-existence check, not a complete Markdown renderer.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlsplit

IGNORED_TREES = (
    ("datasets_benchmark_pyfast",),
    (".work",),
    ("runs",),
    ("audit",),
    ("docs", "archive"),
    ("docs", "history"),
    ("docs", "historical"),
)


@dataclass(frozen=True, slots=True)
class LinkIssue:
    source: str
    line: int
    target: str
    reason: str


def _ignored(relative: Path) -> bool:
    parts = tuple(part.casefold() for part in relative.parts)
    return any(parts[: len(prefix)] == prefix for prefix in IGNORED_TREES)


def _visible(text: str) -> str:
    """Mask code/comments while preserving offsets and line numbers."""

    def mask(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group())

    text = re.sub(r"<!--.*?-->", mask, text, flags=re.S)
    lines, fence = [], None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence is not None:
            lines.append("".join("\n" if char == "\n" else " " for char in line))
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        elif marker:
            fence = marker[1]
            lines.append("\n" if line.endswith("\n") else "")
        else:
            lines.append(line)
    return re.sub(r"(`+).*?\1", mask, "".join(lines), flags=re.S)


def _inline_target(text: str, start: int) -> str | None:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text):
        return None
    if text[index] == "<":
        end = text.find(">", index + 1)
        return text[index + 1 : end] if end >= 0 else None
    first, depth = index, 0
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                return text[first:index]
            depth -= 1
        elif char.isspace() and depth == 0:
            return text[first:index]  # Any following quoted title is not a destination.
        index += 1
    return None


def destinations(text: str) -> list[tuple[int, str]]:
    """Extract maintained-document links, excluding examples inside code blocks."""
    visible = _visible(text)
    found = []
    for match in re.finditer(r"(?<!\\)\[[^\]\n]*\]\(", visible):
        target = _inline_target(visible, match.end())
        if target is not None:
            found.append((visible.count("\n", 0, match.start()) + 1, target))
    for match in re.finditer(r"(?m)^ {0,3}\[[^\]\n]+\]:\s*(<[^>]+>|\S+)", visible):
        target = match[1]
        found.append((visible.count("\n", 0, match.start()) + 1, target.strip("<>")))
    return found


def check_doc_links(root: str | Path) -> list[LinkIssue]:
    """Check only docs/; never follow a destination outside the repository root."""
    root = Path(root).resolve()
    docs = root / "docs"
    if not docs.is_dir():
        return [LinkIssue("docs", 0, "", "maintained docs directory is missing")]
    issues = []
    for source in sorted(docs.rglob("*.md")):
        label = source.relative_to(root).as_posix()
        if not source.resolve().is_relative_to(root):
            issues.append(LinkIssue(label, 0, "", "source escapes repository root"))
            continue
        if _ignored(source.relative_to(root)):
            continue
        try:
            links = destinations(source.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError) as exc:
            issues.append(LinkIssue(label, 0, "", f"cannot read Markdown: {exc}"))
            continue
        for line, target in links:
            if not target or target.startswith("#"):
                continue
            unescaped = re.sub(r"\\([\\`()\[\]<> ])", r"\1", target)
            windows_drive = bool(PureWindowsPath(unquote(unescaped)).drive)
            scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", unescaped)
            if unescaped.startswith("//") or (
                scheme and not windows_drive and scheme[1].casefold() != "file"
            ):
                continue
            if (scheme and scheme[1].casefold() == "file") or windows_drive:
                issues.append(
                    LinkIssue(label, line, target, "absolute local paths are not portable")
                )
                continue
            parsed = urlsplit(unescaped)
            local_path = unquote(parsed.path).replace("\\", "/")
            if "\0" in local_path:
                issues.append(LinkIssue(label, line, target, "invalid local destination: NUL byte"))
                continue
            try:
                local = (source.parent / local_path).resolve()
            except (OSError, ValueError, RuntimeError) as exc:
                issues.append(LinkIssue(label, line, target, f"invalid local destination: {exc}"))
                continue
            if not local.is_relative_to(root):
                issues.append(LinkIssue(label, line, target, "destination escapes repository root"))
            elif _ignored(local.relative_to(root)):
                continue
            elif not local.exists():
                issues.append(LinkIssue(label, line, target, "local destination is missing"))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="Print structured issues")
    args = parser.parse_args(argv)
    issues = check_doc_links(args.root)
    if args.json:
        print(json.dumps([asdict(issue) for issue in issues], indent=2))
    else:
        for issue in issues:
            print(f"{issue.source}:{issue.line}: {issue.target!r}: {issue.reason}")
        print(f"Maintained Markdown links: {len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

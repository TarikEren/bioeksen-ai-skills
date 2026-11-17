#!/usr/bin/env python3
"""Check a project's code comments against sds-project's limits.

    python check_comments.py PATH [PATH ...]

A comment block holds at most 5 lines, and a comment line at most 30 words,
per **Comments** in sds-project/SKILL.md. A block is a run of lines holding
only comments: line comments in a row, or one block comment, its delimiters'
lines included. A trailing comment beside code is a block of its own.

It reads the comments of C-like languages (// and /* */), of #-languages, of
SQL (-- and /* */), of CSS (/* */) and of markup (<!-- -->), skipping strings
so that "https://" or "#fff" is not taken for a comment. A file in no known
language is skipped. Folders are walked, except dependencies and build output.

It exits 0 when every comment is within the limits, 1 when one is not, each
reported with its file and line, and 2 when a path does not exist. It needs
only the standard library.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

MAX_LINES = 5
MAX_WORDS = 30
SKIPPED_DIRS = {".git", "node_modules", ".next", "dist", "build", "coverage", "vendor",
                ".venv", "venv", "__pycache__", "target", ".turbo"}
# A word of a comment is anything but the markers around it.
MARKER = re.compile(r"^(?:[*/#-]+|<!--|-->)$")


class Syntax(NamedTuple):
    line: tuple[str, ...]
    block: tuple[str, str] | None
    quotes: tuple[str, ...]  # string delimiters, the longest first
    hash_needs_space: bool = False


C_LIKE = Syntax(("//",), ("/*", "*/"), ("`", '"', "'"))
HASH = Syntax(("#",), None, ('"""', "'''", '"', "'"), hash_needs_space=True)
SQL = Syntax(("--",), ("/*", "*/"), ("'", '"'))
CSS = Syntax((), ("/*", "*/"), ('"', "'"))
MARKUP = Syntax((), ("<!--", "-->"), ())

SUFFIXES = {
    **dict.fromkeys((".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".java",
                     ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".go", ".rs", ".swift",
                     ".kt", ".kts", ".scala"), C_LIKE),
    **dict.fromkeys((".py", ".sh", ".bash", ".rb", ".yml", ".yaml", ".toml", ".ps1",
                     ".r", ".pl"), HASH),
    ".sql": SQL,
    **dict.fromkeys((".css", ".scss", ".less"), CSS),
    **dict.fromkeys((".html", ".htm", ".xml", ".svg"), MARKUP),
}
NAMES = {"Dockerfile": HASH, "Makefile": HASH}
BLOCK = object()  # the scanner's state inside a block comment


class Line(NamedTuple):
    code: bool              # anything but whitespace and comments
    comment: str | None     # the comment text on the line, None when there is none


def scan(text: str, syntax: Syntax) -> list[Line]:
    """Each line's code and comment text, carrying block comments and long
    strings across lines."""
    lines: list[Line] = []
    state: object | str | None = None
    for number, raw in enumerate(text.split("\n")):
        code, parts = False, []
        if state is BLOCK:
            parts.append("")
        i = 0
        if number == 0 and syntax is HASH and raw.startswith("#!"):
            code, i = True, len(raw)  # a shebang is not a comment
        while i < len(raw):
            if state is BLOCK:
                end = raw.find(syntax.block[1], i)
                parts.append(raw[i:] if end < 0 else raw[i:end])
                i, state = (len(raw), BLOCK) if end < 0 else (end + len(syntax.block[1]), None)
                continue
            if isinstance(state, str):
                j = i
                while j < len(raw) and not raw.startswith(state, j):
                    j += 2 if raw[j] == "\\" else 1
                code = True
                i, state = (len(raw), state) if j >= len(raw) else (j + len(state), None)
                continue
            if syntax.block and raw.startswith(syntax.block[0], i):
                state, i = BLOCK, i + len(syntax.block[0])
                parts.append("")
                continue
            marker = next((m for m in syntax.line if raw.startswith(m, i)), None)
            if marker and not (syntax.hash_needs_space and i and not raw[i - 1].isspace()):
                parts.append(raw[i + len(marker):])
                break
            quote = next((q for q in syntax.quotes if raw.startswith(q, i)), None)
            if quote:
                state, code, i = quote, True, i + len(quote)
                continue
            code = code or not raw[i].isspace()
            i += 1
        if isinstance(state, str) and len(state) == 1 and state != "`":
            state = None  # a one-line string ends with its line
        lines.append(Line(code, " ".join(parts) if parts else None))
    return lines


def findings(path: Path, syntax: Syntax) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    found, run = [], 0
    lines = scan(text, syntax) + [Line(True, None)]
    for number, line in enumerate(lines, 1):
        if line.comment is not None:
            count = len([w for w in line.comment.split() if not MARKER.match(w)])
            if count > MAX_WORDS:
                found.append(f"{path}:{number}: a comment line of {count} words; at most "
                             f"{MAX_WORDS}")
        if line.comment is not None and not line.code:
            run += 1
            continue
        if run > MAX_LINES:
            found.append(f"{path}:{number - run}: a comment block of {run} lines; at most "
                         f"{MAX_LINES}")
        run = 0
    return sorted(found, key=lambda f: int(f.rsplit(":", 2)[-2]))


def files(paths: list[Path]) -> list[tuple[Path, Syntax]]:
    found = []
    for path in paths:
        candidates = [path] if path.is_file() else sorted(
            p for p in path.rglob("*")
            if p.is_file() and not SKIPPED_DIRS & set(p.relative_to(path).parts))
        for candidate in candidates:
            syntax = NAMES.get(candidate.name) or SUFFIXES.get(candidate.suffix.lower())
            if syntax:
                found.append((candidate, syntax))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check code comments against sds-project's "
                                                 "limits.")
    parser.add_argument("paths", nargs="+", type=Path, help="files or folders to check")
    args = parser.parse_args(argv)
    missing = [str(path) for path in args.paths if not path.exists()]
    if missing:
        print(f"NOT RUN - {', '.join(missing)} does not exist")
        return 2
    checked = files(args.paths)
    problems = [problem for path, syntax in checked for problem in findings(path, syntax)]
    for problem in problems:
        print(problem)
    if problems:
        print(f"FAIL - {len(problems)} comment{'s' if len(problems) != 1 else ''} over the "
              "limits")
        return 1
    print(f"OK - {len(checked)} files, every comment block within {MAX_LINES} lines and every "
          f"comment line within {MAX_WORDS} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())

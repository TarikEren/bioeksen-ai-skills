#!/usr/bin/env python3
"""Check that every feat and fix commit changes a test, per sds-testing.

    python check_tests.py --range A..B

Every non-merge feat or fix commit in the range must change at least one test
path, or carry a Test-Exempt trailer in its final paragraph naming one of the
exemptions sds-testing lists. Other types are not checked: a refactor keeps
its tests green rather than adding one, and a docs commit has nothing to test.

What counts as a test path is read from .bioeksen/test-paths at the current
checkout — one glob per line, # for comments — or the defaults below when the
file is absent. Reading it from the checkout means a pull request can change
its own patterns, so every commit in the range that edits the file is
printed, for review to see.

A pattern without a / is matched against a file's name; one with a / against
the file's path and every /-suffix of it, so tests/* matches tests/a.py and
service/tests/a.py alike. Matching is case-sensitive on every platform.

Run it over the range a change adds, never back past the release the rule
began after: earlier commits predate it. In a monorepo, the commits of a
history moved into it predate it too, and are listed as notices, unchecked.
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
from pathlib import Path

from change_id import repo_root
from commit_msg import SUBJECT, TEST_EXEMPTIONS, TESTED_TYPES, clean, paragraphs
from units import predates_monorepo

PATTERNS_FILE = Path(".bioeksen") / "test-paths"
# Directories that hold tests, and the file names test runners look for, per
# language. Deliberately not *.test.* or *.spec.*, which also match
# configuration such as appsettings.test.json or openapi.spec.yaml.
DEFAULT_PATTERNS: tuple[str, ...] = (
    "test/*", "tests/*", "__tests__/*", "spec/*",
    "test_*.py", "*_test.py", "*_test.go", "*_spec.rb",
    "*.test.ts", "*.test.tsx", "*.test.js", "*.test.jsx",
    "*.spec.ts", "*.spec.tsx", "*.spec.js", "*.spec.jsx",
    "*Test.java", "*Tests.java", "*IT.java", "*Test.kt", "*Tests.kt",
    "*Test.cs", "*Tests.cs",
)


def read_patterns(root: Path) -> list[str]:
    """The project's test path globs, or the defaults when it declares none."""
    path = root / PATTERNS_FILE
    if not path.is_file():
        return list(DEFAULT_PATTERNS)
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def is_test(path: str, patterns) -> bool:
    """Whether a repository path matches any of the test path globs."""
    parts = path.split("/")
    suffixes = ["/".join(parts[i:]) for i in range(len(parts))]
    for pattern in patterns:
        candidates = suffixes if "/" in pattern else [parts[-1]]
        if any(fnmatch.fnmatchcase(candidate, pattern) for candidate in candidates):
            return True
    return False


def exemption(message: str) -> str | None:
    """The exemption a message names in its final paragraph, if a known one."""
    blocks = paragraphs(clean(message))
    for line in blocks[-1] if len(blocks) > 1 else []:
        if line.startswith("Test-Exempt:"):
            value = line.partition(":")[2].strip()
            return value if value in TEST_EXEMPTIONS else None
    return None


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout


def findings(root: Path, revisions: str) -> tuple[list[str], list[str], int]:
    """(failures, notices, commits checked) for the non-merge commits in range."""
    patterns = read_patterns(root)
    log = git(root, "log", "--no-merges", "--format=%H%x00%B%x1e", revisions)
    failures: list[str] = []
    notices: list[str] = []
    checked = 0
    for record in filter(str.strip, log.split("\x1e")):
        sha, _, body = record.strip("\n").partition("\x00")
        checked += 1
        files = git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r",
                    sha).splitlines()
        subject = body.splitlines()[0] if body else ""
        if predates_monorepo(root, sha):
            notices.append(f"{sha[:10]} predates the monorepo and is not checked: {subject}")
            continue
        if PATTERNS_FILE.as_posix() in files:
            notices.append(f"{sha[:10]} changes {PATTERNS_FILE.as_posix()}: {subject}")
        parsed = SUBJECT.match(subject)
        if not parsed or parsed["type"] not in TESTED_TYPES:
            continue
        if any(is_test(f, patterns) for f in files) or exemption(body):
            continue
        failures.append(f"{sha[:10]} {subject}: changes no test and names no "
                        "Test-Exempt (see sds-testing)")
    return failures, notices, checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that feat and fix commits "
                                                 "change a test.")
    parser.add_argument("--range", required=True, metavar="A..B",
                        help="the revision range to check")
    parser.add_argument("--root", type=Path,
                        help="repository root (default: the enclosing git repository)")
    args = parser.parse_args(argv)
    failures, notices, checked = findings(args.root or repo_root(Path.cwd()), args.range)
    for notice in notices:
        print(f"note: {notice}")
    for failure in failures:
        print(failure)
    print(f"{checked - len(failures)} of {checked} commits in {args.range} pass the test check")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

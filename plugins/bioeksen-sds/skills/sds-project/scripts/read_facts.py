#!/usr/bin/env python3
"""Read a project's recorded choices, the facts under .bioeksen/.

    python read_facts.py [--path DIR] [FACT ...]

Prints each fact as fact=value, read from the nearest .bioeksen/{fact} above
DIR (the working directory by default), never past the repository's root, per
sds-project/SKILL.md. Every fact is read unless some are named.

It exits 0 when every fact read holds an allowed value, 1 when one holds
another value, and 2 when one is missing or a name is not a fact: a missing
fact is asked of the user, never guessed. It needs only the standard library.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SOFTWARE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Each fact and its allowed values; None means a format instead of a list.
FACTS: dict[str, tuple[str, ...] | None] = {
    "software-id": None,
    "git-provider": ("github", "gitlab"),
    "identity-provider": ("entra-id", "keycloak"),
    "log-aggregator": ("present", "none"),
    "bio-softop": ("present", "none"),
    "test-order": ("tests-first", "implementation-first"),
}


def repository_root(start: Path) -> Path | None:
    """The nearest directory at or above start holding .git, if any."""
    for folder in (start, *start.parents):
        if (folder / ".git").exists():
            return folder
    return None


def find(fact: str, start: Path) -> Path | None:
    """The nearest .bioeksen/{fact} at or above start, never past the root."""
    root = repository_root(start)
    for folder in (start, *start.parents):
        candidate = folder / ".bioeksen" / fact
        if candidate.is_file():
            return candidate
        if folder == root:
            return None
    return None


def problem(fact: str, value: str) -> str | None:
    allowed = FACTS[fact]
    if allowed is None:
        if len(value) > 63 or not SOFTWARE_ID.match(value):
            return "is not a software id: lowercase words joined by '-', at most 63 characters"
        return None
    if value not in allowed:
        return f"is not one of {', '.join(allowed)}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a project's facts under .bioeksen/.")
    parser.add_argument("--path", type=Path, default=Path.cwd(),
                        help="where to read from: a file or folder of the project")
    parser.add_argument("facts", nargs="*", help=f"facts to read: {', '.join(FACTS)}")
    args = parser.parse_args(argv)

    unknown = [fact for fact in args.facts if fact not in FACTS]
    if unknown:
        print(f"NOT RUN - {', '.join(unknown)} is not a fact: {', '.join(FACTS)}")
        return 2
    start = args.path.resolve()
    if start.is_file():
        start = start.parent

    missing = invalid = 0
    for fact in args.facts or FACTS:
        path = find(fact, start)
        if path is None:
            print(f"{fact}: missing - ask the user, and record the answer in .bioeksen/{fact}")
            missing += 1
            continue
        value = path.read_text(encoding="utf-8").strip()
        wrong = problem(fact, value)
        if wrong:
            print(f"{fact}: {value!r} in {path} {wrong}")
            invalid += 1
        else:
            print(f"{fact}={value}")
    return 2 if missing else 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())

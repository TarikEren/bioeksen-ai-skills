#!/usr/bin/env python3
"""Release units as of a commit already made, for the kit's checks.

sds-commit's mint script attributes the staged change, which is all a commit
being written needs. The kit checks commits already made, so it reads each
commit's own tree, and the paths it changes against its first parent, and
hands them to the same attribute(): one implementation of **Release units**
in sds-commit/references/release-notes.md, used both ways.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from change_id import ID_FILE, Attribution, attribute, needed_files, parse_id, software_id
from change_id import unit_dirs


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def tree_at(root: Path, revision: str) -> list[str]:
    """Every path in the revision's tree."""
    return [p for p in git(root, "ls-tree", "-r", "-z", "--name-only", revision).split("\0")
            if p]


def changed_at(root: Path, revision: str) -> list[str]:
    """The paths the revision changes against its first parent; all of them for a root."""
    return [p for p in git(root, "diff-tree", "--root", "--no-commit-id", "-r", "--name-only",
                           "--no-renames", "-z", revision).split("\0") if p]


def read_at(root: Path, revision: str, paths: list[str]) -> dict[str, str | None]:
    """Each path's content in the revision, or None where it has none."""
    request = "".join(f"{revision}:{path}\n" for path in paths).encode("utf-8")
    out = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input=request,
                         capture_output=True, check=True).stdout
    found: dict[str, str | None] = {}
    position = 0
    for path in paths:
        end = out.index(b"\n", position)
        header = out[position:end].decode("utf-8")
        position = end + 1
        if header.endswith((" missing", " ambiguous")):
            found[path] = None
            continue
        size = int(header.rsplit(" ", 1)[1])
        found[path] = out[position:position + size].decode("utf-8")
        position += size + 1
    return found


def predates(tree: list[str]) -> bool:
    """Whether a tree is from a history moved into a monorepo, before it held it:
    it holds release units' ids, and none at the root."""
    return ID_FILE.as_posix() not in tree and bool(unit_dirs(tree))


def predates_monorepo(root: Path, revision: str) -> bool:
    return predates(tree_at(root, revision))


def commit_attribution(root: Path, revision: str) -> Attribution | None:
    """The attribution a commit's paths give it, as of that commit.

    In a repository holding one service, the root's id. None for a commit that
    predates the monorepo, which these rules do not check.
    """
    tree = tree_at(root, revision)
    if not unit_dirs(tree):
        return Attribution(software_id(root))
    if predates(tree):
        return None
    return attribute(tree, read_at(root, revision, needed_files(tree)),
                     changed_at(root, revision), f" at {revision[:10]}")


def release_units(root: Path, revision: str) -> dict[str, str]:
    """Each release unit's directory and id, as of the revision; empty for a
    repository holding one service."""
    tree = tree_at(root, revision)
    marker = ID_FILE.as_posix()
    units = unit_dirs(tree)
    contents = read_at(root, revision, [f"{unit}/{marker}" for unit in units])
    return {unit: parse_id(contents[f"{unit}/{marker}"], f"{unit}/{marker} at {revision}")
            for unit in units}


def holding_units(root: Path, revision: str) -> tuple[str, ...]:
    """The ids of the units whose directories hold a path the revision changes: who a
    commit from before the monorepo belongs to."""
    changed = changed_at(root, revision)
    return tuple(sorted(unit_id for unit, unit_id in release_units(root, revision).items()
                        if any(p == unit or p.startswith(unit + "/") for p in changed)))

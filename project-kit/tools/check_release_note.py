#!/usr/bin/env python3
"""Check a release note against sds-commit/references/release-notes.md.

    python check_release_note.py VERSION [--head REV] [--previous TAG]
    python check_release_note.py SOFTWARE_ID/vVERSION [--head REV] [--previous TAG]

Run it with the release commit at HEAD, after committing the note and before
tagging — the note carries an entry for its own commit, so run any earlier and
the count is one short. On a tag push HEAD is that same commit. It checks:

  - release-notes/{VERSION}.md exists, titled and dated
  - one entry per non-merge commit in {previous}..{head}, matched by Change-Id,
    each with the commit's own type, scope and breaking marker; a first
    release, with no earlier tag, covers every commit up to {head}
  - breaking entries first, then the type order, and every breaking entry
    carrying its BREAKING CHANGE: text
  - no <software-id> placeholder
  - VERSION is the one the commits imply, and 0.1.0 for a first release

In a monorepo a release names its unit, as the tag does: bio-inventory/v2.4.0.
The note is read from that unit's directory, the previous release is the
unit's own latest earlier tag, and the commits are those **Release units**
gives the unit. A commit is breaking for the unit only when its scope names
it, and an entry minted with the monorepo's id ends by naming the units the
commit affects: (affects bio-inventory, bio-softop).
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from change_id import repo_root
from commit_msg import SUBJECT, TYPES
from units import commit_attribution, holding_units, release_units

ENTRY = re.compile(r"^- (?P<id>\S+) (?P<type>[a-z]+(?:\([^)]*\))?!?): (?P<reason>.+)$")
CHANGES = re.compile(r"^  - What changed: .+$")
VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$")
UNIT_RELEASE = re.compile(r"^(?P<unit>[a-z0-9]+(?:-[a-z0-9]+)*)/v(?P<version>.+)$")
# A new service's first release, whatever its commits, per release-notes.md.
FIRST_VERSION = "0.1.0"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout


def precedence(version: str) -> tuple:
    """A sort key in SemVer precedence: a pre-release ranks below its release, and
    numeric identifiers compare as numbers."""
    parsed = VERSION.match(version)
    if not parsed:
        return (-1,)
    core, _, pre = version.partition("-")
    numbers = tuple(int(part) for part in core.split("."))
    if not pre:
        return (*numbers, 1)
    return (*numbers, 0, *((0, int(p), "") if p.isdigit() else (1, 0, p)
                           for p in pre.split(".")))


def previous_tag(root: Path, head: str, version: str, prefix: str = "v") -> str | None:
    """The latest earlier tag of this release's kind reachable from head, or None for
    a first release: v* for a repository holding one service, {software-id}/v* for
    a unit of a monorepo.

    Sorted here rather than by git, whose version sort ranks v1.0.0-beta.1 above
    v1.0.0 unless versionsort.suffix is configured.
    """
    tags = git(root, "tag", "--merged", head, "--list", f"{prefix}*").split()
    earlier = [t for t in tags
               if t != f"{prefix}{version}" and VERSION.match(t[len(prefix):])]
    return (max(earlier, key=lambda t: precedence(t[len(prefix):])) if earlier
            else None)


def implied(previous: str | None, commits: list[dict]) -> str:
    """The version the commits imply, per the Version section of release-notes.md.

    previous is the previous release's version, without its tag's prefix.
    """
    if previous is None:
        return FIRST_VERSION
    parsed = VERSION.match(previous)
    if not parsed:
        raise SystemExit(f"the previous release {previous!r} does not name a version")
    major, minor, patch = (int(p) for p in parsed.groups())
    breaking = any(c["breaking"] for c in commits)
    feature = any(c["type"] == "feat" for c in commits)
    if major == 0:
        return f"0.{minor + 1}.0" if breaking else f"0.{minor}.{patch + 1}"
    if breaking:
        return f"{major + 1}.0.0"
    if feature:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a release note against sds-commit.")
    parser.add_argument("release", help="the released version, without the v; in a "
                                        "monorepo, the unit's tag, e.g. bio-inventory/v2.4.0")
    parser.add_argument("--head", default="HEAD", help="the release commit (default: HEAD)")
    parser.add_argument("--previous", help="the previous release's tag (default: the "
                                           "latest earlier tag of the release's kind "
                                           "reachable from --head)")
    parser.add_argument("--root", type=Path, help="repository root")
    args = parser.parse_args(argv)
    root = args.root or repo_root(Path.cwd())
    problems: list[str] = []

    units = release_units(root, args.head)
    unit_release = UNIT_RELEASE.match(args.release)
    if unit_release:
        unit, version = unit_release["unit"], unit_release["version"]
        directories = [d for d, unit_id in units.items() if unit_id == unit]
        if not directories:
            raise SystemExit(f"no release unit at {args.head} holds the id {unit!r}")
        note_dir, prefix = root / directories[0], f"{unit}/v"
    elif units:
        raise SystemExit("a monorepo releases one unit at a time: name it as its tag does, "
                         "{software-id}/v{version}, e.g. "
                         f"{next(iter(units.values()))}/v{args.release}")
    else:
        unit, version, note_dir, prefix = None, args.release, root, "v"
    if not VERSION.match(version):
        raise SystemExit(f"{version!r} is not a version such as 2.4.0 or 1.0.0-beta.1")
    note_path = note_dir / "release-notes" / f"{version}.md"
    try:
        note = note_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"{note_path} does not exist")
    lines = note.splitlines()
    if not lines or lines[0] != f"# {version}":
        problems.append(f"the note's first line is not '# {version}'")
    if not re.search(r"^Released \d{4}-\d{2}-\d{2}\.$", note, re.M):
        problems.append("the note has no 'Released YYYY-MM-DD.' line")
    if "<software-id>" in note:
        problems.append("the <software-id> placeholder has not been replaced")

    entries = []
    for number, line in enumerate(lines):
        match = ENTRY.match(line)
        if not match:
            continue
        entries.append(match.groupdict())
        if number + 1 >= len(lines) or not CHANGES.match(lines[number + 1]):
            problems.append(f"entry {match['id']} has no '  - What changed:' line after it")

    previous = args.previous or previous_tag(root, args.head, version, prefix)
    span = f"{previous}..{args.head}" if previous else args.head
    log = git(root, "log", "--no-merges", "--reverse", "--format=%H%x00%B%x1e", span)
    commits = []
    for record in filter(str.strip, log.split("\x1e")):
        sha, _, body = record.strip("\n").partition("\x00")
        subject = SUBJECT.match(body.splitlines()[0]) if body else None
        breaking = bool(subject and subject["breaking"])
        affects: tuple[str, ...] = ()
        if unit:
            found = commit_attribution(root, sha)
            if found is None:
                # A commit from before the monorepo: its own repository's, unscoped.
                if unit not in holding_units(root, sha):
                    continue
            else:
                if unit != found.software_id and unit not in found.affects:
                    continue
                affects = found.affects
                breaking = breaking and bool(subject) and subject["scope"] == unit
        ids = [l.partition(":")[2].strip() for l in body.splitlines()
               if l.startswith("Change-Id:")]
        prefix_text = body.split(":", 1)[0] if subject else None
        commits.append({"sha": sha[:10], "id": ids[0] if len(ids) == 1 else None,
                        "prefix": prefix_text, "type": subject["type"] if subject else None,
                        "breaking": breaking, "affects": affects})

    if len(entries) != len(commits):
        problems.append(f"{len(entries)} entries, but {len(commits)} non-merge commits in "
                        f"{span}{f' that reach {unit}' if unit else ''}")
    by_id = {c["id"]: c for c in commits if c["id"]}
    for c in commits:
        if not c["id"]:
            problems.append(f"commit {c['sha']} has no single Change-Id to match an entry")
    noted = {e["id"] for e in entries}
    for missing in sorted(set(by_id) - noted):
        problems.append(f"commit {by_id[missing]['sha']} ({missing}) has no entry")
    for extra in sorted(noted - set(by_id)):
        problems.append(f"entry {extra} matches no commit in the range")
    for e in entries:
        c = by_id.get(e["id"])
        if c and c["prefix"] != e["type"]:
            problems.append(f"entry {e['id']} says {e['type']!r}, its commit {c['prefix']!r}")
        if e["type"].endswith("!") and "BREAKING CHANGE:" not in e["reason"]:
            problems.append(f"breaking entry {e['id']} does not carry its BREAKING CHANGE: text")
        if c and c["affects"]:
            named = f"(affects {', '.join(c['affects'])})"
            if not e["reason"].endswith(" " + named):
                problems.append(f"entry {e['id']} does not end by naming the units its "
                                f"commit affects: {named}")

    def type_rank(change_type: str) -> int:
        kind = change_type.split("(")[0].rstrip("!")
        return TYPES.index(kind) if kind in TYPES else len(TYPES)

    rank = [(0 if e["type"].endswith("!") else 1, type_rank(e["type"])) for e in entries]
    breaking_first = [r[0] for r in rank]
    types_in_order = [r[1] for r in rank if r[0] == 1]
    if breaking_first != sorted(breaking_first) or types_in_order != sorted(types_in_order):
        problems.append("entries are not ordered breaking first, then by the type table")

    previous_version = previous[len(prefix):] if previous else None
    expected = implied(previous_version, commits)
    core = version.split("-")[0]
    declared_stable = (previous_version is not None and core == "1.0.0"
                       and previous_version.startswith("0."))
    if previous is None and core != expected:
        problems.append(f"a first release is {expected}, not {version}")
    elif core != expected and not declared_stable:
        problems.append(f"the commits since {previous} imply {expected}, not {version}")

    for problem in problems:
        print(f"  - {problem}")
    print(f"{note_path.name}: {len(entries)} entries against {len(commits)} commits in "
          f"{span}: {'FAILED' if problems else 'OK'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

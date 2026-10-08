#!/usr/bin/env python3
"""Check commit messages against sds-commit/SKILL.md.

    python commit_msg.py --hook FILE     # as a commit-msg hook
    python commit_msg.py --range A..B    # every non-merge commit in a range, for CI

As a hook it first appends a freshly minted Change-Id when the message has
none, then checks the result. It checks:

  - the subject: a known type, an optional lowercase scope, an optional !,
    and a description that does not start with a capital or end with a period
  - a blank line between the subject and anything after it
  - exactly one Change-Id trailer, in the final paragraph, in the identifier
    format, carrying the software id stored in .bioeksen/software-id; in a
    monorepo, the id **Release units** in sds-commit/references/release-notes.md
    gives the commit's paths, with exactly the Affects: and Changes-Package:
    trailers it gives, each once, in the final paragraph
  - a BREAKING CHANGE: footer on every commit whose subject carries !, and
    no such footer without the !
  - at most one Test-Exempt trailer, only on a feat or fix commit, in the
    final paragraph, naming one of the exemptions sds-testing lists
  - Fixes-Log trailers only on a fix commit, in the final paragraph, each
    naming one aggregator recordId
  - no <software-id> placeholder left anywhere

In a monorepo, --range attributes each commit against its first parent, and
lists as notices, unchecked, the commits of a history moved into it, which
predate it. The hook attributes the staged change when it mints the
Change-Id. A message that already carries one is checked for its form
alone: an amended or reworded commit's staged change is not its whole
change, so only --range can attribute it.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from change_id import CHANGE_ID, Attribution, attribution, mint, repo_root
from units import commit_attribution

# The type table in sds-commit/SKILL.md, in its order.
TYPES = ("feat", "fix", "refactor", "perf", "style", "test", "docs", "build",
         "ops", "chore", "revert")
SUBJECT = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?: (?P<description>.*)$")
SCOPE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
# The types whose commits must change a test or name an exemption, and the
# exemptions themselves — the table in sds-testing/SKILL.md, which invariant
# 11 holds this tuple to.
TESTED_TYPES = ("feat", "fix")
TEST_EXEMPTIONS = ("docs", "config", "generated", "acceptance")
TRAILER = re.compile(r"^[A-Za-z][A-Za-z0-9-]*: ")
SCISSORS = "# ------------------------ >8 ------------------------"
# Messages git or an autosquash workflow writes, which a hook lets through;
# --range still rejects the fixups, which must be squashed before merging.
PASSED_BY_HOOK = ("Merge ", "Revert \"", "fixup! ", "squash! ", "amend! ")


def clean(message: str) -> str:
    """The message as git will store it: no comment lines, nothing below scissors."""
    message = message.split(SCISSORS)[0]
    lines = [line.rstrip() for line in message.splitlines() if not line.startswith("#")]
    return "\n".join(lines).strip("\n")


def paragraphs(message: str) -> list[list[str]]:
    blocks, current = [], []
    for line in message.splitlines():
        if line.strip():
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def check(message: str, expected: str | Attribution | None) -> list[str]:
    """Every problem with one cleaned message; an empty list means it conforms.

    expected is the attribution the commit's paths give it, or a single-service
    repository's id; None checks the message's form alone.
    """
    if isinstance(expected, str):
        expected = Attribution(expected)
    problems: list[str] = []
    lines = message.splitlines()
    if not lines or not lines[0].strip():
        return ["the message is empty"]

    subject = SUBJECT.match(lines[0])
    if not subject:
        problems.append(f"subject {lines[0]!r} is not <type>(<scope>): <description>")
        breaking = False
    else:
        kind, scope, description = subject["type"], subject["scope"], subject["description"]
        breaking = bool(subject["breaking"])
        if kind not in TYPES:
            problems.append(f"type {kind!r} is not one of {', '.join(TYPES)}")
        if scope is not None and not SCOPE.match(scope):
            problems.append(f"scope {scope!r} is not a lowercase word")
        if not description.strip():
            problems.append("the description is empty")
        elif description[0].isupper():
            problems.append("the description starts with a capital letter")
        if description.endswith("."):
            problems.append("the description ends with a period")
    if len(lines) > 1 and lines[1].strip():
        problems.append("the subject is not followed by a blank line")

    change_ids = [line for line in lines if line.startswith("Change-Id:")]
    if len(change_ids) != 1:
        problems.append(f"{len(change_ids)} Change-Id trailers; exactly one is required")
    else:
        value = change_ids[0].partition(":")[2].strip()
        parsed = CHANGE_ID.match(value)
        if not parsed:
            problems.append(f"Change-Id {value!r} is not "
                            "{software-id}-{YYYYMMDDTHHMMSS}-{random}")
        elif expected and parsed["software_id"] != expected.software_id:
            if expected.monorepo:
                problems.append(f"Change-Id carries {parsed['software_id']!r}, but the paths "
                                f"the commit changes attribute it to "
                                f"{expected.software_id!r} (see Release units in "
                                "sds-commit/references/release-notes.md)")
            else:
                problems.append(f"Change-Id carries {parsed['software_id']!r}, but "
                                f".bioeksen/software-id holds {expected.software_id!r}")
        if change_ids[0] not in paragraphs(message)[-1]:
            problems.append("the Change-Id trailer is not in the final paragraph")

    footer = any(line.startswith("BREAKING CHANGE:") for line in lines)
    if breaking and not footer:
        problems.append("the subject carries ! but there is no BREAKING CHANGE: footer")
    if footer and not breaking:
        problems.append("there is a BREAKING CHANGE: footer but the subject carries no !")
    if breaking and subject and expected and expected.monorepo:
        # The scope names the one unit the change breaks; every other unit it
        # affects counts it by its type, per Versioning in sds-commit/SKILL.md.
        breakable = expected.affects or (expected.software_id,)
        if subject["scope"] not in breakable:
            problems.append("a breaking commit in a monorepo names the unit it breaks as "
                            f"its scope: one of {', '.join(map(repr, breakable))}")

    exemptions = [line for line in lines if line.startswith("Test-Exempt:")]
    if len(exemptions) > 1:
        problems.append(f"{len(exemptions)} Test-Exempt trailers; at most one is allowed")
    for line in exemptions[:1]:
        value = line.partition(":")[2].strip()
        if value not in TEST_EXEMPTIONS:
            problems.append(f"Test-Exempt names {value!r}, which is not one of "
                            f"{', '.join(TEST_EXEMPTIONS)} (see sds-testing)")
        if line not in paragraphs(message)[-1]:
            problems.append("the Test-Exempt trailer is not in the final paragraph")
        if subject and subject["type"] not in TESTED_TYPES:
            problems.append(f"a Test-Exempt trailer on a {subject['type']} commit, which "
                            "needs none")
    fixes = [line for line in lines if line.startswith("Fixes-Log:")]
    for line in fixes:
        value = line.partition(":")[2].strip()
        if not value or any(character.isspace() for character in value):
            problems.append(f"Fixes-Log {value!r} does not name one recordId")
        if line not in paragraphs(message)[-1]:
            problems.append("a Fixes-Log trailer is not in the final paragraph")
    if fixes and subject and subject["type"] != "fix":
        problems.append(f"a Fixes-Log trailer on a {subject['type']} commit; only a fix "
                        "resolves a log record")
    if expected:
        problems += _unit_trailers(lines, paragraphs(message)[-1], expected)
    if "<software-id>" in message:
        problems.append("the <software-id> placeholder has not been replaced")
    return problems


def _unit_trailers(lines: list[str], final: list[str], expected: Attribution) -> list[str]:
    """Problems with a message's Affects: and Changes-Package: trailers."""
    problems: list[str] = []
    for key, wanted, verb in (("Affects", expected.affects, "affect"),
                              ("Changes-Package", expected.packages, "change")):
        found = [line for line in lines if line.startswith(f"{key}:")]
        values = [line.partition(":")[2].strip() for line in found]
        if any(line not in final for line in found):
            problems.append(f"an {key}: trailer is not in the final paragraph")
        for value in sorted(set(values)):
            if values.count(value) > 1:
                problems.append(f"{key}: names {value!r} twice")
        for value in sorted(set(values) - set(wanted)):
            problems.append(f"{key}: names {value!r}, which the commit does not {verb}")
        for value in wanted:
            if value not in values:
                problems.append(f"no {key}: trailer names {value!r}, which the commit "
                                f"does {verb}")
    return problems


def with_change_id(message: str, change_id: str,
                   trailers: tuple[str, ...] | list[str] = ()) -> str:
    """The message with a Change-Id, then trailers, first in its trailer paragraph."""
    blocks = paragraphs(message)
    added = [f"Change-Id: {change_id}", *trailers]
    if len(blocks) > 1 and all(TRAILER.match(line) for line in blocks[-1]):
        blocks[-1][:0] = added
    else:
        blocks.append(added)
    return "\n\n".join("\n".join(block) for block in blocks) + "\n"


def run_hook(path: Path, root: Path) -> int:
    message = clean(path.read_text(encoding="utf-8"))
    if message.startswith(PASSED_BY_HOOK):
        return 0
    found = attribution(root)
    expected = found if not found.monorepo else None
    if not any(line.startswith("Change-Id:") for line in message.splitlines()):
        message = with_change_id(message, mint(found.software_id), found.trailers())
        path.write_text(message, encoding="utf-8")
        expected = found
    problems = check(message, expected)
    for problem in problems:
        print(f"commit-msg: {problem}", file=sys.stderr)
    if problems:
        print("commit-msg: see sds-commit/SKILL.md", file=sys.stderr)
    return 1 if problems else 0


def run_range(revisions: str, root: Path) -> int:
    log = subprocess.run(["git", "log", "--no-merges", "--format=%H%x00%B%x1e", revisions],
                         cwd=root, capture_output=True, text=True, check=True).stdout
    failed = checked = 0
    for record in filter(str.strip, log.split("\x1e")):
        sha, _, body = record.strip("\n").partition("\x00")
        expected = commit_attribution(root, sha)
        if expected is None:
            print(f"note: {sha[:10]} predates the monorepo and is not checked: "
                  f"{body.splitlines()[0] if body else ''}")
            continue
        checked += 1
        problems = check(clean(body), expected)
        if problems:
            failed += 1
            print(f"{sha[:10]} {body.splitlines()[0] if body else ''}")
            for problem in problems:
                print(f"    - {problem}")
    print(f"{checked - failed} of {checked} commits in {revisions} conform")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check commit messages against sds-commit.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--hook", type=Path, metavar="FILE",
                      help="the message file git passes to a commit-msg hook")
    mode.add_argument("--range", metavar="A..B", help="a revision range to check")
    parser.add_argument("--root", type=Path,
                        help="repository root (default: the enclosing git repository)")
    args = parser.parse_args(argv)
    root = args.root or repo_root(Path.cwd())
    return run_hook(args.hook, root) if args.hook else run_range(args.range, root)


if __name__ == "__main__":
    raise SystemExit(main())

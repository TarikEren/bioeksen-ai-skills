#!/usr/bin/env python3
"""Read a project's recorded choices: its facts and its services, under .bioeksen/.

    python read_facts.py [--path DIR] [NAME ...]

A NAME is a fact, such as test-order, or a service, as services/{capability}.
Each is read from the nearest .bioeksen/ above DIR (the working directory by
default), never past the repository's root, per sds-project/SKILL.md. Every
fact and every service found is read unless some are named.

A fact prints as fact=value. A service is .bioeksen/services/{capability}.md,
whose opening Key: value lines say whether it is used, and, when it is, what
was learned about it; it prints as services/{capability}=used or =not used.

It exits 0 when everything read is valid, 1 when something holds a value or
field outside the rules, and 2 when something is missing or a name is neither:
a missing fact or service is asked of the user, never guessed. It needs only
the standard library.
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
    "test-order": ("tests-first", "implementation-first"),
}

CAPABILITY = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
FIELD = re.compile(r"^([A-Z][A-Za-z ]*?):\s*(.*?)\s*$")
# Determined at initialization, because every app needs the answer.
REQUIRED = ("log-aggregator",)
STATUS = ("used", "not used")
WHEN_USED = ("Service", "Purpose", "Reached by", "Interface")
# The fields a capability adds when it is used, each with its allowed values.
ADDED: dict[str, dict[str, tuple[str, ...]]] = {}


def repository_root(start: Path) -> Path | None:
    """The nearest directory at or above start holding .git, if any."""
    for folder in (start, *start.parents):
        if (folder / ".git").exists():
            return folder
    return None


def find(name: str, start: Path) -> Path | None:
    """The nearest .bioeksen/{name} at or above start, never past the root."""
    root = repository_root(start)
    for folder in (start, *start.parents):
        candidate = folder / ".bioeksen" / name
        if candidate.is_file():
            return candidate
        if folder == root:
            return None
    return None


def capabilities(start: Path) -> list[str]:
    """Every capability a services file above start names, and the required ones."""
    root = repository_root(start)
    found = set(REQUIRED)
    for folder in (start, *start.parents):
        services = folder / ".bioeksen" / "services"
        if services.is_dir():
            found |= {path.stem for path in services.glob("*.md")}
        if folder == root:
            break
    return sorted(found)


def problem(fact: str, value: str) -> str | None:
    allowed = FACTS[fact]
    if allowed is None:
        if len(value) > 63 or not SOFTWARE_ID.match(value):
            return "is not a software id: lowercase words joined by '-', at most 63 characters"
        return None
    if value not in allowed:
        return f"is not one of {', '.join(allowed)}"
    return None


def fields(text: str) -> tuple[dict[str, str], list[str]]:
    """The opening Key: value lines, up to the first blank line, and any malformed ones."""
    found: dict[str, str] = {}
    wrong = []
    for line in text.strip().splitlines():
        if not line.strip():
            break
        match = FIELD.match(line)
        if not match:
            wrong.append(f"{line.strip()!r} is not a 'Key: value' line")
        elif match.group(1) in found:
            wrong.append(f"{match.group(1)} is given twice")
        else:
            found[match.group(1)] = match.group(2)
    return found, wrong


def service_problems(capability: str, found: dict[str, str]) -> list[str]:
    wrong = []
    status = found.get("Status")
    if status not in STATUS:
        wrong.append(f"Status {status!r} is not one of {', '.join(STATUS)}")
    if not found.get("Answered by"):
        wrong.append("Answered by is missing: the person, or the decision it was inferred from")
    if status != "used":
        return wrong
    for name in WHEN_USED:
        if not found.get(name):
            wrong.append(f"{name} is missing, which a used service needs")
    for name, allowed in ADDED.get(capability, {}).items():
        if found.get(name) not in allowed:
            wrong.append(f"{name} {found.get(name)!r} is not one of {', '.join(allowed)}")
    return wrong


def read_service(capability: str, start: Path) -> tuple[str, str]:
    """('ok', status), ('invalid', problems) or ('missing', advice) for one service."""
    path = find(f"services/{capability}.md", start)
    if path is None:
        return "missing", (f"services/{capability}: missing - determine whether the project "
                           "needs it, from its specification or by asking the user, and record "
                           f"the answer in .bioeksen/services/{capability}.md")
    found, wrong = fields(path.read_text(encoding="utf-8"))
    wrong += service_problems(capability, found)
    if wrong:
        return "invalid", "\n".join(f"services/{capability}: {w}, in {path}" for w in wrong)
    return "ok", f"services/{capability}={found['Status']}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a project's facts and services under .bioeksen/.")
    parser.add_argument("--path", type=Path, default=Path.cwd(),
                        help="where to read from: a file or folder of the project")
    parser.add_argument("names", nargs="*",
                        help=f"facts ({', '.join(FACTS)}) or services/{{capability}}")
    args = parser.parse_args(argv)

    start = args.path.resolve()
    if start.is_file():
        start = start.parent
    facts, services, unknown = [], [], []
    for name in args.names:
        capability = name.removeprefix("services/")
        if name == capability:
            if name in FACTS:
                facts.append(name)
            else:
                unknown.append(f"{name} is not a fact: {', '.join(FACTS)}")
        elif CAPABILITY.match(capability):
            services.append(capability)
        else:
            unknown.append(f"{capability!r} is not a capability: lowercase words joined by '-'")
    if unknown:
        print(f"NOT RUN - {'; '.join(unknown)}")
        return 2
    if not args.names:
        facts, services = list(FACTS), capabilities(start)

    missing = invalid = 0
    for fact in facts:
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
    for capability in services:
        outcome, text = read_service(capability, start)
        print(text)
        missing += outcome == "missing"
        invalid += outcome == "invalid"
    return 2 if missing else 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())

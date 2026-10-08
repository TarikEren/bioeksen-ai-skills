#!/usr/bin/env python3
"""Mint a change identifier for a commit's Change-Id trailer.

    python mint_change_id.py [--root DIR]

Prints {software-id}-{timestamp}-{random}, e.g.
bioeksen-sds-20261002T131500-4c1e, in the format
references/release-notes.md defines. The timestamp is UTC+03:00 with no
zone suffix. Run it from anywhere inside the repository the commit belongs
to, after staging the commit.

The software id is read from .bioeksen/software-id, where
sds-logging/references/log-record.md says it is stored. It is never written
into this script and never guessed: this script ships with the plugin and
runs for every project, so a built-in id would label every other project's
commits as one project's. When a file it needs is missing, empty or
malformed the script exits non-zero and says so — ask for the id, write it
there, and run again.

In a repository holding one service, the id is the one at the root. In a
monorepo, whose release units each hold their own id below the root, the
script works out which units the staged changes affect, per **Release units**
in references/release-notes.md. It mints with that unit's id when they
affect exactly one, and otherwise with the monorepo's id from the root,
printing after it the Affects: and Changes-Package: trailers the commit
carries, one per line.

Minting is local by rule and makes no network call. The four random hex
characters keep two identifiers minted in the same second distinct.
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import NamedTuple

# SoftwareId in sds-api-design/references/openapi.yaml.
SOFTWARE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOFTWARE_ID_MAX = 63
# The zone every timestamp is minted in. A fixed offset rather than a named
# zone: Türkiye has kept UTC+03:00 all year since 2016, and an offset can
# never shift or repeat an hour.
MINT_ZONE = timezone(timedelta(hours=3), "UTC+03:00")
# {software-id}-{YYYYMMDDTHHMMSS}-{four or more random characters}. The
# optional Z accepts identifiers minted before the change to UTC+03:00, which
# carry a UTC time and stay valid; the Z is what tells the two apart.
CHANGE_ID = re.compile(
    r"^(?P<software_id>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<timestamp>\d{8}T\d{6}Z?)-(?P<random>[a-z0-9]{4,})$")
ID_FILE = Path(".bioeksen") / "software-id"
# The monorepo's workspace, and the root files every unit's closure holds,
# per **Release units**; root tsconfig*.json files join them.
WORKSPACE_FILE = "pnpm-workspace.yaml"
LOCKFILE = "pnpm-lock.yaml"
ROOT_BUILD_FILES = frozenset({"package.json", WORKSPACE_FILE, "turbo.json", ".npmrc",
                              ".nvmrc"})
ROOT_TSCONFIG = re.compile(r"^tsconfig[^/]*\.json$")
DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "peerDependencies",
                     "optionalDependencies")


class Attribution(NamedTuple):
    """The id a commit's Change-Id carries, and the trailers that go beside it."""
    software_id: str
    affects: tuple[str, ...] = ()
    packages: tuple[str, ...] = ()
    monorepo: bool = False

    def trailers(self) -> list[str]:
        return ([f"Affects: {unit}" for unit in self.affects]
                + [f"Changes-Package: {name}" for name in self.packages])


def repo_root(start: Path) -> Path:
    """The enclosing git repository's root, or start when there is none."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start,
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return start
    return Path(out.stdout.strip())


def parse_id(value: str | None, where: object) -> str:
    """A stored id, stripped and checked, or exit explaining what is wrong."""
    if value is None:
        raise SystemExit(f"{where} does not exist. The software id is supplied by the "
                         "project and never guessed: ask for it, then write it there.")
    value = value.strip()
    if not value:
        raise SystemExit(f"{where} is empty. The software id is supplied by the project "
                         "and never guessed: ask for it, then write it there.")
    if not SOFTWARE_ID.match(value) or len(value) > SOFTWARE_ID_MAX:
        raise SystemExit(f"{where} holds {value!r}, which is not a software id: lowercase "
                         f"letters and digits in hyphen-separated words, at most "
                         f"{SOFTWARE_ID_MAX} characters.")
    return value


def software_id(root: Path) -> str:
    """The id stored in .bioeksen/software-id, or exit explaining what is wrong."""
    path = root / ID_FILE
    try:
        value = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        value = None
    return parse_id(value, path)


def mint(software: str, now: datetime | None = None) -> str:
    """An identifier for now, or for the given aware datetime, in UTC+03:00."""
    moment = (now or datetime.now(timezone.utc)).astimezone(MINT_ZONE)
    return f"{software}-{moment.strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(2)}"


# --- Release units -----------------------------------------------------------

def unit_dirs(tree: list[str]) -> list[str]:
    """The directories below the root that hold an id: the release units."""
    marker = "/" + ID_FILE.as_posix()
    return sorted(path[:-len(marker)] for path in tree if path.endswith(marker))


def needed_files(tree: list[str]) -> list[str]:
    """The files attribute() reads: the ids, the workspace file and the manifests."""
    marker = ID_FILE.as_posix()
    return [marker, WORKSPACE_FILE, *(path for path in tree if path.endswith("/package.json")),
            *(f"{unit}/{marker}" for unit in unit_dirs(tree))]


def _workspace_globs(text: str) -> list[str]:
    """The packages list of a pnpm workspace file: block or flow style, quoted or not."""
    globs: list[str] = []
    inside = False
    for raw in text.splitlines():
        line = re.sub(r"\s+#.*$", "", raw).rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not raw[0].isspace():
            key, _, rest = line.partition(":")
            inside = key.strip() == "packages"
            rest = rest.strip()
            if inside and rest.startswith("["):
                globs += [item.strip().strip("'\"") for item in rest.strip("[]").split(",")
                          if item.strip()]
                inside = False
        elif inside and line.strip().startswith("-"):
            globs.append(line.strip()[1:].strip().strip("'\""))
    return globs


def _glob(pattern: str) -> re.Pattern[str]:
    """A workspace glob as a regular expression over a directory path.

    * and ? stay within one path segment; a ** segment spans any number of
    them, none included, so apps/** matches apps itself.
    """
    parts = pattern.strip().removeprefix("./").rstrip("/").split("/")
    if parts == ["**"]:
        return re.compile(r"^.*$")
    regex = ""
    for index, part in enumerate(parts):
        if part == "**":
            # Leading, it consumes "segment/" pairs; elsewhere "/segment" ones.
            regex += "(?:[^/]+/)*" if index == 0 else "(?:/[^/]+)*"
            continue
        if index and not (index == 1 and parts[0] == "**"):
            regex += "/"
        regex += "".join("[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
                         for c in part)
    return re.compile(f"^{regex}$")


def _inside(path: str, directory: str) -> bool:
    return path == directory or path.startswith(directory + "/")


def attribute(tree: list[str], contents: dict[str, str | None], changed: list[str],
              where: str = "") -> Attribution:
    """Who a change belongs to in a monorepo, per **Release units**.

    tree is every path in the repository as of the change, contents the
    needed_files() among them (None where absent), and changed the paths the
    change makes. where says, in an error, which state the files were read in.
    """
    marker = ID_FILE.as_posix()
    units = unit_dirs(tree)
    for outer in units:
        for inner in units:
            if inner != outer and _inside(inner, outer):
                raise SystemExit(f"{inner}/{marker} is inside the release unit {outer}/: "
                                 "a unit holds one id, and units do not nest.")
    ids = {unit: parse_id(contents.get(f"{unit}/{marker}"), f"{unit}/{marker}{where}")
           for unit in units}
    monorepo_id = parse_id(contents.get(marker), f"{marker}{where}")

    globs = _workspace_globs(contents.get(WORKSPACE_FILE) or "")
    include = [_glob(g) for g in globs if not g.startswith("!")]
    exclude = [_glob(g[1:]) for g in globs if g.startswith("!")]
    dirs_by_name: dict[str, str] = {}
    deps: dict[str, set[str]] = {}
    for manifest in (path for path in tree if path.endswith("/package.json")):
        directory = manifest[:-len("/package.json")]
        if (not any(p.match(directory) for p in include)
                or any(p.match(directory) for p in exclude)):
            continue
        try:
            data = json.loads(contents.get(manifest) or "")
            name = data["name"]
        except (ValueError, KeyError, TypeError):
            raise SystemExit(f"{manifest}{where} is not a package.json with a name, so "
                             "its dependencies cannot be followed.")
        dirs_by_name[name] = directory
        deps[directory] = {dep for field in DEPENDENCY_FIELDS
                           for dep, spec in (data.get(field) or {}).items()
                           if isinstance(spec, str) and spec.startswith("workspace:")}

    root_change = any("/" not in path and (path in ROOT_BUILD_FILES
                                           or ROOT_TSCONFIG.match(path))
                      for path in changed)
    # The lockfile belongs to the units whose package.json the change edits,
    # which their closures already reach, or to every unit when it edits none.
    lockfile_alone = LOCKFILE in changed and not any(
        PurePosixPath(path).name == "package.json" for path in changed)
    affected: list[str] = []
    for unit in units:
        # The unit's directory and every package its packages reach, transitively.
        reached: set[str] = set()
        queue = [d for d in deps if _inside(d, unit)]
        while queue:
            directory = queue.pop()
            if directory not in reached:
                reached.add(directory)
                queue += [dirs_by_name[name] for name in deps[directory]
                          if name in dirs_by_name]
        reached.add(unit)
        if (root_change or lockfile_alone
                or any(_inside(path, d) for path in changed for d in reached)):
            affected.append(ids[unit])
    affected.sort()
    shared = sorted(name for name, directory in dirs_by_name.items()
                    if not any(_inside(directory, unit) for unit in units)
                    and any(_inside(path, directory) for path in changed))
    if len(affected) == 1:
        return Attribution(affected[0], (), (), True)
    return Attribution(monorepo_id, tuple(affected), tuple(shared), True)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def _staged_contents(root: Path, paths: list[str]) -> dict[str, str | None]:
    """Each path's staged content, or None where the index has none."""
    request = "".join(f":{path}\n" for path in paths).encode("utf-8")
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


def attribution(root: Path) -> Attribution:
    """Who the staged change belongs to: the root's id in a repository holding one
    service, and per **Release units** in a monorepo."""
    try:
        at_top = not _git(root, "rev-parse", "--show-prefix").strip()
        tree = [path for path in _git(root, "ls-files", "-z").split("\0") if path]
    except (OSError, subprocess.CalledProcessError):
        at_top, tree = False, []
    if not at_top or not unit_dirs(tree):
        return Attribution(software_id(root))
    changed = [path for path in _git(root, "diff", "--cached", "--name-only",
                                     "--no-renames", "-z").split("\0") if path]
    return attribute(tree, _staged_contents(root, needed_files(tree)), changed,
                     " in the index")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mint a change identifier.")
    parser.add_argument("--root", type=Path,
                        help="repository root (default: the enclosing git repository)")
    args = parser.parse_args(argv)
    found = attribution(args.root or repo_root(Path.cwd()))
    print(mint(found.software_id))
    for trailer in found.trailers():
        print(trailer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

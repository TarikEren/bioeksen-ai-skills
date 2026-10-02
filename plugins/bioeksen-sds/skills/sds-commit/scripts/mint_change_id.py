#!/usr/bin/env python3
"""Mint a change identifier for a commit's Change-Id trailer.

    python mint_change_id.py [--root DIR]

Prints {software-id}-{UTC timestamp}-{random}, e.g.
bioeksen-sds-20260917T101500Z-4c1e, in the format
references/release-notes.md defines. Run it from anywhere inside the
repository the commit belongs to.

The software id is read from .bioeksen/software-id at the repository root,
the one place sds-logging/references/log-record.md says it is stored. It is
never written into this script and never guessed: this script ships with the
plugin and runs for every project, so a built-in id would label every other
project's commits as one project's. When the file is missing, empty or
malformed the script exits non-zero and says so — ask for the id, write it
there, and run again.

Minting is local by rule and makes no network call. The four random hex
characters keep two identifiers minted in the same second distinct.
"""
from __future__ import annotations

import argparse
import re
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# SoftwareId in sds-api-design/references/openapi.yaml.
SOFTWARE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOFTWARE_ID_MAX = 63
# {software-id}-{YYYYMMDDTHHMMSSZ}-{four or more random characters}
CHANGE_ID = re.compile(
    r"^(?P<software_id>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<timestamp>\d{8}T\d{6}Z)-(?P<random>[a-z0-9]{4,})$")
ID_FILE = Path(".bioeksen") / "software-id"


def repo_root(start: Path) -> Path:
    """The enclosing git repository's root, or start when there is none."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start,
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return start
    return Path(out.stdout.strip())


def software_id(root: Path) -> str:
    """The id stored in .bioeksen/software-id, or exit explaining what is wrong."""
    path = root / ID_FILE
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise SystemExit(f"{path} does not exist. The software id is supplied by the "
                         "project and never guessed: ask for it, then write it there.")
    if not value:
        raise SystemExit(f"{path} is empty. The software id is supplied by the project "
                         "and never guessed: ask for it, then write it there.")
    if not SOFTWARE_ID.match(value) or len(value) > SOFTWARE_ID_MAX:
        raise SystemExit(f"{path} holds {value!r}, which is not a software id: lowercase "
                         f"letters and digits in hyphen-separated words, at most "
                         f"{SOFTWARE_ID_MAX} characters.")
    return value


def mint(software: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"{software}-{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(2)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mint a change identifier.")
    parser.add_argument("--root", type=Path,
                        help="repository root (default: the enclosing git repository)")
    args = parser.parse_args(argv)
    print(mint(software_id(args.root or repo_root(Path.cwd()))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

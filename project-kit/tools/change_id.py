#!/usr/bin/env python3
"""Mint a change identifier, per sds-commit/references/release-notes.md.

    python change_id.py [--root DIR]

The implementation is the sds-commit skill's own script,
plugins/bioeksen-sds/skills/sds-commit/scripts/mint_change_id.py, which an
installed plugin carries so an assistant can run it. This file re-exports it
for the kit's other tools, so the kit and the skill mint identifiers one way.
The kit always runs from a full checkout of this repository, where that
script is present.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "bioeksen-sds"
                       / "skills" / "sds-commit" / "scripts"))

from mint_change_id import (  # noqa: E402 - the path above has to be set first
    CHANGE_ID, ID_FILE, MINT_ZONE, SOFTWARE_ID, SOFTWARE_ID_MAX, main, mint, repo_root,
    software_id)

__all__ = ["CHANGE_ID", "ID_FILE", "MINT_ZONE", "SOFTWARE_ID", "SOFTWARE_ID_MAX", "main",
           "mint", "repo_root", "software_id"]

if __name__ == "__main__":
    raise SystemExit(main())

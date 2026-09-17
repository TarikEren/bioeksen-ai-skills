#!/usr/bin/env python3
"""Enforce the cross-file invariants recorded in CLAUDE.md.

These documents restate each other deliberately, so nothing but a check like
this notices when two copies drift apart. Run from the repository root:

    python scripts/check_invariants.py

Exits non-zero on the first failing invariant, listing every problem found.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugins" / "bioeksen-sds" / "skills"
CODE_PREFIXES = SKILLS / "sds-logging" / "references" / "code-prefixes.md"
ERROR_CODES = SKILLS / "sds-logging" / "references" / "error-codes.md"
AUTH_SKILL = SKILLS / "sds-auth" / "SKILL.md"
AGGREGATOR = SKILLS / "sds-logging" / "references" / "aggregator-api.md"
SERVICE_CALLS = SKILLS / "sds-api-design" / "references" / "service-calls.md"
OPENAPI = SKILLS / "sds-api-design" / "references" / "openapi.yaml"
AGGREGATOR_YAML = SKILLS / "sds-logging" / "references" / "aggregator-api.yaml"
SCHEMAS = (OPENAPI, AGGREGATOR_YAML)

# The only unversioned paths in the estate; everything else carries /api/v{major}/.
STANDARD_PATHS = {"/api/health", "/api/health/live", "/api/health/ready",
                  "/api/admin/logs"}

# `| `AUTH-4100` | 401 | Credential missing |` — the per-prefix tables.
PREFIX_ROW = re.compile(r"^\|\s*`([A-Z][A-Z0-9]*-\d{4})`\s*\|\s*(\d{3})\s*\|", re.M)
# `| 1 | Caller is over a rate limit ... | `RATE-4400` |` — selection procedure.
SELECT_ROW = re.compile(r"^\|\s*\d+\s*\|\s*.+?\s*\|\s*`([A-Z0-9-]+)`\s*\|\s*$", re.M)
# Same, with a trailing HTTP column — sds-auth's validation order.
AUTH_ROW = re.compile(r"^\|\s*\d+\s*\|\s*.+?\s*\|\s*`([A-Z0-9-]+)`\s*\|\s*\d{3}\s*\|\s*$", re.M)
# `| `4100-4149` | 401 | Missing or invalid credential |` — the range table.
RANGE_ROW = re.compile(r"^\|\s*`(\d{4})-(\d{4})`\s*\|\s*(\d{3})\s*\|", re.M)
# '## `POST HOST/api/v1/logs`' — an aggregator endpoint heading.
AGG_PATH = re.compile(r"^##\s+`(?:GET|POST|PUT|PATCH|DELETE)\s+HOST(/\S*?)`\s*$", re.M)
# `| `5500-5999` | 503 | Yes |` — the retry classification.
RETRY_ROW = re.compile(r"^\|\s*`(\d{4})-(\d{4})`\s*\|\s*(\d{3})\s*\|\s*(Yes|No)\s*\|", re.M)

failures: list[str] = []


def fail(invariant: str, detail: str) -> None:
    failures.append(f"{invariant}: {detail}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_refs(node):
    """Every $ref value anywhere in a parsed document."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from iter_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_refs(value)


def resolve_pointer(doc, pointer: str):
    """Walk a JSON pointer, returning None when any step is missing."""
    node = doc
    for part in pointer.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return None
    return node


def main() -> int:
    cp, au = read(CODE_PREFIXES), read(AUTH_SKILL)
    spec = yaml.safe_load(read(OPENAPI))

    table = {m.group(1): int(m.group(2)) for m in PREFIX_ROW.finditer(cp)}
    selection = SELECT_ROW.findall(cp)
    enum = spec["components"]["schemas"]["ErrorCode"]["enum"]

    # 1. The same codes in the prefix tables, the selection procedure and the enum.
    for name, got, ref in (("selection procedure", set(selection), set(table)),
                           ("ErrorCode enum", set(enum), set(table))):
        if got - ref:
            fail("invariant 1", f"in {name} but not the prefix tables: {sorted(got - ref)}")
        if ref - got:
            fail("invariant 1", f"in the prefix tables but not {name}: {sorted(ref - got)}")
    if len(enum) != len(set(enum)):
        fail("invariant 1", "ErrorCode enum contains duplicates")

    # 2. sds-auth restates steps 1-9 of the selection procedure, codes and order.
    auth = AUTH_ROW.findall(au)
    if auth != selection[: len(auth)]:
        fail("invariant 2", f"sds-auth order {auth} != selection procedure {selection[:len(auth)]}")

    # 3. Every code's HTTP status matches the range table in error-codes.md.
    ranges = [(int(a), int(b), int(h)) for a, b, h in RANGE_ROW.findall(read(ERROR_CODES))]
    if not ranges:
        fail("invariant 3", "no range table found in error-codes.md")
    for code, http in sorted(table.items()):
        number = int(code.split("-")[1])
        expected = next((h for lo, hi, h in ranges if lo <= number <= hi), None)
        if expected is None:
            fail("invariant 3", f"{code} falls in no documented range")
        elif expected != http:
            fail("invariant 3", f"{code} is documented as {http}, range table says {expected}")

    # 4. The four standard endpoints are unversioned; every other path is not.
    paths = set(spec["paths"])
    if paths != STANDARD_PATHS:
        for extra in sorted(paths - STANDARD_PATHS):
            fail("invariant 4", f"openapi.yaml defines {extra}, which is not one of "
                                "the four unversioned standard endpoints")
        for missing in sorted(STANDARD_PATHS - paths):
            fail("invariant 4", f"openapi.yaml no longer defines {missing}")
    agg = yaml.safe_load(read(AGGREGATOR_YAML))
    # `:recordId` in the prose is `{recordId}` in the schema; same endpoint.
    documented_paths = {re.sub(r":(\w+)", r"{\1}", p)
                        for p in AGG_PATH.findall(read(AGGREGATOR))}
    if not documented_paths:
        fail("invariant 4", "no endpoint headings found in aggregator-api.md")
    for path in documented_paths | set(agg["paths"]):
        if not re.match(r"^/api/v\d+/", path):
            fail("invariant 4", f"aggregator endpoint {path} is app-specific and "
                                "must be served under /api/v{major}/")
    if documented_paths != set(agg["paths"]):
        fail("invariant 4", f"aggregator-api.md documents {sorted(documented_paths)}, "
                            f"aggregator-api.yaml defines {sorted(agg['paths'])}")

    # 5. Retryable is exactly the 503 range, non-retryable exactly the 500 range.
    retry = {(int(a), int(b), int(h)): yes == "Yes"
             for a, b, h, yes in RETRY_ROW.findall(read(SERVICE_CALLS))}
    documented = {(lo, hi, h) for lo, hi, h in ranges if h in (500, 503)}
    if set(retry) != documented:
        fail("invariant 5", f"service-calls.md classifies {sorted(retry)}, "
                            f"error-codes.md documents {sorted(documented)}")
    for (lo, hi, http), retryable in sorted(retry.items()):
        if retryable != (http == 503):
            verb = "retryable" if retryable else "not retryable"
            fail("invariant 5", f"service-calls.md calls {lo}-{hi} ({http}) {verb}")

    # 6. Every $ref in every schema file resolves, across files as well as within.
    loaded = {OPENAPI: spec, AGGREGATOR_YAML: agg}
    refs = 0
    for source in SCHEMAS:
        for ref in iter_refs(loaded[source]):
            refs += 1
            filepart, _, pointer = ref.partition("#")
            target = (source.parent / filepart).resolve() if filepart else source
            if target not in loaded:
                if not target.is_file():
                    fail("invariant 6", f"{source.name}: $ref {ref} names no file")
                    continue
                loaded[target] = yaml.safe_load(read(target))
            if resolve_pointer(loaded[target], pointer) is None:
                fail("invariant 6", f"{source.name}: $ref {ref} resolves to nothing")

    # The manifests and the schema must at least parse.
    for manifest in (ROOT / ".claude-plugin" / "marketplace.json",
                     ROOT / "plugins" / "bioeksen-sds" / ".claude-plugin" / "plugin.json"):
        try:
            json.loads(read(manifest))
        except (OSError, json.JSONDecodeError) as exc:
            fail("manifests", f"{manifest.relative_to(ROOT)}: {exc}")

    # Every skill needs the frontmatter that decides when it loads.
    for skill in sorted(SKILLS.glob("*/SKILL.md")):
        head = read(skill)[:800]
        for key in ("name:", "description:"):
            if not re.search(rf"^{key}", head, re.M):
                fail("frontmatter", f"{skill.relative_to(ROOT)} has no {key.rstrip(':')}")

    if failures:
        print(f"FAILED ({len(failures)} problem(s)):\n", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print(f"OK - {len(table)} error codes consistent across "
          f"code-prefixes.md, its selection procedure and the ErrorCode enum")
    print(f"OK - sds-auth restates steps 1-{len(auth)} in the same order")
    print("OK - every code's HTTP status matches the range table")
    print(f"OK - the {len(STANDARD_PATHS)} standard endpoints are unversioned and "
          f"the {len(documented_paths)} aggregator paths are not")
    print("OK - retryable codes are exactly the 503 range, per error-codes.md")
    print(f"OK - all {refs} $refs across {len(SCHEMAS)} schema files resolve")
    print("OK - manifests parse, every skill declares name and description")
    return 0


if __name__ == "__main__":
    sys.exit(main())

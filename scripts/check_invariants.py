#!/usr/bin/env python3
"""Enforce the cross-file invariants recorded in CLAUDE.md.

These documents restate each other deliberately, so nothing but a check like
this notices when two copies drift apart. Run from the repository root:

    python scripts/check_invariants.py

Every invariant is checked before exiting, so one run lists every problem found
rather than stopping at the first.
"""
from __future__ import annotations

import ast
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
README = ROOT / "README.md"
CODE_PREFIXES = SKILLS / "sds-logging" / "references" / "code-prefixes.md"
ERROR_CODES = SKILLS / "sds-logging" / "references" / "error-codes.md"
AUTH_SKILL = SKILLS / "sds-auth" / "SKILL.md"
SERVICE_CALLS = SKILLS / "sds-api-design" / "references" / "service-calls.md"
OPENAPI = SKILLS / "sds-api-design" / "references" / "openapi.yaml"
SCHEMAS = (OPENAPI,)
LOG_RECORD = SKILLS / "sds-logging" / "references" / "log-record.md"
LOGGING_SKILL = SKILLS / "sds-logging" / "SKILL.md"
STANDARD_ENDPOINTS = SKILLS / "sds-api-design" / "references" / "standard-api-endpoints.md"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_MANIFEST = ROOT / "plugins" / "bioeksen-sds" / ".claude-plugin" / "plugin.json"
TESTING = SKILLS / "sds-testing"
TESTING_SKILL = TESTING / "SKILL.md"
CONTRACT_TESTS = TESTING / "references" / "contract-tests.md"
COMMIT_MSG = ROOT / "project-kit" / "tools" / "commit_msg.py"
TEMPLATE = ROOT / "project-kit" / "template"
TEMPLATE_SETTINGS = TEMPLATE / ".claude" / "settings.json"
# The CI file a project copies for its git provider, per sds-ci and sds-project,
# and where each keeps the kit's repository and tag.
CI_FILES = {
    "github": (ROOT / "project-kit" / "ci" / "github" / ".github" / "workflows" / "bioeksen.yml", "env"),
    "gitlab": (ROOT / "project-kit" / "ci" / "gitlab" / ".gitlab-ci.yml", "variables"),
}
# A CI definition, of any provider, that the template must not carry.
CI_DEFINITIONS = (".github", ".gitlab", ".gitlab-ci.yml")
# Where the CI image carries a bioeksen-sds release's project kit, per sds-ci.

# sds-auth restates exactly steps 1-10 of the selection procedure.
AUTH_STEPS = 10

# The only unversioned paths in the estate; everything else carries /api/v{major}/.
STANDARD_PATHS = {"/api/health", "/api/health/live", "/api/health/ready",
                  "/api/admin/logs", "/api/client-errors"}

# `| `AUTH-4100` | 401 | Credential missing |` — the per-prefix tables.
PREFIX_ROW = re.compile(r"^\|\s*`([A-Z][A-Z0-9]*-\d{4})`\s*\|\s*(\d{3})\s*\|", re.M)
# `| 1 | Caller is over a rate limit ... | `RATE-4400` |` — selection procedure.
SELECT_ROW = re.compile(r"^\|\s*\d+\s*\|\s*.+?\s*\|\s*`([A-Z0-9-]+)`\s*\|\s*$", re.M)
# Same, with a trailing HTTP column — sds-auth's validation order.
AUTH_ROW = re.compile(r"^\|\s*\d+\s*\|\s*.+?\s*\|\s*`([A-Z0-9-]+)`\s*\|\s*\d{3}\s*\|\s*$", re.M)
# `| `4100-4149` | 401 | Missing or invalid credential |` — the range table.
RANGE_ROW = re.compile(r"^\|\s*`(\d{4})-(\d{4})`\s*\|\s*(\d{3})\s*\|", re.M)
# `| `5500-5999` | 503 | Yes |` — the retry classification.
RETRY_ROW = re.compile(r"^\|\s*`(\d{4})-(\d{4})`\s*\|\s*(\d{3})\s*\|\s*(Yes|No)\s*\|", re.M)
# `AUTH-4100` anywhere in running text: an error code, by its format alone.
CODE_TOKEN = re.compile(r"\b([A-Z][A-Z0-9]{1,7}-[45][0-9]{3})\b")
# 400 `VAL-4005` — a status and the code it is expected with.
STATUS_CODE = re.compile(r"\b([1-5][0-9]{2})\s+`([A-Z][A-Z0-9]{1,7}-[45][0-9]{3})`")
# A fenced code block, stripped before looking for references: paths inside
# examples name files in the project using a skill, not files in this plugin.
FENCE = re.compile(r"^```.*?^```", re.M | re.S)
# `sds-logging/references/log-record.md` — a file named in running text. Under
# `${CLAUDE_SKILL_DIR}/` it names a file in the naming skill's own directory,
# such as a script an assistant is told to run.
TICKED_PATH = re.compile(
    r"`(\$\{CLAUDE_SKILL_DIR\}/)?((?:[\w.-]+/)*[\w-]+\.(?:md|yaml|py))`")
# [text](target) — a markdown link.
LINK = re.compile(r"\]\(([^)\s]+)\)")
# The same paths as they appear in plain YAML description text.
PLAIN_PATH = re.compile(r"(?<![\w./-])((?:[\w-]+/)*[\w-]+\.(?:md|yaml))\b")
# "... whose roles hold operator." — the role a security scheme requires.
SCHEME_ROLE = re.compile(r"roles hold ([\w-]+(?:\.[\w-]+)*)")
HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
# `---\nname: ...\n---` — the frontmatter block that decides when a skill loads.
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def cells(row: str) -> list[str]:
    """The cells of a markdown table row, split on unescaped pipes only."""
    return [c.strip() for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]


def ticked(text: str) -> list[str]:
    """Every backticked token in a piece of text, in order."""
    return re.findall(r"`([^`]+)`", text)


def section(text: str, heading: str) -> str:
    """The body under a markdown heading, up to the next heading of any level."""
    match = re.search(rf"^#+\s+{re.escape(heading)}\s*$(.*?)(?=^#|\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def table_rows(body: str) -> list[dict[str, str]]:
    """The data rows of the first markdown table in body, keyed by header."""
    rows = [cells(line) for line in body.splitlines() if line.startswith("|")]
    if len(rows) < 2:
        return []
    header = rows[0]
    return [dict(zip(header, row)) for row in rows[2:]]

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

    # 2. sds-auth restates steps 1-10 of the selection procedure, codes and order.
    # The counts are asserted first: a table the pattern stops matching would
    # otherwise compare an empty list with an empty slice and pass.
    auth = AUTH_ROW.findall(au)
    if not selection:
        fail("invariant 2", "no selection procedure rows found in code-prefixes.md")
    if len(auth) != AUTH_STEPS:
        fail("invariant 2", f"sds-auth validation order has {len(auth)} matching rows, "
                            f"expected {AUTH_STEPS}")
    elif auth != selection[:AUTH_STEPS]:
        fail("invariant 2", f"sds-auth order {auth} != selection procedure {selection[:AUTH_STEPS]}")
    # The database failures table restates steps by number: each row's code is
    # the code of the step it names, so a renumbered procedure fails it loudly.
    db_rows = table_rows(section(cp, "Database failures"))
    if not db_rows:
        fail("invariant 2", "no Database failures table found in code-prefixes.md")
    for row in db_rows:
        step, codes = row.get("Step", ""), ticked(row.get("Code", ""))
        named = selection[int(step) - 1] if step.isdigit() and 0 < int(step) <= len(selection)             else None
        if codes[:1] != [named] or named is None:
            fail("invariant 2", f"database failure {row.get('Database condition')!r} pairs "
                                f"step {step} with {codes}, but that step is {named}")

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

    # 4. The schema defines exactly the five standard endpoints, unversioned.
    paths = set(spec["paths"])
    if paths != STANDARD_PATHS:
        for extra in sorted(paths - STANDARD_PATHS):
            fail("invariant 4", f"openapi.yaml defines {extra}, which is not one of "
                                "the five unversioned standard endpoints")
        for missing in sorted(STANDARD_PATHS - paths):
            fail("invariant 4", f"openapi.yaml no longer defines {missing}")

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
    loaded = {OPENAPI: spec}
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

    # The manifests must parse, and 7: the marketplace must mirror each plugin's
    # own version. The marketplace's own version tracks which plugins it offers,
    # not what is inside them, so the two move independently and only the
    # mirrored entry has to agree.
    manifests = {}
    for manifest in (MARKETPLACE, PLUGIN_MANIFEST):
        try:
            manifests[manifest] = json.loads(read(manifest))
        except (OSError, json.JSONDecodeError) as exc:
            fail("manifests", f"{manifest.relative_to(ROOT)}: {exc}")
    if len(manifests) == 2:
        listed = {p["name"]: p.get("version") for p in manifests[MARKETPLACE]["plugins"]}
        own = manifests[PLUGIN_MANIFEST]
        if own["name"] not in listed:
            fail("invariant 7", f"marketplace.json lists no plugin named {own['name']}")
        elif listed[own["name"]] != own.get("version"):
            fail("invariant 7", f"marketplace.json says {own['name']} is "
                                f"{listed[own['name']]}, plugin.json says {own.get('version')}")

        # 10. The project template pins the release it ships in, and so does
        # each provider's CI file, so the skills an assistant loads and the
        # checks CI runs come from one version. CI checks the kit out of the
        # repository the settings name. The template carries no CI file: a
        # project copies its own provider's.
        marketplace = manifests[MARKETPLACE]["name"]
        pinned = f"v{own.get('version')}"
        settings = json.loads(read(TEMPLATE_SETTINGS))
        source = settings.get("extraKnownMarketplaces", {}).get(marketplace, {}).get("source", {})
        if source.get("ref") != pinned:
            fail("invariant 10", f"template settings.json pins {source.get('ref')!r}, "
                                 f"the plugin is {pinned}")
        for provider, (ci_file, key) in CI_FILES.items():
            where = ci_file.relative_to(ROOT)
            if not ci_file.is_file():
                fail("invariant 10", f"{provider} has no CI file at {where}")
                continue
            values = (yaml.safe_load(read(ci_file)) or {}).get(key) or {}
            if values.get("KIT_REF") != pinned:
                fail("invariant 10", f"{where} checks the kit out at "
                                     f"{values.get('KIT_REF')!r}, the plugin is {pinned}")
            if values.get("KIT_REPOSITORY") != source.get("repo"):
                fail("invariant 10", f"{where} checks the kit out of "
                                     f"{values.get('KIT_REPOSITORY')!r}, the settings name "
                                     f"{source.get('repo')!r}")
        for name in CI_DEFINITIONS:
            if (TEMPLATE / name).exists():
                fail("invariant 10", f"the template carries {name}: a project copies the CI "
                                     "file of its own git provider")
        if settings.get("enabledPlugins", {}).get(f"{own['name']}@{marketplace}") is not True:
            fail("invariant 10", f"template settings.json does not enable "
                                 f"{own['name']}@{marketplace}")

    # 8. The severity and type sets are closed, and restated in four places.
    # A rename has to land in every one of them, so each is compared to the
    # schema, which is the only copy a validator ever sees.
    record, logging_skill = read(LOG_RECORD), read(LOGGING_SKILL)
    standard = read(STANDARD_ENDPOINTS)
    query = {cells(row)[0].strip("`"): cells(row) for row in standard.splitlines()
             if row.startswith("| `")}
    for name, schema, heading, skill_heading in (
            ("severity", "Severity", "Severity", "Choosing a severity"),
            ("type", "LogType", "Type", "Choosing a type")):
        expected = spec["components"]["schemas"][schema]["enum"]
        body = section(record, heading).strip()
        copies = {
            "log-record.md": ticked(body.splitlines()[0]) if body else [],
            "sds-logging/SKILL.md": [ticked(cells(row)[0])[0]
                                     for row in section(logging_skill, skill_heading).splitlines()
                                     if row.startswith("| `")],
            "standard-api-endpoints.md": ticked(query[name][3]) if name in query else [],
        }
        for where, got in copies.items():
            if got != expected:
                fail("invariant 8", f"{where} lists {name} values {got}, "
                                    f"openapi.yaml {schema} has {expected}")
    # The outbox table says what happens to a record at each severity: when it
    # may be removed, and whether it may be dropped. It names every severity once, DEBUG included, so a new severity
    # cannot arrive without a rule for whether the outbox may lose it.
    outbox = [cells(row) for row in section(record, "The outbox").splitlines()
              if row.startswith("|")]
    held = [value for row in outbox[2:] for value in ticked(row[0])]
    severities = spec["components"]["schemas"]["Severity"]["enum"]
    if sorted(held) != sorted(severities) or len(held) != len(set(held)):
        fail("invariant 8", f"log-record.md's outbox table covers severity values {held}; "
                            f"it must name each of {severities} once")
    # The retention table groups the same values: every type once down its
    # first column, and every severity, DEBUG included, once across its header.
    retention = [cells(row) for row in section(record, "Retention").splitlines()
                 if row.startswith("|")]
    kept = {
        "type": ([value for row in retention[2:] for value in ticked(row[0])],
                 spec["components"]["schemas"]["LogType"]["enum"]),
        "severity": ([value for cell in (retention[0][1:] if retention else [])
                      for value in ticked(cell)], severities),
    }
    for name, (got, expected) in kept.items():
        if sorted(got) != sorted(expected) or len(got) != len(set(got)):
            fail("invariant 8", f"log-record.md's Retention table covers {name} "
                                f"values {got}; it must name each of {expected} once")

    # 9. Every file one skill document names resolves once the plugin is
    # installed: from the skills root, beside the naming file, or from the
    # naming skill's own directory. Paths starting with `/` or carrying a `{`
    # name files in the project using a skill, and are skipped.
    references = 0
    for doc in sorted(list(SKILLS.rglob("*.md")) + list(SKILLS.rglob("*.yaml"))):
        text = FENCE.sub("", read(doc))
        skill_dir = SKILLS / doc.relative_to(SKILLS).parts[0]
        if doc.suffix == ".md":
            targets = [(path, bool(in_skill)) for in_skill, path in TICKED_PATH.findall(text)]
            targets += [(t.split("#")[0], False) for t in LINK.findall(text)
                        if not t.startswith(("http", "#"))]
        else:
            targets = [(t, False) for t in PLAIN_PATH.findall(text)]
        for target, in_skill in targets:
            if target.startswith("/") or "{" in target:
                continue
            references += 1
            where = doc.relative_to(ROOT)
            bases = (skill_dir,) if in_skill else (SKILLS, doc.parent, skill_dir)
            if target.startswith("plugins/"):
                fail("invariant 9", f"{where} names {target} by a repository path, "
                                    "which does not exist once the plugin is installed")
            elif not any((base / target).is_file() for base in bases):
                fail("invariant 9", f"{where} names {target}, which resolves nowhere")

    # 11. The contract test catalogue can be trusted as a test plan: it names
    # no code the registry lacks, covers every step of the validation order
    # sds-auth restates, and pairs each code with the status it carries.
    catalogue = read(CONTRACT_TESTS) if CONTRACT_TESTS.is_file() else ""
    if not catalogue:
        fail("invariant 11", "sds-testing/references/contract-tests.md does not exist")
    for doc in sorted(TESTING.rglob("*.md")) if TESTING.is_dir() else []:
        for code in sorted(set(CODE_TOKEN.findall(read(doc))) - set(table)):
            fail("invariant 11", f"{doc.relative_to(ROOT)} names {code}, which is not a "
                                 "registered error code")
    groups = re.findall(r"^##\s+(.+?)\s*$", catalogue, re.M)
    expected = []
    for group in groups:
        for row in table_rows(section(catalogue, group)):
            then = row.get("Then", "")
            for status, code in STATUS_CODE.findall(then):
                if code in table and int(status) != table[code]:
                    fail("invariant 11", f"contract-tests.md {group}: {row.get('Case')!r} "
                                         f"expects {status} with {code}, which is "
                                         f"{table[code]}")
            if group == "Auth":
                expected += CODE_TOKEN.findall(then)
    for code in auth:
        if code not in expected:
            fail("invariant 11", f"contract-tests.md has no Auth case expecting {code}, "
                                 "a step of the validation order in sds-auth")
    # The exemptions are listed once, in sds-testing's table, and the tool that
    # validates the Test-Exempt trailer holds the same tuple.
    listed = [ticked(cells(row)[0])[0] for row in
              section(read(TESTING_SKILL), "Exemptions").splitlines()
              if row.startswith("| `")] if TESTING_SKILL.is_file() else []
    assignment = re.search(r"^TEST_EXEMPTIONS\s*=\s*(\(.*?\))\s*$", read(COMMIT_MSG),
                           re.M | re.S)
    coded = list(ast.literal_eval(assignment.group(1))) if assignment else None
    if coded is None:
        fail("invariant 11", "project-kit/tools/commit_msg.py defines no TEST_EXEMPTIONS")
    elif listed != coded:
        fail("invariant 11", f"sds-testing lists the exemptions {listed}, "
                             f"commit_msg.py accepts {coded}")

    # 12. README's Skills table is the one list of the skills a reader sees:
    # it names every skill directory, and nothing else.
    skill_dirs = {s.parent.name for s in SKILLS.glob("*/SKILL.md")}
    readme_skills = {(ticked(row.get("Skill", "")) or [""])[0]
                     for row in table_rows(section(read(README), "Skills"))}
    for missing in sorted(skill_dirs - readme_skills):
        fail("invariant 12", f"README.md's Skills table has no row for {missing}")
    for stray in sorted(readme_skills - skill_dirs):
        fail("invariant 12", f"README.md's Skills table names {stray!r}, which is not a skill")

    # 13. sds-auth's Requirements by endpoint table restates every endpoint
    # the schemas define, with the principal each requires. A reader protects
    # an endpoint from that table, so an endpoint missing from it, or listed
    # with another principal, is one protected differently from its schema.
    # A security scheme's principal is the role its description says the
    # credential's roles hold; an empty security list is "None".
    schemes = {}
    for source, doc in ((OPENAPI, spec),):
        for name, scheme in doc["components"]["securitySchemes"].items():
            held = SCHEME_ROLE.search(" ".join(scheme.get("description", "").split()))
            if not held:
                fail("invariant 13", f"{source.name}: security scheme {name} names no role "
                                     "its credential's roles hold")
            schemes[(source, name)] = held.group(1) if held else name
    defined = {}
    for source, doc in ((OPENAPI, spec),):
        for path, item in doc["paths"].items():
            for method, operation in item.items():
                if method in HTTP_METHODS:
                    defined[f"{method.upper()} {path}"] = {
                        schemes[(source, scheme)] for requirement in operation.get("security", [])
                        for scheme in requirement}
    listed = {}
    for row in table_rows(section(au, "Requirements by endpoint")):
        principal = row.get("Principal", "")
        roles = set() if principal == "None" else (
            set(ticked(principal)) | ({"operator"} if "Operator" in principal else set()))
        for endpoint in ticked(row.get("Endpoint", "")):
            endpoint = re.sub(r":(\w+)", r"{\1}", endpoint.replace("HOST/", "/"))
            listed[endpoint] = roles
    if not listed:
        fail("invariant 13", "no Requirements by endpoint table found in sds-auth/SKILL.md")
    for endpoint in sorted(defined.keys() - listed.keys()):
        fail("invariant 13", f"sds-auth's Requirements by endpoint table has no row for "
                             f"{endpoint}, which a schema defines")
    for endpoint in sorted(listed.keys() - defined.keys()):
        fail("invariant 13", f"sds-auth's Requirements by endpoint table lists {endpoint}, "
                             "which no schema defines")
    for endpoint in sorted(defined.keys() & listed.keys()):
        if defined[endpoint] != listed[endpoint]:
            fail("invariant 13", f"sds-auth lets {sorted(listed[endpoint]) or 'anyone'} call "
                                 f"{endpoint}; its schema lets "
                                 f"{sorted(defined[endpoint]) or 'anyone'}")

    # Every skill needs the frontmatter that decides when it loads, and its
    # name must be its directory's.
    for skill in sorted(SKILLS.glob("*/SKILL.md")):
        where = skill.relative_to(ROOT)
        block = FRONTMATTER.match(read(skill))
        if not block:
            fail("frontmatter", f"{where} does not open with a --- frontmatter block")
            continue
        fields = dict(re.findall(r"^(\w+):\s*(.*?)\s*$", block.group(1), re.M))
        if fields.get("name") != skill.parent.name:
            fail("frontmatter", f"{where} is named {fields.get('name')!r}, "
                                f"its directory {skill.parent.name!r}")
        if not fields.get("description"):
            fail("frontmatter", f"{where} has no description")

    if failures:
        print(f"FAILED ({len(failures)} problem(s)):\n", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print(f"OK - {len(table)} error codes consistent across "
          f"code-prefixes.md, its selection procedure and the ErrorCode enum")
    print(f"OK - sds-auth restates steps 1-{len(auth)} in the same order, and the "
          f"{len(db_rows)} database failures name each step's own code")
    print("OK - every code's HTTP status matches the range table")
    print(f"OK - the schema defines exactly the {len(STANDARD_PATHS)} standard endpoints, "
          "unversioned")
    print("OK - retryable codes are exactly the 503 range, per error-codes.md")
    print(f"OK - all {refs} $refs in the schema resolve")
    print("OK - manifests parse and agree on the plugin version, and the project "
          "template pins it")
    print("OK - severity and type values agree across log-record.md, sds-logging, "
          "standard-api-endpoints.md and the schema, and the retention and outbox "
          "tables cover them")
    print(f"OK - all {references} file references in the skills resolve")
    print("OK - the contract tests name only registered codes, cover every validation "
          "step, and pair each code with its status; the exemptions are listed once")
    print(f"OK - README.md's Skills table lists exactly the {len(skill_dirs)} skills")
    print(f"OK - sds-auth lists the {len(defined)} endpoints the schemas define, each with "
          "the principal its schema requires")
    print("OK - every skill's frontmatter names its directory and has a description")
    return 0


if __name__ == "__main__":
    sys.exit(main())

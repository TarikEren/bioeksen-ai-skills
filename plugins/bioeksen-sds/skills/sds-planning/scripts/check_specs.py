#!/usr/bin/env python3
"""Check a specification set, and the tests' citations of it.

    python check_specs.py --specs docs/specs
    python check_specs.py --specs docs/specs --tests tests e2e [--through B2]

The format is sds-planning's: a README.md that is the entry point, and area
files that hold decision tables and build items with numbered acceptance
criteria (sds-planning/SKILL.md, and references/spec-format.md beside it).
This script checks what can be checked without reading the prose for its
meaning: every id is defined once and every reference to one resolves; every
decision row is complete; every item has its blocks and its criteria, and sits
in the file the README names; the open decisions are exactly the Pending
rows; and every item is in a stage of the build order. An item that is not the
first of its group, such as WID-41 beside WID-40, is a part of the group's main
item: it needs only its criteria, and it is built in the main item's stages
unless a stage lists it.

Given --tests, it also reads every file under those paths for criterion ids
such as WID-30.AC6. Each one cited must exist, and every criterion of the
items due by --through (the last stage, by default) must be cited at least
once. An item listed in several stages is due at the last of them. A citation
is not a pass: whether the cited tests pass is the runner's to say.

It needs only the standard library. It exits 0 when the set is consistent, 1
when it found a defect, and 2 when it could not run: the directory or its
README is missing or unreadable, a tests path does not exist, or --through
names no stage. A check not run is never a pass, per **Keeping the suite
honest** in sds-testing/SKILL.md.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

STATUSES = ("Decided", "Pending", "Default")
DECISION_COLUMNS = ["ID", "Decision", "Status", "Owner", "Ask", "Affects", "Trace"]
REQUIRED_BLOCKS = ("What", "Rules", "Acceptance")
NO_QUESTION = "—"
DECISION_ID = re.compile(r"^DEC-\d{3}$")
# A table row's cells; a pipe escaped as `\|` stays inside its cell.
CELL = re.compile(r"(?<!\\)\|")
SEPARATOR = re.compile(r"^\|?[\s:|-]+\|?$")
# A fenced block, blanked before reading: examples are not part of the set.
FENCE = re.compile(r"^```.*?^```", re.M | re.S)
# `WID-nn` — a form in the README's Identifiers table.
FORM = re.compile(r"`([A-Z][A-Z0-9]*)-n+`")
# `### WID-30 Lifecycle` — a build item's heading.
ITEM_HEADING = re.compile(r"^### ([A-Z][A-Z0-9]*-\d+) +\S", re.M)
HEADING = re.compile(r"^#{1,3} ", re.M)
BLOCK = re.compile(r"^\*\*([A-Z][a-z]+)\.\*\*", re.M)
CRITERION = re.compile(r"^- \*\*AC(\d+)\.\*\*", re.M)
# The end of a labelled paragraph: the next **Label.** or heading.
PARAGRAPH_END = re.compile(r"^(?:\*\*|#)", re.M)
# `- `QA`: Quality Assurance.` — an owner in the README's Owners list.
OWNER = re.compile(r"^\s*- `([^`]+)`", re.M)
# `questions.md 4`, or `questions.md 14, 36` — the question a decision asks.
ASK = re.compile(r"^[\w./-]+\.md \d+(?:, \d+)*$")
# `- `core.md`: DEC-001 to DEC-011; DEC-013.` — the decisions a file holds.
FILE_RANGES = re.compile(r"^\s*- `([\w.-]+\.md)`:\s*(.*)$")
STAGE = re.compile(r"^[*\s]*([\w.]+)")
SKIPPED_DIRS = {".git", "node_modules"}


class Decision(NamedTuple):
    file: str
    line: int
    status: str


class Item(NamedTuple):
    file: str
    line: int
    criteria: list[int]
    blocks: list[str]


class Listing(NamedTuple):
    stage: int
    line: int
    names_part: bool


def line_of(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def blank_fences(text: str) -> str:
    """The text with each fenced block emptied, keeping every line number."""
    return FENCE.sub(lambda match: "\n" * match.group(0).count("\n"), text)


def cells(row: str) -> list[str]:
    return [cell.strip() for cell in CELL.split(row.strip().strip("|"))]


def section(text: str, title: str) -> tuple[int, int] | None:
    """The span of a `## title` section's body."""
    match = re.search(rf"^## {re.escape(title)}\s*$", text, re.M)
    if not match:
        return None
    following = re.search(r"^## ", text[match.end():], re.M)
    return match.end(), match.end() + following.start() if following else len(text)


def labelled(text: str, label: str) -> tuple[int, str] | None:
    """The first line and the body of the paragraph a `**Label.**` opens."""
    match = re.search(rf"^\*\*{re.escape(label)}\.\*\*", text, re.M)
    if not match:
        return None
    rest = text[match.end():]
    end = PARAGRAPH_END.search(rest)
    return line_of(text, match.end()), rest[:end.start() if end else len(rest)]


def tables(text: str, span: tuple[int, int]):
    """Each table in a span: its header's line, its header, and each row's line
    and cells."""
    start, end = span
    found: list[tuple[int, list[str], list[tuple[int, list[str]]]]] = []
    current = None
    for offset, line in enumerate(text[start:end].split("\n")):
        number = line_of(text, start) + offset
        if not line.startswith("|"):
            current = None
        elif current is None:
            current = (number, cells(line), [])
            found.append(current)
        elif not SEPARATOR.match(line.strip()):
            current[2].append((number, cells(line)))
    return found


def stage_id(cell: str) -> str:
    match = STAGE.match(cell)
    return match.group(1) if match else ""


class Specification:
    """One specification set, read once, with every defect found in it."""

    def __init__(self, root: Path):
        self.root = root
        self.texts: dict[str, str] = {}
        self.prefixes: set[str] = set()
        self.owners: set[str] = set()
        self.homes: dict[str, str] = {}
        self.ranges: dict[str, list[tuple[int, int]]] = {}
        self.decisions: dict[str, Decision] = {}
        self.items: dict[str, Item] = {}
        self.stages: list[str] = []
        self.phases: set[str] = set()
        self.listed: dict[str, list[Listing]] = {}
        self.findings: list[str] = []

    def find(self, where: str, line: int, message: str) -> None:
        self.findings.append(f"{where}:{line}: {message}")

    def load(self) -> str | None:
        """Read every file of the set; the reason it cannot be read, if any."""
        if not self.root.is_dir():
            return f"{self.root} is not a directory"
        if not (self.root / "README.md").is_file():
            return f"{self.root} has no README.md, the specification's entry point"
        for path in sorted(self.root.glob("*.md")):
            try:
                self.texts[path.name] = blank_fences(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError) as error:
                return f"cannot read {path}: {error}"
        return None

    def check(self) -> None:
        self.read_identifiers()
        self.read_owners()
        self.read_homes()
        self.read_decisions()
        self.read_items()
        self.check_items()
        self.read_build_order()
        self.check_open_decisions()
        self.check_references()
        self.check_ranges()
        self.check_stages()

    @property
    def readme(self) -> str:
        return self.texts["README.md"]

    def read_identifiers(self) -> None:
        forms: set[str] = set()
        for _, header, rows in tables(self.readme, (0, len(self.readme))):
            if header[:1] == ["Form"]:
                forms.update(prefix for _, row in rows for prefix in FORM.findall(row[0]))
        self.prefixes = forms - {"DEC"}
        if not self.prefixes:
            self.find("README.md", 1, "the Identifiers table names no item prefix, "
                                      "as a form such as `WID-nn`")
        names = "|".join(sorted(map(re.escape, self.prefixes | {"DEC"}), key=len, reverse=True))
        self.reference = re.compile(rf"(?<![\w-])((?:{names})-\d+)(?:\.AC(\d+))?(?![\w-])")
        items = "|".join(sorted(map(re.escape, self.prefixes), key=len, reverse=True)) or "(?!)"
        self.item_id = re.compile(rf"^(?:{items})-\d+$")
        self.citation = re.compile(rf"(?<![\w-])((?:{items})-\d+)\.AC(\d+)(?!\d)")
        self.item_range = re.compile(rf"(?<![\w-])((?:{items}))-(\d+) to \1-(\d+)(?!\d)")
        self.listing = re.compile(rf"(?<![\w-])((?:{items})-\d+)(?![\w-])(\s*\()?")

    def read_owners(self) -> None:
        found = labelled(self.readme, "Owners")
        self.owners = set(OWNER.findall(found[1])) if found else set()
        if not self.owners:
            self.find("README.md", found[0] if found else 1,
                      "the README lists no owners under **Owners.**")

    def read_homes(self) -> None:
        found = labelled(self.readme, "Where to find an ID")
        if not found:
            self.find("README.md", 1, "the README has no **Where to find an ID.** list")
            return
        first, body = found
        for offset, line in enumerate(body.split("\n")):
            ranged = FILE_RANGES.match(line)
            if ranged:
                self.ranges.setdefault(ranged.group(1), []).extend(
                    parse_ranges(ranged.group(2)))
                continue
            waiting: list[str] = []
            for token in re.findall(r"`([^`]+)`", line):
                if token in self.prefixes:
                    waiting.append(token)
                elif token.endswith(".md"):
                    self.homes.update((prefix, token) for prefix in waiting)
                    waiting = []
        for prefix in sorted(self.prefixes - self.homes.keys()):
            self.find("README.md", first, "**Where to find an ID.** does not say which "
                                          f"file holds the `{prefix}` items")

    def read_decisions(self) -> None:
        for name, text in self.texts.items():
            span = section(text, "Decisions")
            for header_line, header, rows in tables(text, span) if span else []:
                if not any(DECISION_ID.match(row[0]) for _, row in rows):
                    continue
                if header != DECISION_COLUMNS:
                    self.find(name, header_line,
                              f"a decision table has the columns {', '.join(header)}; it "
                              f"must have {', '.join(DECISION_COLUMNS)}")
                    continue
                for line, row in rows:
                    self.read_decision(name, line, row)

    def read_decision(self, name: str, line: int, row: list[str]) -> None:
        if len(row) != len(DECISION_COLUMNS):
            self.find(name, line, f"a decision row has {len(row)} cells, not "
                                  f"{len(DECISION_COLUMNS)}")
            return
        decision, rule, status, owner, ask, affects, _ = row
        if not DECISION_ID.match(decision):
            self.find(name, line, f"{decision!r} is not a decision id, DEC-nnn")
            return
        if decision in self.decisions:
            first = self.decisions[decision]
            self.find(name, line, f"{decision} is defined more than once, also at "
                                  f"{first.file}:{first.line}")
            return
        if not rule:
            self.find(name, line, f"{decision} states no rule")
        if status not in STATUSES:
            self.find(name, line, f"{decision} has the status {status!r}; it must be one of "
                                  f"{', '.join(STATUSES)}")
        if self.owners and owner not in self.owners:
            self.find(name, line, f"{decision} names the owner {owner!r}, whom the "
                                  "README's Owners list does not name")
        if ask != NO_QUESTION and not ASK.match(ask):
            self.find(name, line, f"{decision} asks {ask!r}: the Ask column holds "
                                  f"{NO_QUESTION} or a question, such as questions.md 4")
        if status == "Pending" and ask == NO_QUESTION:
            self.find(name, line, f"{decision} is Pending and names no question: its Ask "
                                  "column names the question that decides it")
        targets = [target.strip() for target in affects.split(",") if target.strip()]
        if not targets:
            self.find(name, line, f"{decision} affects no item")
        for target in targets:
            if not self.item_id.match(target):
                self.find(name, line, f"{decision} lists {target!r} under Affects, which "
                                      "names build items only")
        self.decisions[decision] = Decision(name, line, status)

    def read_items(self) -> None:
        for name, text in self.texts.items():
            for match in ITEM_HEADING.finditer(text):
                item = match.group(1)
                prefix = item.split("-")[0]
                if prefix not in self.prefixes:
                    continue
                line = line_of(text, match.start())
                if item in self.items:
                    first = self.items[item]
                    self.find(name, line, f"{item} is defined more than once, also at "
                                          f"{first.file}:{first.line}")
                    continue
                following = HEADING.search(text, match.end())
                body = text[match.end():following.start() if following else len(text)]
                numbers = [int(number) for number in CRITERION.findall(body)]
                if any(later <= earlier for earlier, later in zip(numbers, numbers[1:])):
                    given = ", ".join(f"AC{number}" for number in numbers)
                    self.find(name, line, f"{item} numbers its criteria {given}; the numbers "
                                          "rise, and each is used once")
                home = self.homes.get(prefix)
                if home and home != name:
                    self.find(name, line, f"{item} is in {name}; the README puts the "
                                          f"`{prefix}` items in {home}")
                self.items[item] = Item(name, line, numbers, BLOCK.findall(body))

    def main_of(self, item: str) -> str | None:
        """The main item of the group a part belongs to; None for an item that is
        its group's main item, or whose group has none."""
        prefix, number = item.split("-")
        main = f"{prefix}-{int(number) // 10 * 10:0{len(number)}d}"
        return main if main != item and main in self.items else None

    def check_items(self) -> None:
        """Each item's blocks. A part shares its main item's What and Rules."""
        for item, where in self.items.items():
            required = ("Acceptance",) if self.main_of(item) else REQUIRED_BLOCKS
            for block in required:
                if block not in where.blocks:
                    self.find(where.file, where.line, f"{item} has no **{block}.** block")
            if "Acceptance" in where.blocks and not where.criteria:
                self.find(where.file, where.line, f"{item} has no acceptance criterion")

    def stages_of(self, item: str) -> list[Listing]:
        """Where an item is built: where the build order lists it, or, for a part
        it does not list, where it lists the part's main item."""
        main = self.main_of(item)
        return self.listed.get(item) or (self.listed.get(main, []) if main else [])

    def read_build_order(self) -> None:
        span = section(self.readme, "Build order")
        if not span:
            self.find("README.md", 1, "the README has no ## Build order")
            return
        for _, header, rows in tables(self.readme, span):
            if header[:1] == ["Phase"]:
                self.phases.update(stage_id(row[0]) for _, row in rows)
            if header[:1] != ["Stage"]:
                continue
            for line, row in rows:
                stage = stage_id(row[0])
                if stage in self.stages:
                    self.find("README.md", line, f"the stage {stage} is listed twice")
                self.stages.append(stage)
                if len(row) < 3 or not row[2]:
                    self.find("README.md", line, f"the stage {stage} has no exit criterion")
                self.read_listing(line, len(self.stages) - 1, row[1] if len(row) > 1 else "")
        if not self.stages:
            self.find("README.md", line_of(self.readme, span[0]),
                      "the build order has no stage table: Stage, Items, Exit criterion")

    def read_listing(self, line: int, stage: int, cell: str) -> None:
        for match in self.item_range.finditer(cell):
            prefix, low, high = match.group(1), int(match.group(2)), int(match.group(3))
            for item in self.items:
                kind, number = item.split("-")
                if kind == prefix and low <= int(number) <= high:
                    self.listed.setdefault(item, []).append(Listing(stage, line, False))
        for match in self.listing.finditer(self.item_range.sub("", cell)):
            self.listed.setdefault(match.group(1), []).append(
                Listing(stage, line, bool(match.group(2))))

    def check_open_decisions(self) -> None:
        pending = {d for d, decision in self.decisions.items() if decision.status == "Pending"}
        stages = set(self.stages) | self.phases
        listed: set[str] = set()
        span = section(self.readme, "Open decisions")
        for _, header, rows in tables(self.readme, span) if span else []:
            if header[:1] != ["Decision"]:
                continue
            for line, row in rows:
                decision, first = row[0], stage_id(row[1]) if len(row) > 1 else ""
                listed.add(decision)
                if decision in self.decisions and decision not in pending:
                    self.find("README.md", line, f"{decision} is in the open decisions, but it "
                                                 "is not Pending: an answered decision "
                                                 "leaves the list")
                if first not in stages:
                    self.find("README.md", line, f"{decision} is first needed in {first!r}, "
                                                 "which is not a stage or a phase of the "
                                                 "build order")
        for decision in sorted(pending - listed):
            where = self.decisions[decision]
            self.find(where.file, where.line, f"{decision} is Pending, but the README's "
                                              "Open decisions list does not hold it")

    def check_references(self) -> None:
        for name, text in self.texts.items():
            for match in self.reference.finditer(text):
                target, criterion = match.group(1), match.group(2)
                item = self.items.get(target)
                known = target in self.decisions if target.startswith("DEC-") else bool(item)
                if criterion:
                    known = bool(item) and int(criterion) in item.criteria
                    target = f"{target}.AC{criterion}"
                if not known:
                    self.find(name, line_of(text, match.start()),
                              f"names {target}, which does not exist")

    def check_ranges(self) -> None:
        if not self.ranges:
            return
        for decision, where in self.decisions.items():
            number = int(decision.split("-")[1])
            files = [file for file, spans in self.ranges.items()
                     if any(low <= number <= high for low, high in spans)]
            if where.file not in files:
                listed = (f"the README lists it under {', '.join(files)}" if files else
                          "no range in the README's **Where to find an ID.** holds it")
                self.find(where.file, where.line, f"{decision} is in {where.file}, but "
                                                  f"{listed}")

    def check_stages(self) -> None:
        for item, where in self.items.items():
            listings = self.listed.get(item, [])
            if not self.stages_of(item):
                self.find(where.file, where.line, f"{item} is in no stage of the build order")
            elif len(listings) > 1 and not all(listing.names_part for listing in listings):
                whole = next(listing for listing in listings if not listing.names_part)
                stages = ", ".join(self.stages[listing.stage] for listing in listings)
                self.find("README.md", whole.line,
                          f"{item} is listed in the stages {stages}: an item split across "
                          "stages names its part, in parentheses, in each")

    def due(self, through: int) -> list[str]:
        """The criteria of every item due by a stage: built there or before, and
        nowhere later."""
        return [f"{item}.AC{number}" for item, where in self.items.items()
                if self.stages_of(item)
                and max(listing.stage for listing in self.stages_of(item)) <= through
                for number in where.criteria]

    def check_citations(self, files: list[Path], through: int) -> int:
        cited: set[str] = set()
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(text.splitlines(), 1):
                for match in self.citation.finditer(line):
                    reference = f"{match.group(1)}.AC{match.group(2)}"
                    item = self.items.get(match.group(1))
                    if not item or int(match.group(2)) not in item.criteria:
                        self.find(str(path), number, f"cites {reference}, which does not "
                                                     "exist")
                    cited.add(reference)
        due = self.due(through)
        for reference in due:
            if reference not in cited:
                where = self.items[reference.split(".")[0]]
                self.find(where.file, where.line, f"{reference} is due by "
                                                  f"{self.stages[through]}, but no test "
                                                  "cites it")
        return len(due)


def parse_ranges(text: str) -> list[tuple[int, int]]:
    """`DEC-001 to DEC-011; DEC-016.` as [(1, 11), (16, 16)]."""
    spans = []
    for part in text.split(";"):
        numbers = [int(number) for number in re.findall(r"DEC-(\d+)", part)]
        if len(numbers) == 2 and " to " in part:
            spans.append((numbers[0], numbers[1]))
        elif len(numbers) == 1:
            spans.append((numbers[0], numbers[0]))
    return spans


def test_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_file():
            files.append(path)
            continue
        files += sorted(found for found in path.rglob("*") if found.is_file()
                        and not SKIPPED_DIRS & set(found.relative_to(path).parts))
    return files


def not_run(reason: str) -> int:
    print(f"NOT RUN - {reason}")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a specification set, and the "
                                                 "tests' citations of it.")
    parser.add_argument("--specs", required=True, type=Path,
                        help="the specification directory, such as docs/specs")
    parser.add_argument("--tests", nargs="+", type=Path,
                        help="files or directories whose criterion citations to check")
    parser.add_argument("--through",
                        help="the last stage whose criteria are due (default: the last)")
    args = parser.parse_args(argv)
    if args.through and not args.tests:
        parser.error("--through needs --tests")

    spec = Specification(args.specs)
    reason = spec.load()
    if reason:
        return not_run(reason)
    spec.check()

    due = None
    if args.tests:
        missing = [str(path) for path in args.tests if not path.exists()]
        if missing:
            return not_run(f"{', '.join(missing)} does not exist")
        through = len(spec.stages) - 1
        if args.through:
            if args.through not in spec.stages:
                return not_run(f"--through {args.through} names no stage of the build "
                               f"order ({', '.join(spec.stages)})")
            through = spec.stages.index(args.through)
        if through >= 0:
            due = (spec.stages[through], spec.check_citations(test_files(args.tests), through))

    for finding in spec.findings:
        print(finding)
    if spec.findings:
        print(f"FAIL - {len(spec.findings)} "
              f"{'defect' if len(spec.findings) == 1 else 'defects'} found")
        return 1
    criteria = sum(len(item.criteria) for item in spec.items.values())
    print(f"OK - {len(spec.decisions)} decisions, {len(spec.items)} items and {criteria} "
          "acceptance criteria, each defined once, with every reference resolved")
    if due:
        print(f"OK - every acceptance criterion due by {due[0]} is cited: "
              f"{due[1]} of {due[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

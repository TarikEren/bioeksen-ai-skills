"""sds-planning's specification checker, as an installed plugin carries it."""
import importlib.util
import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / "plugins" / "bioeksen-sds" / "skills" / "sds-planning"
SCRIPT = SKILL / "scripts" / "check_specs.py"
EXAMPLE = SKILL / "references" / "example"

# Every acceptance criterion of the example set, by the stage its item is due in.
B0 = ["FND-01.AC1", "FND-01.AC2", "FND-02.AC1", "FND-02.AC2"]
B1 = ["WID-10.AC1", "WID-10.AC2", "WID-10.AC3", "WID-10.AC4", "WID-20.AC1", "WID-20.AC2"]
B2 = [f"WID-30.AC{n}" for n in range(1, 8)] + ["WID-40.AC1", "WID-40.AC2", "WID-40.AC3"]


def load():
    """The plugin's script as a fresh module, wherever the plugin is installed."""
    spec = importlib.util.spec_from_file_location("sds_check_specs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SpecTest(unittest.TestCase):
    """A copy of the example set to break, one rule at a time."""

    def setUp(self):
        self.module = load()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.specs = self.root / "specs"
        shutil.copytree(EXAMPLE, self.specs)

    def edit(self, name: str, old: str, new: str) -> None:
        path = self.specs / name
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"the example's {name} no longer holds {old!r}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def citing_tests(self, *ids: str) -> Path:
        folder = self.root / "tests"
        folder.mkdir(exist_ok=True)
        body = "".join(f'it("{ref}: a rule", () => {{}});\n' for ref in ids)
        (folder / "widgets.test.ts").write_text(body, encoding="utf-8")
        return folder

    def run_check(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            status = self.module.main(["--specs", str(self.specs), *args])
        return status, out.getvalue()

    def assertFinding(self, *expected: str, args: tuple[str, ...] = ()) -> None:
        status, out = self.run_check(*args)
        self.assertEqual(status, 1, out)
        for text in expected:
            self.assertIn(text, out)


class ConsistentSetTest(SpecTest):
    def test_the_skills_example_set_is_consistent(self):
        status, out = self.run_check()
        self.assertEqual(status, 0, out)
        self.assertIn("7 decisions, 6 items and 20 acceptance criteria", out)

    def test_a_missing_directory_is_not_run(self):
        out = io.StringIO()
        with redirect_stdout(out):
            status = self.module.main(["--specs", str(self.root / "nowhere")])
        self.assertEqual(status, 2, out.getvalue())
        self.assertIn("NOT RUN", out.getvalue())

    def test_a_set_without_its_readme_is_not_run(self):
        (self.specs / "README.md").unlink()
        status, out = self.run_check()
        self.assertEqual(status, 2, out)
        self.assertIn("README.md", out)


class IdentifierTest(SpecTest):
    def test_an_id_defined_twice(self):
        self.edit("widgets.md", "| DEC-007 | QA decides", "| DEC-006 | QA decides")
        self.assertFinding("DEC-006 is defined more than once")

    def test_an_item_defined_twice(self):
        self.edit("widgets.md", "### WID-40 Retire requests", "### WID-30 Retire requests")
        self.assertFinding("WID-30 is defined more than once")

    def test_a_reference_to_a_decision_that_does_not_exist(self):
        self.edit("widgets.md", "persons (DEC-005, WID-20)", "persons (DEC-009, WID-20)")
        self.assertFinding("widgets.md:", "DEC-009, which does not exist")

    def test_a_reference_to_a_criterion_that_does_not_exist(self):
        self.edit("README.md", "for example `WID-30.AC6`", "for example `WID-30.AC9`")
        self.assertFinding("README.md:", "WID-30.AC9, which does not exist")

    def test_an_item_outside_the_file_the_readme_names(self):
        (self.specs / "other.md").write_text(
            "# Other\n\n### WID-50 Stray\n\n**What.** A stray item.\n\n**Rules.** None.\n\n"
            "**Acceptance.**\n- **AC1.** It exists.\n", encoding="utf-8")
        self.edit("README.md", "| **B2 Review and retirement** | WID-30 (the moves 4 and 5), WID-40",
                  "| **B2 Review and retirement** | WID-30 (the moves 4 and 5), WID-40, WID-50")
        self.assertFinding("WID-50 is in other.md", "widgets.md")

    def test_a_decision_outside_its_files_range(self):
        self.edit("README.md", "`widgets.md`: DEC-001 to DEC-007.", "`widgets.md`: DEC-001 to DEC-006.")
        self.assertFinding("DEC-007")


class DecisionTest(SpecTest):
    def test_a_pending_decision_must_ask_its_question(self):
        self.edit("widgets.md", "| Pending | QA | questions.md 1 |", "| Pending | QA | — |")
        self.assertFinding("DEC-003 is Pending")

    def test_an_unknown_status(self):
        self.edit("widgets.md", "| Default | PO | — | WID-20", "| Agreed | PO | — | WID-20")
        self.assertFinding("DEC-005", "Agreed")

    def test_an_owner_the_readme_does_not_list(self):
        self.edit("widgets.md", "| Default | QA | — | WID-40", "| Default | HR | — | WID-40")
        self.assertFinding("DEC-007", "HR")

    def test_an_ask_that_names_no_question(self):
        self.edit("widgets.md", "| Decided | PO | questions.md 2 |", "| Decided | PO | ask QA |")
        self.assertFinding("DEC-004", "ask QA")

    def test_affects_names_only_items(self):
        self.edit("widgets.md", "| WID-20, WID-30 | §3.3 |", "| WID-20, DEC-002 | §3.3 |")
        self.assertFinding("DEC-005", "DEC-002")

    def test_a_decision_table_with_other_columns(self):
        self.edit("widgets.md", "| ID | Decision | Status | Owner | Ask | Affects | Trace |",
                  "| ID | Decision | Status | Owner | Affects | Ask | Trace |")
        self.assertFinding("ID, Decision, Status, Owner, Ask, Affects, Trace")


class ItemTest(SpecTest):
    def test_an_item_without_acceptance_criteria(self):
        self.edit("widgets.md",
                  "**Acceptance.**\n- **AC1.** If a person without the `CREATOR` role creates a "
                  "widget, the\n  creation fails.\n- **AC2.** If the creator of a widget approves "
                  "it, the approval fails.\n", "")
        self.assertFinding("WID-20", "Acceptance")

    def test_an_item_without_what(self):
        self.edit("widgets.md", "**What.** These roles act on widgets.\n", "")
        self.assertFinding("WID-20", "What")

    def test_criteria_numbered_out_of_order(self):
        self.edit("widgets.md", "- **AC3.** If a person deletes", "- **AC5.** If a person deletes")
        self.assertFinding("WID-10", "AC1, AC2, AC5, AC4", "rise")

    def test_a_number_used_twice(self):
        self.edit("widgets.md", "- **AC3.** If a person deletes", "- **AC2.** If a person deletes")
        self.assertFinding("WID-10", "AC1, AC2, AC2, AC4")

    def test_a_removed_criterion_leaves_its_number_unused(self):
        # Renumbering AC4 to AC3 would re-point every test citing it.
        self.edit("widgets.md", "- **AC3.** If a person deletes a widget, the deletion fails, "
                                "and the row\n  stays.\n", "")
        status, out = self.run_check()
        self.assertEqual(status, 0, out)


class BuildOrderTest(SpecTest):
    def test_every_item_is_in_a_stage(self):
        self.edit("README.md", "WID-30 (the moves 4 and 5), WID-40 |", "WID-30 (the moves 4 and 5) |")
        self.assertFinding("WID-40 is in no stage")

    def test_an_item_in_two_stages_names_its_part_in_each(self):
        self.edit("README.md", "WID-30 (the moves 4 and 5), WID-40", "WID-30, WID-40")
        self.assertFinding("WID-30", "names its part")

    def test_the_open_list_holds_every_pending_decision(self):
        self.edit("README.md", "| DEC-006 | B1 |\n", "")
        self.assertFinding("DEC-006 is Pending", "Open decisions")

    def test_the_open_list_holds_only_pending_decisions(self):
        self.edit("README.md", "| DEC-006 | B1 |\n", "| DEC-006 | B1 |\n| DEC-001 | B0 |\n")
        self.assertFinding("DEC-001", "not Pending")

    def test_the_open_list_names_a_stage_that_exists(self):
        self.edit("README.md", "| DEC-006 | B1 |", "| DEC-006 | B9 |")
        self.assertFinding("DEC-006", "B9")

    def test_a_phase_is_a_stage_the_open_list_may_name(self):
        self.edit("README.md", "**The B1 order.**",
                  "| Phase | Items |\n|---|---|\n| B2.1 Review | WID-30 |\n\n**The B1 order.**")
        self.edit("README.md", "| DEC-006 | B1 |", "| DEC-006 | B2.1 |")
        status, out = self.run_check()
        self.assertEqual(status, 0, out)


class CitationTest(SpecTest):
    def test_every_criterion_cited(self):
        status, out = self.run_check("--tests", str(self.citing_tests(*B0, *B1, *B2)))
        self.assertEqual(status, 0, out)
        self.assertIn("20 of 20", out)

    def test_an_uncited_criterion(self):
        tests = self.citing_tests(*B0, *B1, *[ref for ref in B2 if ref != "WID-30.AC6"])
        self.assertFinding("WID-30.AC6", "no test cites", args=("--tests", str(tests)))

    def test_a_citation_of_a_criterion_that_does_not_exist(self):
        tests = self.citing_tests(*B0, *B1, *B2, "WID-30.AC8")
        self.assertFinding("widgets.test.ts:21", "WID-30.AC8, which does not exist",
                           args=("--tests", str(tests)))

    def test_only_the_stages_so_far_are_due(self):
        tests = self.citing_tests(*B0)
        status, out = self.run_check("--tests", str(tests), "--through", "B0")
        self.assertEqual(status, 0, out)
        self.assertFinding("WID-10.AC1", args=("--tests", str(tests), "--through", "B1"))

    def test_a_split_item_is_due_at_the_last_stage_that_lists_it(self):
        # WID-30 is listed in B1 and in B2, so its criteria are due at B2.
        tests = self.citing_tests(*B0, *B1)
        status, out = self.run_check("--tests", str(tests), "--through", "B1")
        self.assertEqual(status, 0, out)
        self.assertFinding("WID-30.AC1", args=("--tests", str(tests), "--through", "B2"))

    def test_a_stage_that_does_not_exist_is_not_run(self):
        status, out = self.run_check("--tests", str(self.citing_tests(*B0)), "--through", "B7")
        self.assertEqual(status, 2, out)
        self.assertIn("B7", out)

    def test_a_tests_path_that_does_not_exist_is_not_run(self):
        status, out = self.run_check("--tests", str(self.root / "nowhere"))
        self.assertEqual(status, 2, out)
        self.assertIn("NOT RUN", out)


if __name__ == "__main__":
    unittest.main()

"""The message checks commit_msg.py runs as a commit-msg hook and in CI."""
import io
import unittest
from contextlib import redirect_stdout

from change_id import Attribution
from commit_msg import check, clean, main, with_change_id
from tests.repository import MonorepoTest

SOFTWARE_ID = "bioeksen-sds"
CHANGE_ID = "Change-Id: bioeksen-sds-20261005T120000-ab12"


def message(*paragraphs: str) -> str:
    return "\n\n".join(paragraphs)


class ConformingTest(unittest.TestCase):
    def test_conforming_message_has_no_problems(self):
        self.assertEqual(check(message("feat(api): add a thing", "Why it matters.",
                                       CHANGE_ID), SOFTWARE_ID), [])

    def test_identifier_minted_before_utc_plus_three_still_conforms(self):
        old = "Change-Id: bioeksen-sds-20260929T132418Z-e830"
        self.assertEqual(check(message("docs: explain a thing", old), SOFTWARE_ID), [])


class SubjectTest(unittest.TestCase):
    def problems(self, subject: str) -> list[str]:
        return check(message(subject, CHANGE_ID), SOFTWARE_ID)

    def test_unknown_type_is_a_problem(self):
        self.assertTrue(any("type 'feature'" in p for p in self.problems("feature: add x")))

    def test_capitalised_description_is_a_problem(self):
        self.assertTrue(any("capital" in p for p in self.problems("feat: Add x")))

    def test_trailing_period_is_a_problem(self):
        self.assertTrue(any("period" in p for p in self.problems("feat: add x.")))

    def test_subject_must_be_followed_by_a_blank_line(self):
        problems = check("feat: add x\nno blank line\n\n" + CHANGE_ID, SOFTWARE_ID)
        self.assertTrue(any("blank line" in p for p in problems))


class ChangeIdTest(unittest.TestCase):
    def test_missing_change_id_is_a_problem(self):
        problems = check(message("docs: x", "Body."), SOFTWARE_ID)
        self.assertTrue(any("0 Change-Id" in p for p in problems))

    def test_two_change_ids_are_a_problem(self):
        problems = check(message("docs: x", CHANGE_ID + "\n" + CHANGE_ID), SOFTWARE_ID)
        self.assertTrue(any("2 Change-Id" in p for p in problems))

    def test_another_projects_software_id_is_a_problem(self):
        other = "Change-Id: auth-service-20261005T120000-ab12"
        problems = check(message("docs: x", other), SOFTWARE_ID)
        self.assertTrue(any("'auth-service'" in p for p in problems))

    def test_change_id_outside_the_final_paragraph_is_a_problem(self):
        problems = check(message("docs: x", CHANGE_ID, "A later paragraph."), SOFTWARE_ID)
        self.assertTrue(any("final paragraph" in p for p in problems))


class BreakingChangeTest(unittest.TestCase):
    def test_bang_without_footer_is_a_problem(self):
        problems = check(message("feat(api)!: remove x", CHANGE_ID), SOFTWARE_ID)
        self.assertTrue(any("no BREAKING CHANGE" in p for p in problems))

    def test_footer_without_bang_is_a_problem(self):
        problems = check(message("feat(api): remove x", "BREAKING CHANGE: x is gone.",
                                 CHANGE_ID), SOFTWARE_ID)
        self.assertTrue(any("carries no !" in p for p in problems))

    def test_bang_with_footer_conforms(self):
        self.assertEqual(check(message("feat(api)!: remove x", "BREAKING CHANGE: x is gone.",
                                       CHANGE_ID), SOFTWARE_ID), [])


class PlaceholderTest(unittest.TestCase):
    def test_placeholder_is_a_problem(self):
        problems = check(message("docs: mention <software-id>", CHANGE_ID), SOFTWARE_ID)
        self.assertTrue(any("placeholder" in p for p in problems))


class TestExemptTest(unittest.TestCase):
    def problems(self, subject: str, trailers: str, *body: str) -> list[str]:
        return check(message(subject, *body, trailers), SOFTWARE_ID)

    def test_named_exemption_in_the_final_paragraph_conforms(self):
        self.assertEqual(self.problems("feat(api): add x", CHANGE_ID + "\nTest-Exempt: docs"), [])

    def test_a_feature_driven_by_acceptance_tests_already_on_its_branch_conforms(self):
        self.assertEqual(self.problems("feat(api): add x", CHANGE_ID + "\nTest-Exempt: acceptance"), [])

    def test_unknown_exemption_is_a_problem(self):
        problems = self.problems("feat(api): add x", CHANGE_ID + "\nTest-Exempt: whatever")
        self.assertTrue(any("Test-Exempt" in p and "'whatever'" in p for p in problems), problems)

    def test_two_exemptions_are_a_problem(self):
        problems = self.problems("fix(api): mend x",
                                 CHANGE_ID + "\nTest-Exempt: docs\nTest-Exempt: config")
        self.assertTrue(any("2 Test-Exempt" in p for p in problems), problems)

    def test_exemption_outside_the_final_paragraph_is_a_problem(self):
        problems = self.problems("feat(api): add x", CHANGE_ID, "Test-Exempt: docs")
        self.assertTrue(any("Test-Exempt" in p and "final paragraph" in p for p in problems),
                        problems)

    def test_exemption_on_a_commit_that_needs_none_is_a_problem(self):
        problems = self.problems("docs: explain x", CHANGE_ID + "\nTest-Exempt: docs")
        self.assertTrue(any("Test-Exempt" in p and "docs commit" in p for p in problems),
                        problems)

    def test_minted_change_id_goes_first_beside_an_exemption(self):
        result = with_change_id(message("feat(api): add x", "Body.", "Test-Exempt: config"),
                                "bioeksen-sds-20261005T120000-ab12")
        self.assertTrue(result.endswith(CHANGE_ID + "\nTest-Exempt: config\n"), result)
        self.assertEqual(check(clean(result), SOFTWARE_ID), [])


class FixesLogTest(unittest.TestCase):
    def problems(self, subject: str, trailers: str, *body: str) -> list[str]:
        return check(message(subject, *body, trailers), SOFTWARE_ID)

    def test_a_fix_naming_each_record_it_resolves_conforms(self):
        trailers = CHANGE_ID + "\nFixes-Log: 01J9Z4K7XQ2M8N\nFixes-Log: 01J9Z4K7XQ2M8P"
        self.assertEqual(self.problems("fix(db): retry a write that lost its connection", trailers), [])

    def test_fixes_log_on_a_commit_that_is_not_a_fix_is_a_problem(self):
        problems = self.problems("feat(db): cache widget reads", CHANGE_ID + "\nFixes-Log: 01J9Z4K7XQ2M8N")
        self.assertTrue(any("Fixes-Log" in p and "feat commit" in p for p in problems), problems)

    def test_fixes_log_outside_the_final_paragraph_is_a_problem(self):
        problems = self.problems("fix(db): retry a write", CHANGE_ID, "Fixes-Log: 01J9Z4K7XQ2M8N")
        self.assertTrue(any("Fixes-Log" in p and "final paragraph" in p for p in problems), problems)

    def test_fixes_log_naming_no_single_record_is_a_problem(self):
        for value in ("", "01J9Z4K7XQ2M8N 01J9Z4K7XQ2M8P"):
            problems = self.problems("fix(db): retry a write", f"{CHANGE_ID}\nFixes-Log: {value}")
            self.assertTrue(any("Fixes-Log" in p and "one recordId" in p for p in problems),
                            (value, problems))


class CleanTest(unittest.TestCase):
    def test_comment_lines_and_everything_below_scissors_are_dropped(self):
        raw = ("docs: x\n\n" + CHANGE_ID + "\n# a comment\n"
               "# ------------------------ >8 ------------------------\ndiff --git a b\n")
        self.assertEqual(clean(raw), "docs: x\n\n" + CHANGE_ID)


class WithChangeIdTest(unittest.TestCase):
    def test_change_id_goes_first_in_an_existing_trailer_paragraph(self):
        result = with_change_id(message("docs: x", "Body.", "Co-Authored-By: A <a@b>"),
                                "bioeksen-sds-20261005T120000-ab12")
        self.assertTrue(result.endswith(CHANGE_ID + "\nCo-Authored-By: A <a@b>\n"), result)
        self.assertEqual(check(clean(result), SOFTWARE_ID), [])

    def test_change_id_becomes_its_own_paragraph_after_prose(self):
        result = with_change_id(message("docs: x", "Body."), "bioeksen-sds-20261005T120000-ab12")
        self.assertTrue(result.endswith("Body.\n\n" + CHANGE_ID + "\n"), result)

    def test_trailers_follow_the_change_id(self):
        result = with_change_id(message("feat(ui): x", "Co-Authored-By: A <a@b>"),
                                "bio-software-20261008T100000-ab12",
                                ["Affects: a", "Changes-Package: @x/ui"])
        self.assertTrue(result.endswith("Change-Id: bio-software-20261008T100000-ab12\n"
                                        "Affects: a\nChanges-Package: @x/ui\n"
                                        "Co-Authored-By: A <a@b>\n"), result)


SHARED = Attribution("bio-software", ("bio-inventory", "bio-softop"), ("@bioeksen/ui",), True)
SHARED_ID = "Change-Id: bio-software-20261008T100000-ab12"


class AttributionCheckTest(unittest.TestCase):
    """The prefix and trailers release-notes.md's Release units give a commit."""

    def problems(self, trailers: str, expected: Attribution = SHARED) -> list[str]:
        return check(message("feat(ui): add x", "Body.", trailers), expected)

    def test_the_computed_prefix_and_trailers_conform(self):
        self.assertEqual(self.problems(SHARED_ID + "\nAffects: bio-inventory\n"
                                       "Affects: bio-softop\nChanges-Package: @bioeksen/ui\n"
                                       "Test-Exempt: docs"), [])

    def test_a_single_unit_commit_carries_the_units_id_and_no_trailers(self):
        unit = Attribution("bio-inventory", (), (), True)
        self.assertEqual(self.problems("Change-Id: bio-inventory-20261008T100000-ab12\n"
                                       "Test-Exempt: docs", unit), [])

    def test_another_prefix_than_the_paths_give_is_a_problem(self):
        unit = Attribution("bio-inventory", (), (), True)
        problems = self.problems(SHARED_ID + "\nTest-Exempt: docs", unit)
        self.assertTrue(any("'bio-software'" in p and "'bio-inventory'" in p and "attribute" in p
                            for p in problems), problems)

    def test_a_missing_affects_trailer_is_a_problem(self):
        problems = self.problems(SHARED_ID + "\nAffects: bio-inventory\n"
                                 "Changes-Package: @bioeksen/ui\nTest-Exempt: docs")
        self.assertTrue(any("Affects" in p and "'bio-softop'" in p for p in problems), problems)

    def test_an_affects_trailer_naming_a_unit_not_affected_is_a_problem(self):
        problems = self.problems(SHARED_ID + "\nAffects: bio-inventory\nAffects: bio-softop\n"
                                 "Affects: bio-sdk\nChanges-Package: @bioeksen/ui\n"
                                 "Test-Exempt: docs")
        self.assertTrue(any("Affects" in p and "'bio-sdk'" in p for p in problems), problems)

    def test_a_missing_or_extra_changes_package_trailer_is_a_problem(self):
        problems = self.problems(SHARED_ID + "\nAffects: bio-inventory\nAffects: bio-softop\n"
                                 "Changes-Package: @bioeksen/tsconfig\nTest-Exempt: docs")
        self.assertTrue(any("Changes-Package" in p and "'@bioeksen/ui'" in p
                            for p in problems), problems)
        self.assertTrue(any("Changes-Package" in p and "'@bioeksen/tsconfig'" in p
                            for p in problems), problems)

    def test_a_trailer_twice_is_a_problem(self):
        problems = self.problems(SHARED_ID + "\nAffects: bio-inventory\nAffects: bio-inventory\n"
                                 "Affects: bio-softop\nChanges-Package: @bioeksen/ui\n"
                                 "Test-Exempt: docs")
        self.assertTrue(any("Affects" in p and "twice" in p for p in problems), problems)

    def test_a_trailer_outside_the_final_paragraph_is_a_problem(self):
        problems = check(message("feat(ui): add x", "Affects: bio-inventory",
                                 SHARED_ID + "\nAffects: bio-softop\n"
                                 "Changes-Package: @bioeksen/ui\nTest-Exempt: docs"), SHARED)
        self.assertTrue(any("Affects" in p and "final paragraph" in p for p in problems),
                        problems)

    def test_a_breaking_commit_whose_scope_names_an_affected_unit_conforms(self):
        sdk = Attribution("bio-software", ("bio-inventory", "bio-sdk"), (), True)
        problems = check(message("feat(bio-sdk)!: rename x", "BREAKING CHANGE: x is gone.",
                                 SHARED_ID + "\nAffects: bio-inventory\nAffects: bio-sdk\n"
                                 "Test-Exempt: docs"), sdk)
        self.assertEqual(problems, [])

    def test_a_breaking_commit_in_a_monorepo_must_name_the_unit_it_breaks(self):
        sdk = Attribution("bio-software", ("bio-inventory", "bio-sdk"), (), True)
        for subject in ("feat(api)!: rename x", "feat!: rename x"):
            problems = check(message(subject, "BREAKING CHANGE: x is gone.",
                                     SHARED_ID + "\nAffects: bio-inventory\nAffects: bio-sdk\n"
                                     "Test-Exempt: docs"), sdk)
            self.assertTrue(any("scope" in p and "'bio-sdk'" in p for p in problems),
                            (subject, problems))

    def test_a_breaking_single_unit_commit_names_its_unit(self):
        unit = Attribution("bio-inventory", (), (), True)
        trailers = "Change-Id: bio-inventory-20261008T100000-ab12\nTest-Exempt: docs"
        self.assertEqual(check(message("feat(bio-inventory)!: drop x", "BREAKING CHANGE: x.",
                                       trailers), unit), [])
        problems = check(message("feat(api)!: drop x", "BREAKING CHANGE: x.", trailers), unit)
        self.assertTrue(any("scope" in p for p in problems), problems)

    def test_an_affects_trailer_in_a_repository_holding_one_service_is_a_problem(self):
        problems = check(message("docs: x", CHANGE_ID + "\nAffects: bioeksen-sds"), SOFTWARE_ID)
        self.assertTrue(any("Affects" in p for p in problems), problems)


class MonorepoRangeTest(MonorepoTest):
    def run_range(self) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            status = main(["--range", f"{self.initial}..HEAD", "--root", str(self.root)])
        return status, out.getvalue()

    def test_commits_carrying_their_attribution_conform(self):
        self.commit("feat(ui): x\n\nChange-Id: bio-inventory-20261008T100000-ab12\n"
                    "Test-Exempt: docs\n", {"packages/ui/index.ts": "y"})
        self.commit("chore: tune the linter\n\nChange-Id: bio-software-20261008T100100-ab12\n"
                    "Affects: bio-inventory\nAffects: bio-softop\n"
                    "Changes-Package: @bioeksen/eslint-config\n",
                    {"packages/eslint-config/index.js": "y"})
        status, out = self.run_range()
        self.assertEqual(status, 0, out)

    def test_a_commit_carrying_the_monorepos_id_for_one_app_fails(self):
        self.commit("feat(ui): x\n\nChange-Id: bio-software-20261008T100000-ab12\n"
                    "Test-Exempt: docs\n", {"apps/bio-inventory/app/page.tsx": "y"})
        status, out = self.run_range()
        self.assertEqual(status, 1, out)
        self.assertIn("'bio-inventory'", out)

    def test_the_hook_mints_the_id_and_trailers_the_staged_change_gets(self):
        self.stage({"packages/eslint-config/index.js": "y"})
        path = self.root / "MSG"
        path.write_text("chore: tune the linter\n", encoding="utf-8")
        self.assertEqual(main(["--hook", str(path), "--root", str(self.root)]), 0)
        written = path.read_text(encoding="utf-8")
        self.assertRegex(written, r"\nChange-Id: bio-software-\d{8}T\d{6}-[a-z0-9]{4,}\n"
                                  r"Affects: bio-inventory\nAffects: bio-softop\n"
                                  r"Changes-Package: @bioeksen/eslint-config\n$")

    def test_the_hook_leaves_an_existing_change_id_to_ci(self):
        # An amended or reworded commit's staged change is not its whole change,
        # so only --range, against the first parent, can attribute it.
        self.stage({"apps/bio-inventory/app/page.tsx": "y"})
        path = self.root / "MSG"
        path.write_text("docs: x\n\nChange-Id: bio-softop-20261008T100000-ab12\n",
                        encoding="utf-8")
        self.assertEqual(main(["--hook", str(path), "--root", str(self.root)]), 0)

    def test_a_commit_from_a_history_moved_in_is_not_checked(self):
        self.git("rm", "-q", ".bioeksen/software-id")
        self.commit("fix: an old commit\n", {"apps/bio-inventory/app/page.tsx": "y"})
        status, out = self.run_range()
        self.assertEqual(status, 0, out)
        self.assertIn("predates", out)


if __name__ == "__main__":
    unittest.main()

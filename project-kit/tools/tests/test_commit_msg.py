"""The message checks commit_msg.py runs as a commit-msg hook and in CI."""
import unittest

from commit_msg import check, clean, with_change_id

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


if __name__ == "__main__":
    unittest.main()

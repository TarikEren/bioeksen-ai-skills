"""check_tests.py: every feat and fix commit changes a test or names an exemption."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from check_tests import DEFAULT_PATTERNS, exemption, findings, is_test, read_patterns

CHANGE_ID = "Change-Id: bioeksen-sds-20261005T120000-ab12"


class IsTestTest(unittest.TestCase):
    def test_test_directories_count_at_any_depth(self):
        for path in ("tests/test_api.py", "service/tests/api.py", "test/ApiIT.java",
                     "web/src/__tests__/api.js", "spec/models/user_spec.rb"):
            self.assertTrue(is_test(path, DEFAULT_PATTERNS), path)

    def test_test_file_names_count_in_any_directory(self):
        for path in ("app/test_orders.py", "app/orders_test.py", "orders/handler_test.go",
                     "src/orders.test.ts", "src/orders.spec.js", "src/OrderServiceTest.java",
                     "src/OrderServiceTests.cs", "src/OrderTest.kt"):
            self.assertTrue(is_test(path, DEFAULT_PATTERNS), path)

    def test_files_that_only_look_like_tests_do_not_count(self):
        for path in ("src/orders.py", "appsettings.test.json", "openapi.spec.yaml",
                     "src/Latest.java", "contest/main.go", "docs/testing.md"):
            self.assertFalse(is_test(path, DEFAULT_PATTERNS), path)

    def test_matching_is_case_sensitive_on_every_platform(self):
        self.assertFalse(is_test("src/orderservicetest.java", DEFAULT_PATTERNS))

    def test_a_pattern_with_a_slash_matches_a_path_or_any_suffix_of_it(self):
        patterns = ["scripts/check_invariants.py", "project-kit/tools/tests/*"]
        self.assertTrue(is_test("scripts/check_invariants.py", patterns))
        self.assertTrue(is_test("project-kit/tools/tests/test_x.py", patterns))
        self.assertFalse(is_test("scripts/other.py", patterns))


class ReadPatternsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_absent_file_gives_the_defaults(self):
        self.assertEqual(read_patterns(self.root), list(DEFAULT_PATTERNS))

    def test_file_is_read_line_by_line_ignoring_comments_blanks_and_crlf(self):
        (self.root / ".bioeksen").mkdir()
        (self.root / ".bioeksen" / "test-paths").write_bytes(
            b"# what counts as a test\r\n\r\nchecks/*\r\n  scripts/verify.py  \r\n")
        self.assertEqual(read_patterns(self.root), ["checks/*", "scripts/verify.py"])


class ExemptionTest(unittest.TestCase):
    def test_named_exemption_in_the_final_paragraph(self):
        self.assertEqual(exemption(f"feat: x\n\nBody.\n\n{CHANGE_ID}\nTest-Exempt: config"),
                         "config")

    def test_exemption_outside_the_final_paragraph_is_ignored(self):
        self.assertIsNone(exemption(f"feat: x\n\nTest-Exempt: config\n\n{CHANGE_ID}"))

    def test_unknown_exemption_is_ignored(self):
        self.assertIsNone(exemption(f"feat: x\n\n{CHANGE_ID}\nTest-Exempt: whatever"))


class RepositoryTest(unittest.TestCase):
    """Commits in a throwaway repository, isolated from any git configuration."""

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        empty = self.root.parent / f"{self.root.name}.gitconfig"
        empty.write_text("", encoding="utf-8")
        self.addCleanup(empty.unlink)
        self.enterContext(mock.patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}))
        self.git("init", "-q")

    def git(self, *args: str, stdin: str | None = None) -> str:
        return subprocess.run(["git", *args], cwd=self.root, input=stdin, text=True,
                              capture_output=True, check=True).stdout

    def commit(self, subject: str, files: dict[str, str], trailers: str = CHANGE_ID) -> str:
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-F", "-", stdin=f"{subject}\n\nBody.\n\n{trailers}\n")
        return self.git("rev-parse", "--short", "HEAD").strip()

    def test_root_commit_that_adds_a_test_passes(self):
        self.commit("feat: add orders", {"src/orders.py": "x", "tests/test_orders.py": "x"})
        failures, _, checked = findings(self.root, "HEAD")
        self.assertEqual((failures, checked), ([], 1))

    def test_feat_that_changes_no_test_fails(self):
        self.commit("chore: start", {"README.md": "x"})
        sha = self.commit("feat: add orders", {"src/orders.py": "x"})
        failures, _, _ = findings(self.root, "HEAD")
        self.assertEqual(len(failures), 1)
        self.assertIn(sha, failures[0])

    def test_fix_with_a_named_exemption_passes(self):
        self.commit("chore: start", {"README.md": "x"})
        self.commit("fix: raise the pool size", {"config/app.toml": "x"},
                    trailers=f"{CHANGE_ID}\nTest-Exempt: config")
        self.assertEqual(findings(self.root, "HEAD")[0], [])

    def test_other_types_are_not_checked(self):
        self.commit("chore: start", {"README.md": "x"})
        self.commit("refactor: tidy orders", {"src/orders.py": "y"})
        self.commit("docs: explain orders", {"docs/orders.md": "x"})
        self.assertEqual(findings(self.root, "HEAD")[0], [])

    def test_only_the_range_is_checked(self):
        base = self.commit("feat: add orders", {"src/orders.py": "x"})
        self.commit("feat: add refunds", {"src/refunds.py": "x", "tests/test_refunds.py": "x"})
        self.assertEqual(findings(self.root, f"{base}..HEAD")[0], [])

    def test_merge_commits_are_skipped(self):
        self.commit("chore: start", {"README.md": "x"})
        self.git("checkout", "-q", "-b", "side")
        self.commit("feat: add refunds", {"src/refunds.py": "x", "tests/test_refunds.py": "x"})
        self.git("checkout", "-q", "-")
        self.commit("feat: add orders", {"src/orders.py": "x", "tests/test_orders.py": "x"})
        self.git("merge", "-q", "--no-ff", "--no-edit", "side")
        failures, _, checked = findings(self.root, "HEAD")
        self.assertEqual((failures, checked), ([], 3))

    def test_patterns_come_from_the_repository_and_their_edits_are_reported(self):
        self.commit("chore: start", {"README.md": "x"})
        self.commit("chore: count checks as tests", {".bioeksen/test-paths": "checks/*\n"})
        self.commit("feat: add a check", {"checks/orders.txt": "x"})
        failures, notices, _ = findings(self.root, "HEAD")
        self.assertEqual(failures, [])
        self.assertTrue(any("test-paths" in n for n in notices), notices)


if __name__ == "__main__":
    unittest.main()

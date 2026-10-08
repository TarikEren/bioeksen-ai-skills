"""check_release_note.py: a note against the commits its release contains."""
import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from check_release_note import main
from commit_msg import TYPES

INITIAL = "svc-20261006T120000-aaaa"
RELEASE = "svc-20261006T120500-bbbb"


class RepositoryTest(unittest.TestCase):
    """Releases in a throwaway repository, isolated from any git configuration."""

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

    def commit(self, subject: str, change_id: str, files: dict[str, str]) -> None:
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-F", "-", stdin=f"{subject}\n\nChange-Id: {change_id}\n")

    def release(self, version: str, *entries: tuple[str, str]) -> None:
        """Commit the note for version: entries and its own, in the type table's order."""
        lines = [f"# {version}", "", "Released 2026-10-06.", ""]
        listed = sorted((*entries, (RELEASE, "build")), key=lambda e: TYPES.index(e[1]))
        for change_id, change_type in listed:
            lines += [f"- {change_id} {change_type}: why", "  - What changed: what"]
        self.commit(f"build: release {version}", RELEASE,
                    {f"release-notes/{version}.md": "\n".join(lines) + "\n"})

    def check(self, version: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            status = main([version, "--root", str(self.root)])
        return status, out.getvalue()


class FirstReleaseTest(RepositoryTest):
    def setUp(self):
        super().setUp()
        self.commit("chore: initial commit", INITIAL, {"README.md": "x"})

    def test_first_release_is_checked_over_the_whole_history_at_0_1_0(self):
        self.release("0.1.0", (INITIAL, "chore"))
        status, out = self.check("0.1.0")
        self.assertEqual(status, 0, out)

    def test_first_release_at_any_other_version_is_a_problem(self):
        self.release("0.2.0", (INITIAL, "chore"))
        status, out = self.check("0.2.0")
        self.assertEqual(status, 1, out)
        self.assertIn("0.1.0", out)


class LaterReleaseTest(RepositoryTest):
    def setUp(self):
        super().setUp()
        self.commit("chore: initial commit", INITIAL, {"README.md": "x"})
        self.git("tag", "v0.1.0")
        self.commit("fix: mend x", "svc-20261006T121000-cccc", {"src/x.py": "x"})

    def test_later_release_implies_its_version_from_the_previous_tag(self):
        self.release("0.1.1", ("svc-20261006T121000-cccc", "fix"))
        status, out = self.check("0.1.1")
        self.assertEqual(status, 0, out)

    def test_later_release_at_another_version_is_a_problem(self):
        self.release("0.2.0", ("svc-20261006T121000-cccc", "fix"))
        status, out = self.check("0.2.0")
        self.assertEqual(status, 1, out)
        self.assertIn("imply 0.1.1", out)


class AfterAPreReleaseTest(RepositoryTest):
    def test_the_previous_release_is_the_final_one_not_its_pre_release(self):
        # git's version sort ranks v1.0.0-beta.1 above v1.0.0 unless told otherwise.
        self.commit("chore: initial commit", INITIAL, {"README.md": "x"})
        self.git("tag", "v1.0.0-beta.1")
        self.commit("fix: mend x", "svc-20261006T121000-cccc", {"src/x.py": "x"})
        self.git("tag", "v1.0.0")
        self.commit("fix: mend y", "svc-20261006T121500-dddd", {"src/y.py": "y"})
        self.release("1.0.1", ("svc-20261006T121500-dddd", "fix"))
        status, out = self.check("1.0.1")
        self.assertEqual(status, 0, out)
        self.assertIn("v1.0.0..HEAD", out)


if __name__ == "__main__":
    unittest.main()

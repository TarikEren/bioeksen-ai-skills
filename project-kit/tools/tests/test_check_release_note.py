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
from tests.repository import MonorepoTest

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


ALL = "(affects bio-inventory, bio-sdk, bio-softop)"
CREATED = "bio-software-20261008T100000-aaaa"  # MonorepoTest's initial commit


class UnitReleaseTest(MonorepoTest):
    """A release unit's release in a monorepo, per release-notes.md, Release units."""

    def setUp(self):
        super().setUp()
        self.minted = 0

    def change(self, subject: str, software: str, files: dict[str, str],
               footer: str = "") -> str:
        """Commit a change under a fresh Change-Id carrying software, and return the id."""
        self.minted += 1
        change_id = f"{software}-20261008T11{self.minted:04d}-{self.minted:04x}"
        self.commit(f"{subject}\n\n{footer}Change-Id: {change_id}\n", files)
        return change_id

    def release(self, unit_dir: str, software: str, version: str,
                *entries: tuple[str, str, str]) -> None:
        """Commit the unit's note: (change id, type, reason) entries and its own."""
        own = self.change(f"build: release {version}", software, {})
        listed = sorted((*entries, (own, "build", "why")),
                        key=lambda e: (0 if e[1].endswith("!") else 1,
                                       TYPES.index(e[1].split("(")[0].rstrip("!"))))
        lines = [f"# {version}", "", "Released 2026-10-08.", ""]
        for change_id, change_type, reason in listed:
            lines += [f"- {change_id} {change_type}: {reason}", "  - What changed: what"]
        # The note goes in by amending the release commit, so its id stays its own.
        self.write({f"{unit_dir}/release-notes/{version}.md": "\n".join(lines) + "\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "--amend", "--no-edit")

    def check(self, release: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            status = main([release, "--root", str(self.root)])
        return status, out.getvalue()

    def first_inventory_release(self) -> None:
        page = self.change("feat(ui): add a page", "bio-inventory",
                           {"apps/bio-inventory/app/page.tsx": "y"})
        self.change("fix(web): mend a page", "bio-softop",
                    {"apps/bio-softop/web/app/page.tsx": "y"})
        lock = self.change("build: refresh the lockfile", "bio-software",
                           {"pnpm-lock.yaml": "lockfileVersion: '9.1'\n"})
        self.release("apps/bio-inventory", "bio-inventory", "0.1.0",
                     (CREATED, "chore", f"why {ALL}"), (page, "feat(ui)", "why"),
                     (lock, "build", f"why {ALL}"))

    def test_a_units_first_release_lists_the_commits_that_reached_it_and_no_others(self):
        self.first_inventory_release()
        status, out = self.check("bio-inventory/v0.1.0")
        self.assertEqual(status, 0, out)

    def test_an_entry_minted_with_the_monorepos_id_names_the_units_it_affects(self):
        lock = self.change("build: refresh the lockfile", "bio-software",
                           {"pnpm-lock.yaml": "lockfileVersion: '9.1'\n"})
        self.release("apps/bio-inventory", "bio-inventory", "0.1.0",
                     (CREATED, "chore", f"why {ALL}"), (lock, "build", "why"))
        status, out = self.check("bio-inventory/v0.1.0")
        self.assertEqual(status, 1, out)
        self.assertIn(lock, out)
        self.assertIn("affects", out)

    def test_a_breaking_commit_breaks_only_the_unit_its_scope_names(self):
        self.git("tag", "bio-sdk/v0.1.0", self.initial)
        self.first_inventory_release()
        self.git("tag", "bio-inventory/v0.1.0")
        # Another unit's tag is never this unit's previous release.
        self.git("tag", "bio-softop/v0.3.0")
        rename = self.change("feat(bio-sdk)!: rename createLogger", "bio-software",
                             {"packages/bio-sdk/sdk/index.ts": "y",
                              "apps/bio-inventory/app/page.tsx": "z"},
                             "BREAKING CHANGE: createLogger is now logger.\n")
        self.release("apps/bio-inventory", "bio-inventory", "0.1.1",
                     (rename, "feat(bio-sdk)!", f"BREAKING CHANGE: renamed {ALL}"))
        status, out = self.check("bio-inventory/v0.1.1")
        self.assertEqual(status, 0, out)
        self.assertIn("bio-inventory/v0.1.0..HEAD", out)

        lock = [line.split()[1] for line in
                (self.root / "apps/bio-inventory/release-notes/0.1.0.md")
                .read_text(encoding="utf-8").splitlines()
                if line.startswith("- bio-software-") and "build" in line][0]
        self.release("packages/bio-sdk", "bio-sdk", "0.2.0",
                     (rename, "feat(bio-sdk)!", f"BREAKING CHANGE: renamed {ALL}"),
                     (lock, "build", f"why {ALL}"))
        status, out = self.check("bio-sdk/v0.2.0")
        self.assertEqual(status, 0, out)

    def test_a_breaking_commit_does_not_bump_a_unit_it_does_not_name(self):
        self.first_inventory_release()
        self.git("tag", "bio-inventory/v0.1.0")
        rename = self.change("feat(bio-sdk)!: rename createLogger", "bio-software",
                             {"packages/bio-sdk/sdk/index.ts": "y"},
                             "BREAKING CHANGE: createLogger is now logger.\n")
        self.release("apps/bio-inventory", "bio-inventory", "0.2.0",
                     (rename, "feat(bio-sdk)!", f"BREAKING CHANGE: renamed {ALL}"))
        status, out = self.check("bio-inventory/v0.2.0")
        self.assertEqual(status, 1, out)
        self.assertIn("imply 0.1.1", out)

    def test_a_monorepos_release_names_its_unit(self):
        with self.assertRaises(SystemExit) as raised:
            self.check("0.1.0")
        self.assertIn("{software-id}/v{version}", str(raised.exception))

    def test_a_unit_that_does_not_exist_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            self.check("bio-nothing/v0.1.0")
        self.assertIn("bio-nothing", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

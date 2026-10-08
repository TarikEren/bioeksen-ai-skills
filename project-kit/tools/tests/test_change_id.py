"""Minting a change identifier, through the kit's wrapper of the skill's script."""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from change_id import CHANGE_ID, Attribution, attribution, main, mint, software_id
from tests.repository import ALL_UNITS, MonorepoTest, RepositoryTest, package


class MintTest(unittest.TestCase):
    def test_timestamp_is_utc_plus_three(self):
        minted = mint("auth-service", datetime(2026, 10, 5, 9, 0, 0, tzinfo=timezone.utc))
        self.assertTrue(minted.startswith("auth-service-20261005T120000-"), minted)

    def test_timestamp_rolls_over_to_the_next_day(self):
        minted = mint("auth-service", datetime(2026, 10, 5, 22, 30, 0, tzinfo=timezone.utc))
        self.assertTrue(minted.startswith("auth-service-20261006T013000-"), minted)

    def test_minted_identifier_matches_the_format_and_carries_no_z(self):
        minted = mint("auth-service")
        parsed = CHANGE_ID.match(minted)
        self.assertIsNotNone(parsed, minted)
        self.assertFalse(parsed["timestamp"].endswith("Z"), minted)

    def test_two_identifiers_minted_together_differ(self):
        moment = datetime(2026, 10, 5, 9, 0, 0, tzinfo=timezone.utc)
        self.assertNotEqual(mint("x", moment), mint("x", moment))


class FormatTest(unittest.TestCase):
    def test_identifier_minted_before_utc_plus_three_is_still_accepted(self):
        self.assertIsNotNone(CHANGE_ID.match("bioeksen-sds-20260929T132418Z-e830"))

    def test_explicit_offset_is_rejected(self):
        self.assertIsNone(CHANGE_ID.match("bioeksen-sds-20261005T120000+0300-ab12"))

    def test_short_random_tail_is_rejected(self):
        self.assertIsNone(CHANGE_ID.match("bioeksen-sds-20261005T120000-ab1"))


class SoftwareIdTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / ".bioeksen").mkdir()
        self.file = self.root / ".bioeksen" / "software-id"

    def test_reads_the_stored_id_ignoring_surrounding_whitespace_and_crlf(self):
        self.file.write_bytes(b"bio-kys\r\n")
        self.assertEqual(software_id(self.root), "bio-kys")

    def test_missing_file_refuses_to_guess(self):
        self.file.parent.rmdir()
        with self.assertRaises(SystemExit) as raised:
            software_id(self.root)
        self.assertIn("never guessed", str(raised.exception))

    def test_empty_file_refuses_to_guess(self):
        self.file.write_text("\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            software_id(self.root)

    def test_malformed_id_is_refused(self):
        self.file.write_text("Bio KYS\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            software_id(self.root)
        self.assertIn("not a software id", str(raised.exception))


class AttributionTest(MonorepoTest):
    """Which release units a staged change affects, per release-notes.md, Release units."""

    def staged(self, files: dict[str, str]) -> Attribution:
        self.stage(files)
        return attribution(self.root)

    def assertAttributed(self, files: dict[str, str], software: str,
                         affects: tuple[str, ...] = (), packages: tuple[str, ...] = ()):
        self.assertEqual(self.staged(files), Attribution(software, affects, packages, True))

    def test_a_change_inside_one_app_carries_that_apps_id(self):
        self.assertAttributed({"apps/bio-inventory/app/page.tsx": "y"}, "bio-inventory")

    def test_an_app_of_several_packages_is_one_unit(self):
        self.assertAttributed({"apps/bio-softop/worker/index.ts": "y",
                               "apps/bio-softop/db/schema.prisma": "y"}, "bio-softop")

    def test_a_package_inside_a_unit_reaches_every_unit_that_depends_on_it(self):
        # error-codes is bio-sdk's own, and reaches both apps through sdk. It is
        # in a unit's directory, so no Changes-Package trailer names it.
        self.assertAttributed({"packages/bio-sdk/error-codes/index.ts": "y"},
                              "bio-software", ALL_UNITS)

    def test_a_shared_package_one_app_depends_on_carries_that_apps_id(self):
        self.assertAttributed({"packages/ui/index.ts": "y"}, "bio-inventory")

    def test_a_shared_package_several_apps_depend_on_names_the_package(self):
        self.assertAttributed({"packages/eslint-config/index.js": "y"}, "bio-software",
                              ("bio-inventory", "bio-softop"), ("@bioeksen/eslint-config",))

    def test_dev_dependencies_count(self):
        self.assertAttributed({"packages/tsconfig/base.json": "{ }"}, "bio-inventory")

    def test_the_generator_reaches_bio_softop_through_its_worker(self):
        self.assertAttributed({"tooling/create-app/index.ts": "y"}, "bio-softop")

    def test_a_root_build_file_affects_every_unit(self):
        for name in ("turbo.json", "package.json", "pnpm-workspace.yaml", ".npmrc",
                     "tsconfig.base.json"):
            with self.subTest(name):
                self.git("reset", "-q", "--hard")
                content = (self.root / name).read_text(encoding="utf-8")
                self.assertAttributed({name: content + "\n"}, "bio-software", ALL_UNITS)

    def test_the_lockfile_alone_affects_every_unit(self):
        self.assertAttributed({"pnpm-lock.yaml": "lockfileVersion: '9.1'\n"}, "bio-software",
                              ALL_UNITS)

    def test_the_lockfile_belongs_to_the_units_whose_package_json_changes(self):
        self.assertAttributed({"pnpm-lock.yaml": "lockfileVersion: '9.1'\n",
                               "apps/bio-inventory/package.json":
                                   package("bio-inventory", "@bioeksen/sdk")},
                              "bio-inventory")

    def test_a_change_no_unit_reaches_carries_the_monorepos_id(self):
        self.assertAttributed({".claude/settings.json": "{ }", "README.md": "y",
                               ".forgejo/workflows/ci.yml": "name: ci2\n"}, "bio-software")

    def test_a_package_no_unit_depends_on_is_named_without_affects(self):
        self.assertAttributed({"tooling/lint/package.json": package("@bioeksen/lint"),
                               "tooling/lint/index.ts": "x"},
                              "bio-software", (), ("@bioeksen/lint",))

    def test_a_directory_the_workspace_excludes_is_no_package(self):
        # packages/*/* matches it, and !**/fixtures/** takes it out again.
        self.assertAttributed({"packages/eslint-config/fixtures/package.json":
                                   package("eslint-fixture")},
                              "bio-software", ("bio-inventory", "bio-softop"),
                              ("@bioeksen/eslint-config",))

    def test_several_apps_changed_directly_name_no_package(self):
        self.assertAttributed({"apps/bio-inventory/app/page.tsx": "y",
                               "apps/bio-softop/web/app/page.tsx": "y"},
                              "bio-software", ("bio-inventory", "bio-softop"))

    def test_a_new_app_with_its_lockfile_entry_carries_the_new_id(self):
        self.assertAttributed({"apps/bio-orders/.bioeksen/software-id": "bio-orders\n",
                               "apps/bio-orders/package.json":
                                   package("bio-orders", "@bioeksen/sdk"),
                               "apps/bio-orders/app/page.tsx": "x",
                               "pnpm-lock.yaml": "lockfileVersion: '9.1'\n"}, "bio-orders")

    def test_a_deleted_root_build_file_still_affects_every_unit(self):
        self.git("rm", "-q", "turbo.json")
        self.assertEqual(attribution(self.root),
                         Attribution("bio-software", ALL_UNITS, (), True))

    def test_trailers_are_affects_then_changes_package(self):
        self.assertEqual(Attribution("bio-software", ("a", "b"), ("@x/p",), True).trailers(),
                         ["Affects: a", "Affects: b", "Changes-Package: @x/p"])

    def test_the_script_prints_the_change_id_then_its_trailers(self):
        self.stage({"packages/eslint-config/index.js": "y"})
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--root", str(self.root)]), 0)
        lines = out.getvalue().splitlines()
        self.assertTrue(CHANGE_ID.match(lines[0]) and lines[0].startswith("bio-software-"),
                        lines)
        self.assertEqual(lines[1:], ["Affects: bio-inventory", "Affects: bio-softop",
                                     "Changes-Package: @bioeksen/eslint-config"])

    def test_a_missing_root_id_refuses_to_guess(self):
        self.git("rm", "-q", "--cached", ".bioeksen/software-id")
        with self.assertRaises(SystemExit) as raised:
            attribution(self.root)
        self.assertIn("never guessed", str(raised.exception))

    def test_a_malformed_unit_id_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            self.staged({"apps/bio-inventory/.bioeksen/software-id": "Bio Inventory\n"})
        self.assertIn("not a software id", str(raised.exception))

    def test_a_unit_inside_another_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            self.staged({"apps/bio-softop/web/.bioeksen/software-id": "bio-web\n"})
        self.assertIn("inside", str(raised.exception))

    def test_an_unreadable_package_json_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            self.staged({"packages/ui/package.json": "{ not json"})
        self.assertIn("packages/ui/package.json", str(raised.exception))


class SingleServiceTest(RepositoryTest):
    def test_a_repository_holding_one_service_prints_only_its_id(self):
        self.commit("chore: initial commit\n", {".bioeksen/software-id": "auth-service\n",
                                                "src/a.py": "x"})
        self.stage({"src/a.py": "y"})
        self.assertEqual(attribution(self.root), Attribution("auth-service"))
        out = io.StringIO()
        with redirect_stdout(out):
            main(["--root", str(self.root)])
        self.assertEqual(len(out.getvalue().splitlines()), 1)
        self.assertTrue(out.getvalue().startswith("auth-service-"))


if __name__ == "__main__":
    unittest.main()

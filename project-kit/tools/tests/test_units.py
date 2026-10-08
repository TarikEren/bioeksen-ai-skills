"""units.py: release units as of a commit already made."""
import unittest

from change_id import Attribution
from tests.repository import ALL_UNITS, MonorepoTest, RepositoryTest
from units import commit_attribution, holding_units, predates_monorepo, release_units


class CommitAttributionTest(MonorepoTest):
    def test_a_commit_is_attributed_against_its_first_parent(self):
        self.commit("feat(ui): x\n", {"apps/bio-softop/web/app/page.tsx": "y"})
        sha = self.commit("feat(ui): y\n", {"packages/ui/index.ts": "y"})
        self.assertEqual(commit_attribution(self.root, sha),
                         Attribution("bio-inventory", (), (), True))

    def test_the_first_commit_is_attributed_against_nothing(self):
        found = commit_attribution(self.root, self.initial)
        self.assertEqual(found.software_id, "bio-software")
        self.assertEqual(found.affects, ALL_UNITS)
        self.assertEqual(found.packages, ("@bioeksen/create-app", "@bioeksen/eslint-config",
                                          "@bioeksen/tsconfig", "@bioeksen/ui"))

    def test_the_units_are_those_of_the_commits_own_tree(self):
        sha = self.commit("feat: add bio-orders\n",
                          {"apps/bio-orders/.bioeksen/software-id": "bio-orders\n"})
        self.assertEqual(release_units(self.root, sha)["apps/bio-orders"], "bio-orders")
        self.assertNotIn("apps/bio-orders", release_units(self.root, self.initial))
        self.assertEqual(commit_attribution(self.root, sha).software_id, "bio-orders")


class ImportedHistoryTest(RepositoryTest):
    def test_a_commit_from_before_the_monorepo_is_not_attributed_but_held(self):
        # A history moved in with git filter-repo: an app's own id file, no root one.
        sha = self.commit("fix: mend x\n", {"apps/bio-kys/.bioeksen/software-id": "bio-kys\n",
                                            "apps/bio-kys/src/x.ts": "x"})
        self.assertTrue(predates_monorepo(self.root, sha))
        self.assertIsNone(commit_attribution(self.root, sha))
        self.assertEqual(holding_units(self.root, sha), ("bio-kys",))

    def test_an_empty_commit_from_before_the_monorepo_belongs_to_its_history(self):
        # It changes no path, but the history it came in with is one unit's.
        self.commit("init\n", {"apps/bio-kys/.bioeksen/software-id": "bio-kys\n"})
        sha = self.commit("chore: an empty commit\n", {})
        self.assertEqual(holding_units(self.root, sha), ("bio-kys",))


class SingleServiceTest(RepositoryTest):
    def test_a_repository_holding_one_service_gives_every_commit_its_id(self):
        self.write({".bioeksen/software-id": "auth-service\n"})
        sha = self.commit("chore: initial commit\n", {"src/a.py": "x"})
        self.assertEqual(commit_attribution(self.root, sha), Attribution("auth-service"))
        self.assertFalse(predates_monorepo(self.root, sha))
        self.assertEqual(release_units(self.root, sha), {})


if __name__ == "__main__":
    unittest.main()

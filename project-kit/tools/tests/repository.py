"""A throwaway git repository for the tools' tests, and a monorepo to fill it with."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def package(name: str, *deps: str, dev: tuple[str, ...] = ()) -> str:
    """A package.json on the given workspace packages, and on one that is not."""
    return json.dumps({"name": name, "private": True,
                       "dependencies": {**{dep: "workspace:*" for dep in deps},
                                        "zod": "4.1.12"},
                       "devDependencies": {dep: "workspace:^" for dep in dev}})


# bio-software as spec §12 lays it out: two apps, one of them three packages
# under one id; the published bio-sdk unit, whose sdk depends on its
# error-codes; shared packages; the generator, which bio-softop's worker
# depends on; and the root's own files.
MONOREPO = {
    ".bioeksen/software-id": "bio-software\n",
    "package.json": json.dumps({"name": "bio-software", "private": True}),
    "pnpm-workspace.yaml": ("# the workspace\npackages:\n  - \"apps/*\"\n  - 'apps/*/*'\n"
                            "  - packages/*   # shared\n  - packages/*/*\n  - tooling/*\n"
                            "  - '!**/fixtures/**'\n"),
    "pnpm-lock.yaml": "lockfileVersion: '9.0'\n",
    "turbo.json": "{}",
    "tsconfig.base.json": "{}",
    ".npmrc": "@bioeksen:registry=https://forge.example.invalid/\n",
    ".claude/settings.json": "{}",
    ".forgejo/workflows/ci.yml": "name: ci\n",
    "README.md": "x",
    "apps/bio-inventory/.bioeksen/software-id": "bio-inventory\n",
    "apps/bio-inventory/package.json": package("bio-inventory", "@bioeksen/sdk", "@bioeksen/ui",
                                               dev=("@bioeksen/eslint-config",
                                                    "@bioeksen/tsconfig")),
    "apps/bio-inventory/app/page.tsx": "x",
    "apps/bio-softop/.bioeksen/software-id": "bio-softop\n",
    "apps/bio-softop/web/package.json": package("@bio-softop/web", "@bioeksen/sdk",
                                                "@bio-softop/db",
                                                dev=("@bioeksen/eslint-config",)),
    "apps/bio-softop/web/app/page.tsx": "x",
    "apps/bio-softop/worker/package.json": package("@bio-softop/worker", "@bio-softop/db",
                                                   "@bioeksen/create-app"),
    "apps/bio-softop/worker/index.ts": "x",
    "apps/bio-softop/db/package.json": package("@bio-softop/db"),
    "apps/bio-softop/db/schema.prisma": "x",
    "packages/bio-sdk/.bioeksen/software-id": "bio-sdk\n",
    "packages/bio-sdk/release-notes/.gitkeep": "",
    "packages/bio-sdk/sdk/package.json": package("@bioeksen/sdk", "@bioeksen/error-codes"),
    "packages/bio-sdk/sdk/index.ts": "x",
    "packages/bio-sdk/error-codes/package.json": package("@bioeksen/error-codes"),
    "packages/bio-sdk/error-codes/index.ts": "x",
    "packages/bio-sdk/task-spec/package.json": package("@bioeksen/task-spec"),
    "packages/bio-sdk/task-spec/index.ts": "x",
    "packages/ui/package.json": package("@bioeksen/ui"),
    "packages/ui/index.ts": "x",
    "packages/ui/fixtures/package.json": package("ui-fixture"),
    "packages/eslint-config/package.json": package("@bioeksen/eslint-config"),
    "packages/eslint-config/index.js": "x",
    "packages/tsconfig/package.json": package("@bioeksen/tsconfig"),
    "packages/tsconfig/base.json": "{}",
    "tooling/create-app/package.json": package("@bioeksen/create-app"),
    "tooling/create-app/index.ts": "x",
}

ALL_UNITS = ("bio-inventory", "bio-sdk", "bio-softop")


class RepositoryTest(unittest.TestCase):
    """A repository isolated from any git configuration on the machine."""

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

    def write(self, files: dict[str, str]) -> None:
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def stage(self, files: dict[str, str]) -> None:
        """Write the files and stage every change in the working tree."""
        self.write(files)
        self.git("add", "-A")

    def commit(self, message: str, files: dict[str, str]) -> str:
        """Commit the files with the message, and return the new commit's hash."""
        self.stage(files)
        self.git("commit", "-q", "--allow-empty", "-F", "-", stdin=message)
        return self.git("rev-parse", "HEAD").strip()


class MonorepoTest(RepositoryTest):
    """A repository whose first commit is the MONOREPO tree."""

    def setUp(self):
        super().setUp()
        self.initial = self.commit("chore: create bio-software\n\n"
                                   "Change-Id: bio-software-20261008T100000-aaaa\n", MONOREPO)

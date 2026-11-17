"""sds-project's fact reader, as an installed plugin carries it."""
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "plugins" / "bioeksen-sds" / "skills" / "sds-project" / "scripts" / "read_facts.py"

FACTS = {
    "software-id": "bio-inventory",
    "git-provider": "github",
    "identity-provider": "entra-id",
    "log-aggregator": "present",
    "bio-softop": "none",
    "test-order": "tests-first",
}


def load():
    """The plugin's script as a fresh module, wherever the plugin is installed."""
    spec = importlib.util.spec_from_file_location("sds_read_facts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FactsTest(unittest.TestCase):
    """A repository with every fact recorded at its root, to change one at a time."""

    def setUp(self):
        self.module = load()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "repo"
        (self.root / ".git").mkdir(parents=True)
        for fact, value in FACTS.items():
            self.record(self.root, fact, value)

    def record(self, where: Path, fact: str, value: str) -> None:
        folder = where / ".bioeksen"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / fact).write_text(value + "\n", encoding="utf-8")

    def read(self, *args: str, path: Path | None = None) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            status = self.module.main(["--path", str(path or self.root), *args])
        return status, out.getvalue()

    def test_every_fact_recorded(self):
        status, out = self.read()
        self.assertEqual(status, 0, out)
        for fact, value in FACTS.items():
            self.assertIn(f"{fact}={value}", out)

    def test_a_missing_fact_is_not_run(self):
        (self.root / ".bioeksen" / "test-order").unlink()
        status, out = self.read()
        self.assertEqual(status, 2, out)
        self.assertIn("test-order", out)
        self.assertIn("missing", out)

    def test_a_value_outside_the_choices(self):
        self.record(self.root, "git-provider", "forgejo")
        status, out = self.read()
        self.assertEqual(status, 1, out)
        self.assertIn("forgejo", out)
        self.assertIn("github", out)

    def test_a_software_id_in_the_wrong_format(self):
        self.record(self.root, "software-id", "Bio Inventory")
        status, out = self.read()
        self.assertEqual(status, 1, out)
        self.assertIn("software-id", out)

    def test_the_nearest_file_above_the_path_wins(self):
        unit = self.root / "apps" / "web"
        self.record(unit, "test-order", "implementation-first")
        status, out = self.read("test-order", path=unit / "src")
        self.assertEqual(status, 0, out)
        self.assertIn("test-order=implementation-first", out)

    def test_nothing_above_the_repository_is_read(self):
        (self.root / ".bioeksen" / "bio-softop").unlink()
        self.record(self.root.parent, "bio-softop", "present")
        status, out = self.read("bio-softop")
        self.assertEqual(status, 2, out)

    def test_only_the_facts_asked_for(self):
        status, out = self.read("log-aggregator")
        self.assertEqual(status, 0, out)
        self.assertEqual(out.strip(), "log-aggregator=present")

    def test_an_unknown_fact_is_not_run(self):
        status, out = self.read("favourite-colour")
        self.assertEqual(status, 2, out)
        self.assertIn("favourite-colour", out)


if __name__ == "__main__":
    unittest.main()

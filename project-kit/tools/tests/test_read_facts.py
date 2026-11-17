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
    "test-order": "tests-first",
}

NOT_USED = "Status: not used\nAnswered by: Deniz Örnek\n"
AGGREGATOR = ("Status: used\n"
              "Service: bio-logs\n"
              "Purpose: Keeps every app's log records, searched and alerted on in Grafana\n"
              "Reached by: stdout, collected by Grafana Alloy\n"
              "Interface: https://git.example.com/bio-software/apps/bio-logs/README.md\n"
              "Delivery: collected\n"
              "Retention: meets\n"
              "Answered by: Deniz Örnek\n"
              "\n"
              "Labels are the record's id, type and severity.\n")


def load():
    """The plugin's script as a fresh module, wherever the plugin is installed."""
    spec = importlib.util.spec_from_file_location("sds_read_facts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectCase(unittest.TestCase):
    """A repository with every fact and service recorded at its root, to change one at a time."""

    def setUp(self):
        self.module = load()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "repo"
        (self.root / ".git").mkdir(parents=True)
        for fact, value in FACTS.items():
            self.record(self.root, fact, value)
        self.service(self.root, "log-aggregator", NOT_USED)

    def record(self, where: Path, fact: str, value: str) -> None:
        folder = where / ".bioeksen"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / fact).write_text(value + "\n", encoding="utf-8")

    def service(self, where: Path, capability: str, text: str) -> None:
        folder = where / ".bioeksen" / "services"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{capability}.md").write_text(text, encoding="utf-8")

    def read(self, *args: str, path: Path | None = None) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            status = self.module.main(["--path", str(path or self.root), *args])
        return status, out.getvalue()


class FactsTest(ProjectCase):
    """The single-value facts under .bioeksen/."""

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
        (self.root / ".bioeksen" / "test-order").unlink()
        self.record(self.root.parent, "test-order", "tests-first")
        status, out = self.read("test-order")
        self.assertEqual(status, 2, out)

    def test_only_the_facts_asked_for(self):
        status, out = self.read("test-order")
        self.assertEqual(status, 0, out)
        self.assertEqual(out.strip(), "test-order=tests-first")

    def test_bio_softop_is_not_a_fact(self):
        status, out = self.read("bio-softop")
        self.assertEqual(status, 2, out)
        self.assertIn("not a fact", out)

    def test_the_log_aggregator_is_a_service_not_a_fact(self):
        status, out = self.read("log-aggregator")
        self.assertEqual(status, 2, out)
        self.assertIn("not a fact", out)

    def test_an_unknown_fact_is_not_run(self):
        status, out = self.read("favourite-colour")
        self.assertEqual(status, 2, out)
        self.assertIn("favourite-colour", out)


class ServicesTest(ProjectCase):
    """The services under .bioeksen/services/, each determined, then learned."""

    def test_a_service_not_used_needs_its_status_and_who_answered(self):
        status, out = self.read()
        self.assertEqual(status, 0, out)
        self.assertIn("services/log-aggregator=not used", out)

    def test_a_used_service_with_every_field(self):
        self.service(self.root, "log-aggregator", AGGREGATOR)
        status, out = self.read("services/log-aggregator")
        self.assertEqual(status, 0, out)
        self.assertEqual(out.strip(), "services/log-aggregator=used")

    def test_a_used_service_missing_a_field(self):
        self.service(self.root, "log-aggregator", AGGREGATOR.replace("Interface: ", "Docs: "))
        status, out = self.read()
        self.assertEqual(status, 1, out)
        self.assertIn("Interface", out)

    def test_a_status_outside_the_choices(self):
        self.service(self.root, "log-aggregator", NOT_USED.replace("not used", "maybe"))
        status, out = self.read()
        self.assertEqual(status, 1, out)
        self.assertIn("maybe", out)

    def test_who_answered_is_required(self):
        self.service(self.root, "log-aggregator", "Status: not used\n")
        status, out = self.read()
        self.assertEqual(status, 1, out)
        self.assertIn("Answered by", out)

    def test_an_undetermined_log_aggregator_is_not_run(self):
        (self.root / ".bioeksen" / "services" / "log-aggregator.md").unlink()
        status, out = self.read()
        self.assertEqual(status, 2, out)
        self.assertIn("services/log-aggregator", out)
        self.assertIn("missing", out)

    def test_any_other_service_is_read_and_checked(self):
        self.service(self.root, "email", "Status: used\nService: bio-email\nAnswered by: Deniz\n")
        status, out = self.read()
        self.assertEqual(status, 1, out)
        self.assertIn("services/email", out)
        self.assertIn("Purpose", out)

    def test_a_units_own_service_wins(self):
        unit = self.root / "apps" / "web"
        self.service(unit, "log-aggregator", AGGREGATOR)
        status, out = self.read("services/log-aggregator", path=unit)
        self.assertEqual(status, 0, out)
        self.assertEqual(out.strip(), "services/log-aggregator=used")

    def test_a_capability_name_in_the_wrong_format(self):
        status, out = self.read("services/Log Aggregator")
        self.assertEqual(status, 2, out)
        self.assertIn("not a capability", out)


if __name__ == "__main__":
    unittest.main()

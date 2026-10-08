"""sds-testing's conformance check, as an installed plugin carries it."""
import importlib.util
import io
import sys
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "plugins" / "bioeksen-sds" / "skills" / "sds-testing" / "scripts" / "check_service.py"
sys.path.insert(0, str(REPO / "project-kit" / "conformance"))

from stub_service import DEFAULT_TOKEN, serve  # noqa: E402


def load(name: str = "sds_check_service"):
    """The plugin's script as a fresh module, wherever the plugin is installed."""
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(module, *args: str) -> tuple[int, str]:
    out = io.StringIO()
    with redirect_stdout(out):
        status = module.main(list(args))
    return status, out.getvalue()


class AgainstTheStubTest(unittest.TestCase):
    def setUp(self):
        self.module = load()
        server = serve(port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        self.url = f"http://127.0.0.1:{server.server_address[1]}"

    def test_a_conforming_service_passes_every_check(self):
        status, out = run(self.module, "--base-url", self.url, "--operator-token",
                          DEFAULT_TOKEN)
        self.assertEqual(status, 0, out)
        self.assertNotIn("NOT RUN", out)

    def test_checks_skipped_without_an_operator_token_are_not_run_not_passed(self):
        with mock.patch.dict("os.environ", {"BIOEKSEN_OPERATOR_TOKEN": ""}):
            status, out = run(self.module, "--base-url", self.url)
        self.assertEqual(status, 2, out)
        self.assertIn("NOT RUN", out)
        self.assertNotIn("FAIL", out)


class NotRunTest(unittest.TestCase):
    def test_a_service_that_cannot_be_reached_is_not_run(self):
        status, out = run(load(), "--base-url", "http://127.0.0.1:9")
        self.assertEqual(status, 2, out)
        self.assertIn("not run", out)

    def test_missing_packages_are_named_and_the_check_is_not_run(self):
        with mock.patch.dict(sys.modules, {"jsonschema": None}):
            module = load("sds_check_service_without_jsonschema")
        status, out = run(module, "--base-url", "http://127.0.0.1:9")
        self.assertEqual(status, 2, out)
        self.assertIn("pip install -r", out)
        self.assertIn("requirements.txt", out)


if __name__ == "__main__":
    unittest.main()

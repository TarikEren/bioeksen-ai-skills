"""sds-project's comment checker, as an installed plugin carries it."""
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = (REPO / "plugins" / "bioeksen-sds" / "skills" / "sds-project" / "scripts"
          / "check_comments.py")


def load():
    """The plugin's script as a fresh module, wherever the plugin is installed."""
    spec = importlib.util.spec_from_file_location("sds_check_comments", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def words(count: int) -> str:
    return " ".join(["word"] * count)


class CommentTest(unittest.TestCase):
    def setUp(self):
        self.module = load()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def check(self, *paths: Path) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            status = self.module.main([str(path) for path in paths])
        return status, out.getvalue()

    def assertClean(self, path: Path) -> None:
        status, out = self.check(path)
        self.assertEqual(status, 0, out)

    def assertFinding(self, path: Path, *expected: str) -> None:
        status, out = self.check(path)
        self.assertEqual(status, 1, out)
        for text in expected:
            self.assertIn(text, out)


class BlockLengthTest(CommentTest):
    def test_five_line_comments_in_a_row(self):
        self.assertClean(self.write("a.ts", "".join(f"// {words(3)}\n" for _ in range(5))
                                    + "const a = 1;\n"))

    def test_six_line_comments_in_a_row(self):
        path = self.write("a.ts", "const a = 1;\n" + "".join(f"// {words(3)}\n" for _ in range(6)))
        self.assertFinding(path, "a.ts:2", "6 lines")

    def test_a_doc_comment_of_six_lines(self):
        path = self.write("a.ts", "/**\n" + " * one\n" * 4 + " */\nexport const a = 1;\n")
        self.assertFinding(path, "a.ts:1", "6 lines")

    def test_a_doc_comment_of_five_lines(self):
        self.assertClean(self.write("a.ts", "/**\n" + " * one\n" * 3 + " */\nexport const a = 1;\n"))

    def test_hash_comments_in_python(self):
        path = self.write("a.py", "".join(f"# {words(2)}\n" for _ in range(6)) + "a = 1\n")
        self.assertFinding(path, "a.py:1", "6 lines")

    def test_dash_comments_in_sql(self):
        path = self.write("a.sql", "".join(f"-- {words(2)}\n" for _ in range(6)) + "SELECT 1;\n")
        self.assertFinding(path, "a.sql:1", "6 lines")

    def test_an_html_comment_of_six_lines(self):
        path = self.write("a.html", "<!--\n" + "one\n" * 4 + "-->\n<p>a</p>\n")
        self.assertFinding(path, "a.html:1", "6 lines")

    def test_code_between_comments_ends_a_block(self):
        text = "".join(f"// {words(2)}\n" for _ in range(3)) + "const a = 1;\n" \
            + "".join(f"// {words(2)}\n" for _ in range(3))
        self.assertClean(self.write("a.ts", text))


class LineLengthTest(CommentTest):
    def test_a_line_of_30_words(self):
        self.assertClean(self.write("a.ts", f"// {words(30)}\nconst a = 1;\n"))

    def test_a_line_of_31_words(self):
        self.assertFinding(self.write("a.ts", f"const a = 1;\n// {words(31)}\n"),
                           "a.ts:2", "31 words")

    def test_a_trailing_comment_of_31_words(self):
        self.assertFinding(self.write("a.ts", f"const a = 1; // {words(31)}\n"),
                           "a.ts:1", "31 words")

    def test_a_long_line_inside_a_doc_comment(self):
        self.assertFinding(self.write("a.ts", f"/**\n * {words(31)}\n */\nconst a = 1;\n"),
                           "a.ts:2", "31 words")


class NotACommentTest(CommentTest):
    def test_slashes_inside_a_string(self):
        text = "".join(f'const u{n} = "https://example.com/{n}";\n' for n in range(8))
        self.assertClean(self.write("a.ts", text))

    def test_a_hash_inside_a_python_string(self):
        text = "".join(f'colour{n} = "#ffffff"\n' for n in range(8))
        self.assertClean(self.write("a.py", text))

    def test_a_file_of_no_known_language_is_skipped(self):
        self.assertClean(self.write("notes.txt", "".join("// prose\n" for _ in range(9))))


class PathsTest(CommentTest):
    def test_a_directory_is_walked(self):
        self.write("src/a.ts", "".join("// one\n" for _ in range(6)))
        self.assertFinding(self.root / "src", "a.ts:1")

    def test_dependencies_are_skipped(self):
        self.write("node_modules/lib/a.js", "".join("// one\n" for _ in range(9)))
        status, out = self.check(self.root)
        self.assertEqual(status, 0, out)

    def test_a_path_that_does_not_exist_is_not_run(self):
        status, out = self.check(self.root / "nowhere")
        self.assertEqual(status, 2, out)
        self.assertIn("NOT RUN", out)


if __name__ == "__main__":
    unittest.main()

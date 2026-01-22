import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from greyalien import __main__ as greyalien_main
from greyalien import cli as greyalien_cli
from greyalien.cli import run_source, run_path


class CliTests(unittest.TestCase):
    def test_run_source_success_output(self):
        source = 'fn main() { print("hi"); }'
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_source(source, "test.grl", check_only=False)
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "hi")

    def test_type_error_diagnostic(self):
        source = "fn main() { let x: Int = true; }"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_source(source, "test.grl", check_only=False)
        output = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("Type error:", output)
        self.assertIn("test.grl:1:13", output)

    def test_parse_error_diagnostic(self):
        source = "fn main() { let x = 1 }"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_source(source, "test.grl", check_only=False)
        output = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("Parse error:", output)
        self.assertIn("Missing ';' after let statement", output)

    def test_parse_error_multiple(self):
        source = "fn main() { let x = 1 } fn other() { let y = 2 }"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_source(source, "test.grl", check_only=False, all_errors=True)
        output = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertGreaterEqual(output.count("Parse error:"), 2)

    def test_lex_error_diagnostic(self):
        source = "fn main() { @ }"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_source(source, "test.grl", check_only=False)
        output = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("Lex error:", output)
        self.assertIn("Unexpected character", output)

    def test_runtime_error_diagnostic(self):
        source = "fn main() { return 1 / 0; }"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_source(source, "test.grl", check_only=False)
        output = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("Runtime error:", output)
        self.assertIn("Division by zero", output)

    def test_run_source_check_only(self):
        source = "fn main() { return 0; }"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_source(source, "test.grl", check_only=True)
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "")

    def test_run_source_runtime_error_without_loc(self):
        source = "fn helper() { return 1; }"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_source(source, "test.grl", check_only=False)
        output = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("Runtime error:", output)
        self.assertIn("No 'main' function defined", output)

    def test_run_path_load_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = base / "main.grl"
            path.write_text("import missing;\nfn main() { return 0; }\n", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = run_path(str(path), check_only=False)
            output = buf.getvalue()
            self.assertEqual(code, 1)
            self.assertIn("Import error:", output)

    def test_run_path_parse_error_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = base / "main.grl"
            path.write_text(
                "fn main() { let x = 1 }\nfn other() { let y = 2 }\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = run_path(str(path), check_only=False, all_errors=True)
            output = buf.getvalue()
            self.assertEqual(code, 1)
            self.assertGreaterEqual(output.count("Parse error:"), 2)

    def test_cli_main_help(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = greyalien_cli.main(["--help"])
        output = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Usage:", output)

    def test_cli_main_all_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = base / "main.grl"
            path.write_text(
                "fn main() { let x = 1 }\nfn other() { let y = 2 }\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = greyalien_cli.main(["--all-errors", str(path)])
            output = buf.getvalue()
            self.assertEqual(code, 1)
            self.assertGreaterEqual(output.count("Parse error:"), 2)

    def test_help_flag(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = greyalien_main.main(["--help"])
        output = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Usage:", output)


if __name__ == "__main__":
    unittest.main()

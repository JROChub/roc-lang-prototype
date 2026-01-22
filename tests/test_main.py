import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from greyalien import __main__ as greyalien_main
from greyalien import __version__


class MainEntryTests(unittest.TestCase):
    def test_main_no_args_shows_help(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = greyalien_main.main([])
        self.assertEqual(code, 1)
        self.assertIn("Usage:", buf.getvalue())

    def test_main_version_flag(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = greyalien_main.main(["--version"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), __version__)

    def test_main_run_check_ir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "main.grl"
            path.write_text("fn main() { return 1; }\n", encoding="utf-8")

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = greyalien_main.main(["run", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual(buf.getvalue().strip(), "")

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = greyalien_main.main(["check", str(path)])
            self.assertEqual(code, 0)

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = greyalien_main.main(["ir", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("fn main", buf.getvalue())

    def test_main_run_missing_arg(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = greyalien_main.main(["run"])
        self.assertEqual(code, 1)
        self.assertIn("Usage:", buf.getvalue())

    def test_main_all_errors_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.grl"
            path.write_text(
                "fn main() { let x = 1 }\nfn other() { let y = 2 }\n",
                encoding="utf-8",
            )

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = greyalien_main.main(["--all-errors", str(path)])
            self.assertEqual(code, 1)
            output = buf.getvalue()
            self.assertGreaterEqual(output.count("Parse error:"), 2)

    def test_main_direct_file_arg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "main.grl"
            path.write_text("fn main() { return 1; }\n", encoding="utf-8")

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = greyalien_main.main([str(path)])
            self.assertEqual(code, 0)

    def test_main_uses_sys_argv(self):
        original = greyalien_main.sys.argv
        try:
            greyalien_main.sys.argv = ["greyalien", "--help"]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = greyalien_main.main()
            self.assertEqual(code, 0)
            self.assertIn("Usage:", buf.getvalue())
        finally:
            greyalien_main.sys.argv = original


if __name__ == "__main__":
    unittest.main()

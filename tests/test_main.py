import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from roc import __main__ as roc_main
from roc import __version__


class MainEntryTests(unittest.TestCase):
    def test_main_no_args_shows_help(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = roc_main.main([])
        self.assertEqual(code, 1)
        self.assertIn("Usage:", buf.getvalue())

    def test_main_version_flag(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = roc_main.main(["--version"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), __version__)

    def test_main_run_check_ir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "main.roc"
            path.write_text("fn main() { return 1; }\n", encoding="utf-8")

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = roc_main.main(["run", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual(buf.getvalue().strip(), "")

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = roc_main.main(["check", str(path)])
            self.assertEqual(code, 0)

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = roc_main.main(["ir", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("fn main", buf.getvalue())

    def test_main_run_missing_arg(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = roc_main.main(["run"])
        self.assertEqual(code, 1)
        self.assertIn("Usage:", buf.getvalue())


if __name__ == "__main__":
    unittest.main()

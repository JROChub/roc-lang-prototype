import contextlib
import io
import unittest

from roc import __main__ as roc_main
from roc.cli import run_source


class CliTests(unittest.TestCase):
  def test_run_source_success_output(self):
    source = 'fn main() { print("hi"); }'
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      code = run_source(source, "test.roc", check_only=False)
    self.assertEqual(code, 0)
    self.assertEqual(buf.getvalue().strip(), "hi")

  def test_type_error_diagnostic(self):
    source = "fn main() { let x: Int = true; }"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      code = run_source(source, "test.roc", check_only=False)
    output = buf.getvalue()
    self.assertEqual(code, 1)
    self.assertIn("Type error:", output)
    self.assertIn("test.roc:1:13", output)

  def test_parse_error_diagnostic(self):
    source = "fn main() { let x = 1 }"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      code = run_source(source, "test.roc", check_only=False)
    output = buf.getvalue()
    self.assertEqual(code, 1)
    self.assertIn("Parse error:", output)
    self.assertIn("Expected SEMICOL", output)

  def test_lex_error_diagnostic(self):
    source = "fn main() { @ }"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      code = run_source(source, "test.roc", check_only=False)
    output = buf.getvalue()
    self.assertEqual(code, 1)
    self.assertIn("Lex error:", output)
    self.assertIn("Unexpected character", output)

  def test_runtime_error_diagnostic(self):
    source = "fn main() { return 1 / 0; }"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      code = run_source(source, "test.roc", check_only=False)
    output = buf.getvalue()
    self.assertEqual(code, 1)
    self.assertIn("Runtime error:", output)
    self.assertIn("Division by zero", output)

  def test_help_flag(self):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      code = roc_main.main(["--help"])
    output = buf.getvalue()
    self.assertEqual(code, 0)
    self.assertIn("Usage:", output)


if __name__ == "__main__":
  unittest.main()

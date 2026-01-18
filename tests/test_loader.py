import tempfile
import unittest
from pathlib import Path

from roc.interpreter import Interpreter
from roc.loader import LoadError, load_program
from roc.typechecker import check_program


class LoaderTests(unittest.TestCase):
  def test_imports_merge_definitions(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "math_utils.roc").write_text(
        "module math_utils\n"
        "fn add(a, b) { return a + b; }\n",
        encoding="utf-8",
      )
      (base / "main.roc").write_text(
        "import math_utils;\n"
        "fn main() { return add(2, 3); }\n",
        encoding="utf-8",
      )

      result = load_program(str(base / "main.roc"))
      check_program(result.program)
      interp = Interpreter(result.program)
      self.assertEqual(interp.execute(), 5)

  def test_missing_import_reports_error(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "main.roc").write_text(
        "import missing;\n"
        "fn main() { return 0; }\n",
        encoding="utf-8",
      )

      with self.assertRaises(LoadError) as ctx:
        load_program(str(base / "main.roc"))
      self.assertIn("Module 'missing' not found", ctx.exception.message)


if __name__ == "__main__":
  unittest.main()

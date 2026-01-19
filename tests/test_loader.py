import tempfile
import unittest
from pathlib import Path

from roc.interpreter import Interpreter
from roc.loader import LoadError, load_program
from roc.typechecker import TypeError, check_program


class LoaderTests(unittest.TestCase):
  def test_imports_merge_definitions(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "math_utils.roc").write_text(
        "module math_utils\n"
        "export { add };\n"
        "fn add(a, b) { return a + b; }\n",
        encoding="utf-8",
      )
      (base / "main.roc").write_text(
        "import math_utils;\n"
        "fn main() { return math_utils.add(2, 3); }\n",
        encoding="utf-8",
      )

      result = load_program(str(base / "main.roc"))
      check_program(result.program, modules=result.modules, root_module=result.root_module)
      interp = Interpreter(result.program, modules=result.modules, root_module=result.root_module)
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

  def test_import_requires_namespace(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "math_utils.roc").write_text(
        "module math_utils\n"
        "export { add };\n"
        "fn add(a, b) { return a + b; }\n",
        encoding="utf-8",
      )
      (base / "main.roc").write_text(
        "import math_utils;\n"
        "fn main() { return add(2, 3); }\n",
        encoding="utf-8",
      )

      result = load_program(str(base / "main.roc"))
      with self.assertRaises(TypeError):
        check_program(result.program, modules=result.modules, root_module=result.root_module)

  def test_unexported_symbol_is_hidden(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "math_utils.roc").write_text(
        "module math_utils\n"
        "fn add(a, b) { return a + b; }\n",
        encoding="utf-8",
      )
      (base / "main.roc").write_text(
        "import math_utils;\n"
        "fn main() { return math_utils.add(2, 3); }\n",
        encoding="utf-8",
      )

      result = load_program(str(base / "main.roc"))
      with self.assertRaises(TypeError) as ctx:
        check_program(result.program, modules=result.modules, root_module=result.root_module)
      self.assertIn("has no export", str(ctx.exception))

  def test_import_alias_namespace(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "math_utils.roc").write_text(
        "module math_utils\n"
        "export { add };\n"
        "fn add(a, b) { return a + b; }\n",
        encoding="utf-8",
      )
      (base / "main.roc").write_text(
        "import math_utils as math;\n"
        "fn main() { return math.add(2, 3); }\n",
        encoding="utf-8",
      )

      result = load_program(str(base / "main.roc"))
      check_program(result.program, modules=result.modules, root_module=result.root_module)
      interp = Interpreter(result.program, modules=result.modules, root_module=result.root_module)
      self.assertEqual(interp.execute(), 5)

  def test_module_qualified_type_annotation(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "colors.roc").write_text(
        "module colors\n"
        "export { Color, Red };\n"
        "enum Color { Red }\n",
        encoding="utf-8",
      )
      (base / "main.roc").write_text(
        "import colors;\n"
        "fn main() { let c: colors.Color = colors.Red; return 0; }\n",
        encoding="utf-8",
      )

      result = load_program(str(base / "main.roc"))
      check_program(result.program, modules=result.modules, root_module=result.root_module)

  def test_module_qualified_type_requires_export(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "colors.roc").write_text(
        "module colors\n"
        "enum Color { Red }\n",
        encoding="utf-8",
      )
      (base / "main.roc").write_text(
        "import colors;\n"
        "fn main() { let c: colors.Color = 0; return 0; }\n",
        encoding="utf-8",
      )

      result = load_program(str(base / "main.roc"))
      with self.assertRaises(TypeError) as ctx:
        check_program(result.program, modules=result.modules, root_module=result.root_module)
      self.assertIn("has no export", str(ctx.exception))

  def test_module_variant_requires_export(self):
    with tempfile.TemporaryDirectory() as tmpdir:
      base = Path(tmpdir)
      (base / "colors.roc").write_text(
        "module colors\n"
        "enum Color { Red }\n",
        encoding="utf-8",
      )
      (base / "main.roc").write_text(
        "import colors;\n"
        "fn main() { return colors.Red; }\n",
        encoding="utf-8",
      )

      result = load_program(str(base / "main.roc"))
      with self.assertRaises(TypeError) as ctx:
        check_program(result.program, modules=result.modules, root_module=result.root_module)
      self.assertIn("has no export", str(ctx.exception))


if __name__ == "__main__":
  unittest.main()

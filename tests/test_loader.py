import tempfile
import unittest
from pathlib import Path

from greyalien.interpreter import Interpreter
from greyalien.loader import LoadError, load_program
from greyalien.typechecker import TypeError, check_program


class LoaderTests(unittest.TestCase):
    def test_imports_merge_definitions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "math_utils.grl").write_text(
                "module math_utils\nexport { add };\nfn add(a, b) { return a + b; }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import math_utils;\nfn main() { return math_utils.add(2, 3); }\n",
                encoding="utf-8",
            )

            result = load_program(str(base / "main.grl"))
            check_program(result.program, modules=result.modules, root_module=result.root_module)
            interp = Interpreter(
                result.program, modules=result.modules, root_module=result.root_module
            )
            self.assertEqual(interp.execute(), 5)

    def test_missing_import_reports_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "main.grl").write_text(
                "import missing;\nfn main() { return 0; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("Module 'missing' not found", ctx.exception.message)

    def test_import_requires_namespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "math_utils.grl").write_text(
                "module math_utils\nexport { add };\nfn add(a, b) { return a + b; }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import math_utils;\nfn main() { return add(2, 3); }\n",
                encoding="utf-8",
            )

            result = load_program(str(base / "main.grl"))
            with self.assertRaises(TypeError):
                check_program(
                    result.program, modules=result.modules, root_module=result.root_module
                )

    def test_unexported_symbol_is_hidden(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "math_utils.grl").write_text(
                "module math_utils\nfn add(a, b) { return a + b; }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import math_utils;\nfn main() { return math_utils.add(2, 3); }\n",
                encoding="utf-8",
            )

            result = load_program(str(base / "main.grl"))
            with self.assertRaises(TypeError) as ctx:
                check_program(
                    result.program, modules=result.modules, root_module=result.root_module
                )
            self.assertIn("has no export", str(ctx.exception))

    def test_import_alias_namespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "math_utils.grl").write_text(
                "module math_utils\nexport { add };\nfn add(a, b) { return a + b; }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import math_utils as math;\nfn main() { return math.add(2, 3); }\n",
                encoding="utf-8",
            )

            result = load_program(str(base / "main.grl"))
            check_program(result.program, modules=result.modules, root_module=result.root_module)
            interp = Interpreter(
                result.program, modules=result.modules, root_module=result.root_module
            )
            self.assertEqual(interp.execute(), 5)

    def test_module_qualified_type_annotation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "colors.grl").write_text(
                "module colors\nexport { Color, Red };\nenum Color { Red }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import colors;\nfn main() { let c: colors.Color = colors.Red; return 0; }\n",
                encoding="utf-8",
            )

            result = load_program(str(base / "main.grl"))
            check_program(result.program, modules=result.modules, root_module=result.root_module)

    def test_module_qualified_type_requires_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "colors.grl").write_text(
                "module colors\nenum Color { Red }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import colors;\nfn main() { let c: colors.Color = 0; return 0; }\n",
                encoding="utf-8",
            )

            result = load_program(str(base / "main.grl"))
            with self.assertRaises(TypeError) as ctx:
                check_program(
                    result.program, modules=result.modules, root_module=result.root_module
                )
            self.assertIn("has no export", str(ctx.exception))

    def test_module_variant_requires_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "colors.grl").write_text(
                "module colors\nenum Color { Red }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import colors;\nfn main() { return colors.Red; }\n",
                encoding="utf-8",
            )

            result = load_program(str(base / "main.grl"))
            with self.assertRaises(TypeError) as ctx:
                check_program(
                    result.program, modules=result.modules, root_module=result.root_module
                )
            self.assertIn("has no export", str(ctx.exception))

    def test_import_cycle_reports_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "a.grl").write_text(
                "module a\nimport b;\nfn main() { return 0; }\n",
                encoding="utf-8",
            )
            (base / "b.grl").write_text(
                "module b\nimport a;\nfn helper() { return 1; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "a.grl"))
            self.assertIn("Import cycle detected", ctx.exception.message)

    def test_import_module_name_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "foo.grl").write_text(
                "module bar\nfn helper() { return 1; }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import foo;\nfn main() { return 0; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("does not match import", ctx.exception.message)

    def test_export_duplicate_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "main.grl").write_text(
                "export { add, add };\nfn add() { return 1; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("already listed", ctx.exception.message)

    def test_export_unknown_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "main.grl").write_text(
                "export { Missing };\nfn main() { return 0; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("Unknown export", ctx.exception.message)

    def test_export_ambiguous_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "main.grl").write_text(
                "export { Foo };\nenum Foo { Bar }\nfn Foo() { return 1; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("ambiguous", ctx.exception.message)

    def test_import_alias_duplicate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "util.grl").write_text(
                "module util\nexport { add };\nfn add(a, b) { return a + b; }\n",
                encoding="utf-8",
            )
            (base / "other.grl").write_text(
                "module other\nexport { sub };\nfn sub(a, b) { return a - b; }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import util as math;\nimport other as math;\nfn main() { return 0; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("already used", ctx.exception.message)

    def test_import_alias_conflicts_with_local(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "util.grl").write_text(
                "module util\nexport { add };\nfn add(a, b) { return a + b; }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import util as math;\nfn math() { return 1; }\nfn main() { return 0; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("conflicts with local definition", ctx.exception.message)

    def test_imported_module_lex_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "bad.grl").write_text(
                "fn main() { @ }\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import bad;\nfn main() { return 0; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("Lex error", ctx.exception.kind)

    def test_imported_module_parse_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "bad.grl").write_text(
                "fn main() { let x = 1\n",
                encoding="utf-8",
            )
            (base / "main.grl").write_text(
                "import bad;\nfn main() { return 0; }\n",
                encoding="utf-8",
            )

            with self.assertRaises(LoadError) as ctx:
                load_program(str(base / "main.grl"))
            self.assertIn("Parse error", ctx.exception.kind)


if __name__ == "__main__":
    unittest.main()

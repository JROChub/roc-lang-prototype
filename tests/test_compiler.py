import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from greyalien.compiler import __main__ as compiler_main
from greyalien.compiler import frontend
from greyalien.compiler.ir import IRFunction, IREnum, IRModule
from greyalien.lexer import tokenize
from greyalien.parser import Parser


def parse_program(source: str):
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse_program()


class CompilerCliTests(unittest.TestCase):
    def test_compiler_no_args(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = compiler_main.main([])
        self.assertEqual(code, 1)
        self.assertIn("Usage:", buf.getvalue())

    def test_compiler_uses_sys_argv(self):
        original = compiler_main.sys.argv
        try:
            compiler_main.sys.argv = ["greyalien.compiler", "--help"]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = compiler_main.main()
            self.assertEqual(code, 0)
            self.assertIn("Usage:", buf.getvalue())
        finally:
            compiler_main.sys.argv = original

    def test_compiler_help(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = compiler_main.main(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("Usage:", buf.getvalue())

    def test_compiler_missing_file(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = compiler_main.main(["missing.grl"])
        self.assertEqual(code, 1)
        output = buf.getvalue()
        self.assertIn("Import error", output)
        self.assertIn("Unable to read module", output)

    def test_compiler_type_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "main.grl"
            path.write_text("fn main() { let x: Int = true; }\n", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = compiler_main.main([str(path)])
        self.assertEqual(code, 1)
        self.assertIn("Type error", buf.getvalue())

    def test_compiler_success_ir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "main.grl"
            path.write_text("fn main() { return 1; }\n", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = compiler_main.main([str(path)])
        self.assertEqual(code, 0)
        self.assertIn("fn main", buf.getvalue())

    def test_compiler_lookup_source_default(self):
        source, path = compiler_main._lookup_source(None, "main.grl", {"main.grl": "fn main() {}"})
        self.assertEqual(path, "main.grl")
        self.assertIn("fn main", source)


class CompilerFrontendTests(unittest.TestCase):
    def test_lower_program_covers_constructs(self):
        source = "\n".join(
            [
                "import util as u;",
                "export { Color, Red, Blue, add, paint };",
                "enum Color { Red, Blue(Int) }",
                "fn add(a: Int, b: Int) -> Int {",
                "  let x: Int = a + b;",
                "  set x = x + 1;",
                "  for i in 0..=3 by 1 { break; continue; }",
                "  while true { break; }",
                "  return x;",
                "}",
                "fn paint(c: colors.Color) -> String { return \"paint\"; }",
                "fn main() {",
                "  let rec = {x: 1, y: 2};",
                "  let xs = [1, 2];",
                "  let _ = rec.x;",
                "  let _ = xs[0];",
                "  let _ = -1;",
                "  let _ = 1 * 2;",
                "  let _ = if true { 1; } else { 2; };",
                "  let _ = match 1 { 1 => { 1; } _ => { 0; } };",
                "  let _ = match \"hi\" { \"hi\" => { 1; } _ => { 0; } };",
                "  let _ = match true { true => { 1; } false => { 0; } };",
                "  let _ = match Red { Red => { 1; } _ => { 0; } };",
                "  let _ = match Blue(3) { Blue(x) => { x; } _ => { 0; } };",
                "  return add(1, 2);",
                "}",
            ]
        )
        program = parse_program(source)
        mod = frontend.lower_program(program)

        self.assertEqual(mod.imports, ["util as u"])
        self.assertEqual(mod.exports, [["Color", "Red", "Blue", "add", "paint"]])
        self.assertEqual(mod.enums[0].variants, ["Red", "Blue(Int)"])

        add_fn = next(fn for fn in mod.functions if fn.name == "add")
        self.assertEqual(add_fn.params[0], "a: Int")
        self.assertEqual(add_fn.return_type, "Int")

        paint_fn = next(fn for fn in mod.functions if fn.name == "paint")
        self.assertEqual(paint_fn.params[0], "c: colors.Color")
        self.assertEqual(paint_fn.return_type, "String")

    def test_ir_pretty_formats_module(self):
        mod = IRModule(
            imports=["util"],
            exports=[["main"]],
            enums=[IREnum(name="Color", variants=["Red"])],
            functions=[IRFunction(name="main", params=[], body=["return 1;"])],
        )
        output = mod.pretty()
        self.assertIn("import util;", output)
        self.assertIn("export { main };", output)
        self.assertIn("enum Color { Red }", output)
        self.assertIn("fn main()", output)


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
import unittest

from roc.lexer import tokenize
from roc.parser import Parser
from roc.interpreter import Interpreter, RuntimeError


def build_interpreter(source: str) -> Interpreter:
  tokens = tokenize(source)
  program = Parser(tokens).parse_program()
  return Interpreter(program)


class InterpreterTests(unittest.TestCase):
  def test_return_arithmetic(self):
    interp = build_interpreter("fn main() { return 40 + 2; }")
    self.assertEqual(interp.execute(), 42)

  def test_unary_minus(self):
    interp = build_interpreter("fn main() { return -(1 + 2); }")
    self.assertEqual(interp.execute(), -3)

  def test_logical_ops(self):
    interp = build_interpreter("fn main() { return true && !false || false; }")
    self.assertEqual(interp.execute(), True)

  def test_short_circuit_and(self):
    interp = build_interpreter("fn main() { return false && (1 / 0 == 0); }")
    self.assertEqual(interp.execute(), False)

  def test_short_circuit_or(self):
    interp = build_interpreter("fn main() { return true || (1 / 0 == 0); }")
    self.assertEqual(interp.execute(), True)

  def test_set_and_while(self):
    source = "fn main() { let i = 0; while i < 3 { set i = i + 1; } return i; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 3)

  def test_for_loop_exclusive(self):
    source = "fn main() { let sum = 0; for i in 0..4 { set sum = sum + i; } return sum; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 6)

  def test_for_loop_inclusive(self):
    source = "fn main() { let sum = 0; for i in 1..=3 { set sum = sum + i; } return sum; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 6)

  def test_for_loop_descending(self):
    source = "fn main() { let sum = 0; for i in 3..0 { set sum = sum + i; } return sum; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 6)

  def test_for_loop_step(self):
    source = "fn main() { let sum = 0; for i in 0..10 by 2 { set sum = sum + i; } return sum; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 20)

  def test_for_loop_step_zero(self):
    interp = build_interpreter("fn main() { for i in 0..5 by 0 { print(i); } }")
    with self.assertRaises(RuntimeError) as ctx:
      interp.execute()
    self.assertIn("for step cannot be zero", str(ctx.exception))

  def test_break_continue(self):
    source = (
      "fn main() {"
      "  let total = 0;"
      "  for i in 0..10 {"
      "    if i == 2 {"
      "      continue;"
      "    } else if i == 4 {"
      "      break;"
      "    } else {"
      "      set total = total + i;"
      "    };"
      "  }"
      "  return total;"
      "}"
    )
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 1 + 3)

  def test_break_continue_in_while(self):
    source = (
      "fn main() {"
      "  let i = 0;"
      "  let total = 0;"
      "  while true {"
      "    set i = i + 1;"
      "    if i == 2 { continue; } else { 0; };"
      "    set total = total + i;"
      "    if i == 3 { break; } else { 0; };"
      "  }"
      "  return total;"
      "}"
    )
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 1 + 3)

  def test_break_outside_loop(self):
    interp = build_interpreter("fn main() { break; }")
    with self.assertRaises(RuntimeError) as ctx:
      interp.execute()
    self.assertIn("break used outside", str(ctx.exception))

  def test_continue_outside_loop(self):
    interp = build_interpreter("fn main() { continue; }")
    with self.assertRaises(RuntimeError) as ctx:
      interp.execute()
    self.assertIn("continue used outside", str(ctx.exception))

  def test_print_bool(self):
    interp = build_interpreter("fn main() { print(true); }")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
      interp.execute()
    self.assertEqual(buf.getvalue().strip(), "true")

  def test_division_by_zero(self):
    interp = build_interpreter("fn main() { return 1 / 0; }")
    with self.assertRaises(RuntimeError) as ctx:
      interp.execute()
    self.assertIn("Division by zero", str(ctx.exception))

  def test_mismatched_equality(self):
    interp = build_interpreter('fn main() { return 1 == "1"; }')
    with self.assertRaises(RuntimeError) as ctx:
      interp.execute()
    self.assertIn("matching types", str(ctx.exception))

  def test_if_expression(self):
    source = "fn main() { return if true { 1; } else { 2; }; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 1)

  def test_else_if_expression(self):
    source = "fn main() { return if false { 1; } else if true { 2; } else { 3; }; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 2)

  def test_match_expression(self):
    source = (
      "fn main() {"
      "  let n = 2;"
      "  let label = match n {"
      "    1 => { \"one\"; }"
      "    2 => { \"two\"; }"
      "    _ => { \"other\"; }"
      "  };"
      "  return label;"
      "}"
    )
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), "two")

  def test_match_non_exhaustive(self):
    source = "fn main() { return match 3 { 1 => { 10; } }; }"
    interp = build_interpreter(source)
    with self.assertRaises(RuntimeError) as ctx:
      interp.execute()
    self.assertIn("Non-exhaustive match", str(ctx.exception))

  def test_record_field_access(self):
    source = "fn main() { let p = {x: 1, y: 2}; return p.x + p.y; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 3)

  def test_record_missing_field(self):
    source = "fn main() { let p = {x: 1}; return p.y; }"
    interp = build_interpreter(source)
    with self.assertRaises(RuntimeError) as ctx:
      interp.execute()
    self.assertIn("Record has no field", str(ctx.exception))

  def test_list_index(self):
    source = "fn main() { let xs = [1, 2, 3]; return xs[0] + xs[2]; }"
    interp = build_interpreter(source)
    self.assertEqual(interp.execute(), 4)

  def test_list_index_out_of_bounds(self):
    source = "fn main() { let xs = [1]; return xs[2]; }"
    interp = build_interpreter(source)
    with self.assertRaises(RuntimeError) as ctx:
      interp.execute()
    self.assertIn("out of bounds", str(ctx.exception))


if __name__ == '__main__':
  unittest.main()

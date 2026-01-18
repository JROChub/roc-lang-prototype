import unittest

from roc.lexer import tokenize
from roc.parser import Parser
from roc.typechecker import TypeError, check_program


def parse_program(source: str):
  tokens = tokenize(source)
  parser = Parser(tokens)
  return parser.parse_program()


class TypeCheckerTests(unittest.TestCase):
  def test_valid_program(self):
    program = parse_program("fn main() { let x = 1; return x + 2; }")
    check_program(program)

  def test_string_concat_allows_other_types(self):
    program = parse_program('fn main() { return "x=" + 1; }')
    check_program(program)

  def test_let_annotation_mismatch_reports_loc(self):
    program = parse_program("fn main() { let x: Int = true; }")
    with self.assertRaises(TypeError) as ctx:
      check_program(program)
    self.assertIn("1:13", str(ctx.exception))

  def test_unknown_type_annotation(self):
    program = parse_program("fn main() { let x: Foo = 1; }")
    with self.assertRaises(TypeError) as ctx:
      check_program(program)
    self.assertIn("Unknown type", str(ctx.exception))

  def test_arithmetic_type_error(self):
    program = parse_program("fn main() { return true + 1; }")
    with self.assertRaises(TypeError):
      check_program(program)

  def test_if_condition_type_error(self):
    program = parse_program("fn main() { return if 1 { 2; } else { 3; }; }")
    with self.assertRaises(TypeError):
      check_program(program)

  def test_match_expression(self):
    program = parse_program(
      "fn main() { return match true { true => { 1; } false => { 0; } }; }"
    )
    check_program(program)

  def test_match_pattern_type_error(self):
    program = parse_program(
      "fn main() { return match 1 { \"one\" => { 1; } _ => { 0; } }; }"
    )
    with self.assertRaises(TypeError) as ctx:
      check_program(program)
    self.assertIn("Type mismatch", str(ctx.exception))

  def test_enum_values(self):
    program = parse_program(
      "enum Color { Red, Blue }"
      "fn main() {"
      "  let c: Color = Red;"
      "  return if true { c; } else { Blue; };"
      "}"
    )
    check_program(program)

  def test_enum_match_unknown_variant(self):
    program = parse_program(
      "enum Color { Red }"
      "fn main() {"
      "  return match Red {"
      "    Blue => { 1; }"
      "    _ => { 0; }"
      "  };"
      "}"
    )
    with self.assertRaises(TypeError) as ctx:
      check_program(program)
    self.assertIn("Unknown enum variant", str(ctx.exception))

  def test_for_range_type_error(self):
    program = parse_program("fn main() { for i in true..3 { print(i); } }")
    with self.assertRaises(TypeError):
      check_program(program)

  def test_for_step_type_error(self):
    program = parse_program("fn main() { for i in 0..3 by false { print(i); } }")
    with self.assertRaises(TypeError):
      check_program(program)

  def test_break_outside_loop(self):
    program = parse_program("fn main() { break; }")
    with self.assertRaises(TypeError):
      check_program(program)

  def test_return_inside_expression_block(self):
    source = "fn main() { return if true { return 1; } else { 2; }; }"
    program = parse_program(source)
    with self.assertRaises(TypeError):
      check_program(program)

  def test_function_call_arity(self):
    program = parse_program("fn add(a, b) { return a + b; } fn main() { return add(1); }")
    with self.assertRaises(TypeError):
      check_program(program)

  def test_record_field_access(self):
    program = parse_program("fn main() { let p = {x: 1, y: true}; return p.x; }")
    check_program(program)

  def test_record_unknown_field(self):
    program = parse_program("fn main() { let p = {x: 1}; return p.y; }")
    with self.assertRaises(TypeError) as ctx:
      check_program(program)
    self.assertIn("Unknown field", str(ctx.exception))

  def test_field_access_on_non_record(self):
    program = parse_program("fn main() { let x = 1; return x.y; }")
    with self.assertRaises(TypeError):
      check_program(program)

  def test_list_literal_types(self):
    program = parse_program("fn main() { let xs = [1, 2, 3]; return xs[1]; }")
    check_program(program)

  def test_list_index_type_error(self):
    program = parse_program("fn main() { let xs = [1, 2]; return xs[true]; }")
    with self.assertRaises(TypeError):
      check_program(program)

  def test_index_on_non_list(self):
    program = parse_program("fn main() { let x = 1; return x[0]; }")
    with self.assertRaises(TypeError):
      check_program(program)


if __name__ == '__main__':
  unittest.main()

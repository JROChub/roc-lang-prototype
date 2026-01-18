import unittest

from roc import ast
from roc.lexer import tokenize
from roc.parser import Parser, ParseError


def parse_program(source: str) -> ast.Program:
  tokens = tokenize(source)
  parser = Parser(tokens)
  return parser.parse_program()


class ParserTests(unittest.TestCase):
  def test_bool_literal(self):
    program = parse_program("fn main() { return true; }")
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt, ast.ReturnStmt)
    self.assertIsInstance(stmt.expr, ast.BoolLiteral)

  def test_unary_minus(self):
    program = parse_program("fn main() { return -(1 + 2); }")
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt.expr, ast.UnaryOp)

  def test_unary_not(self):
    program = parse_program("fn main() { return !true; }")
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt.expr, ast.UnaryOp)
    self.assertEqual(stmt.expr.op, '!')

  def test_set_statement(self):
    program = parse_program("fn main() { let x = 1; set x = 2; }")
    stmt = program.functions[0].body.statements[1]
    self.assertIsInstance(stmt, ast.SetStmt)

  def test_for_statement(self):
    program = parse_program("fn main() { for i in 0..3 { print(i); } }")
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt, ast.ForStmt)
    self.assertEqual(stmt.var_name, 'i')
    self.assertFalse(stmt.inclusive)

  def test_for_statement_inclusive(self):
    program = parse_program("fn main() { for i in 0..=3 { print(i); } }")
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt, ast.ForStmt)
    self.assertTrue(stmt.inclusive)

  def test_for_statement_with_step(self):
    program = parse_program("fn main() { for i in 0..10 by 2 { print(i); } }")
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt, ast.ForStmt)
    self.assertIsNotNone(stmt.step)

  def test_enum_definition(self):
    program = parse_program("enum Color { Red, Green } fn main() { return Red; }")
    self.assertEqual(len(program.enums), 1)
    enum_def = program.enums[0]
    self.assertEqual(enum_def.name, "Color")
    self.assertEqual([v.name for v in enum_def.variants], ["Red", "Green"])

  def test_import_definition(self):
    program = parse_program("import util; fn main() { return 1; }")
    self.assertEqual(len(program.imports), 1)
    self.assertEqual(program.imports[0].name, "util")

  def test_type_annotations(self):
    program = parse_program("fn add(a: Int, b: Int) -> Int { return a + b; }")
    fn = program.functions[0]
    self.assertEqual(fn.params[0].type_ann.name, "Int")
    self.assertEqual(fn.params[1].type_ann.name, "Int")
    self.assertEqual(fn.return_type.name, "Int")

  def test_let_type_annotation(self):
    program = parse_program("fn main() { let x: Int = 1; }")
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt, ast.LetStmt)
    self.assertEqual(stmt.type_ann.name, "Int")

  def test_break_continue(self):
    program = parse_program("fn main() { break; continue; }")
    self.assertIsInstance(program.functions[0].body.statements[0], ast.BreakStmt)
    self.assertIsInstance(program.functions[0].body.statements[1], ast.ContinueStmt)

  def test_else_if(self):
    source = "fn main() { return if false { 1; } else if true { 2; } else { 3; }; }"
    program = parse_program(source)
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt.expr, ast.IfExpr)
    else_block = stmt.expr.else_block
    self.assertEqual(len(else_block.statements), 1)
    self.assertIsInstance(else_block.statements[0], ast.ExprStmt)
    self.assertIsInstance(else_block.statements[0].expr, ast.IfExpr)

  def test_record_literal_and_field_access(self):
    source = "fn main() { let p = {x: 1, y: 2}; return p.x; }"
    program = parse_program(source)
    let_stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(let_stmt, ast.LetStmt)
    self.assertIsInstance(let_stmt.expr, ast.RecordLiteral)
    return_stmt = program.functions[0].body.statements[1]
    self.assertIsInstance(return_stmt, ast.ReturnStmt)
    self.assertIsInstance(return_stmt.expr, ast.FieldAccess)

  def test_list_literal_and_index(self):
    source = "fn main() { let xs = [1, 2, 3]; return xs[1]; }"
    program = parse_program(source)
    let_stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(let_stmt.expr, ast.ListLiteral)
    return_stmt = program.functions[0].body.statements[1]
    self.assertIsInstance(return_stmt.expr, ast.IndexExpr)

  def test_match_expression(self):
    source = "fn main() { return match 1 { 1 => { 10; } _ => { 0; } }; }"
    program = parse_program(source)
    stmt = program.functions[0].body.statements[0]
    self.assertIsInstance(stmt.expr, ast.MatchExpr)
    self.assertEqual(len(stmt.expr.arms), 2)

  def test_unclosed_block(self):
    with self.assertRaises(ParseError) as ctx:
      parse_program("fn main() { let x = 1; ")
    self.assertIn("Unclosed block", str(ctx.exception))

  def test_missing_semicolon(self):
    with self.assertRaises(ParseError) as ctx:
      parse_program("fn main() { let x = 1 }")
    self.assertIn("Missing ';' after let statement", str(ctx.exception))

  def test_missing_rparen(self):
    with self.assertRaises(ParseError) as ctx:
      parse_program("fn main() { return (1 + 2; }")
    self.assertIn("Missing ')'", str(ctx.exception))

  def test_missing_rbracket(self):
    with self.assertRaises(ParseError) as ctx:
      parse_program("fn main() { let xs = [1, 2; }")
    self.assertIn("Missing ']'", str(ctx.exception))

  def test_missing_rbrace_before_function(self):
    source = "fn main() { let x = 1; fn other() { return 2; }"
    with self.assertRaises(ParseError) as ctx:
      parse_program(source)
    self.assertIn("Missing '}' before top-level declaration", str(ctx.exception))


if __name__ == '__main__':
  unittest.main()

import unittest

from roc.lexer import LexError, tokenize


class LexerTests(unittest.TestCase):
  def test_invalid_character(self):
    with self.assertRaises(LexError) as ctx:
      tokenize("fn main() { @ }")
    self.assertIn("Unexpected character", str(ctx.exception))

  def test_crlf_normalization(self):
    tokens = tokenize("fn main() {\r\n  print(\"hi\");\r\n}\r\n")
    kinds = [t.kind for t in tokens if t.kind != 'EOF']
    self.assertIn('FN', kinds)

  def test_logical_tokens(self):
    tokens = tokenize("fn main() { return true && !false || false; }")
    ops = [t.value for t in tokens if t.kind == 'OP']
    self.assertIn('&&', ops)
    self.assertIn('||', ops)
    self.assertIn('!', ops)

  def test_range_tokens(self):
    tokens = tokenize("fn main() { for i in 0..=3 by 2 { break; } }")
    ops = [t.value for t in tokens if t.kind == 'OP']
    self.assertIn('..=', ops)

  def test_type_tokens(self):
    tokens = tokenize("fn add(a: Int) -> Int { return a; }")
    kinds = [t.kind for t in tokens]
    self.assertIn('COLON', kinds)
    self.assertIn('ARROW', kinds)

  def test_dot_token(self):
    tokens = tokenize("fn main() { let p = {x: 1}; return p.x; }")
    kinds = [t.kind for t in tokens]
    self.assertIn('DOT', kinds)

  def test_bracket_tokens(self):
    tokens = tokenize("fn main() { let xs = [1, 2]; return xs[0]; }")
    kinds = [t.kind for t in tokens]
    self.assertIn('LBRACKET', kinds)
    self.assertIn('RBRACKET', kinds)


if __name__ == '__main__':
  unittest.main()

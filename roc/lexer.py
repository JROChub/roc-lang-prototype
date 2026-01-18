import re
from dataclasses import dataclass
from typing import List

class LexError(Exception):
  def __init__(self, message: str, line: int, column: int):
    super().__init__(message)
    self.message = message
    self.line = line
    self.column = column

@dataclass
class Token:
  kind: str
  value: str
  line: int
  column: int

TOKEN_SPEC = [
  ('NUMBER',   r'\d+'),
  ('STRING',   r'"(\\.|[^"\\])*"'),
  ('IDENT',    r'[A-Za-z_][A-Za-z0-9_]*'),
  ('COMMENT',  r'//.*'),
  ('ARROW',    r'->'),
  ('FATARROW', r'=>'),
  ('OP',       r'\.\.=|\.\.|==|!=|<=|>=|&&|\|\||[+\-*/<>!]'),
  ('DOT',      r'\.'),
  ('EQUALS',   r'='),
  ('COLON',    r':'),
  ('LBRACE',   r'\{'),
  ('RBRACE',   r'\}'),
  ('LBRACKET', r'\['),
  ('RBRACKET', r'\]'),
  ('LPAREN',   r'\('),
  ('RPAREN',   r'\)'),
  ('COMMA',    r','),
  ('SEMICOL',  r';'),
  ('NEWLINE',  r'\n'),
  ('SKIP',     r'[ \t]+'),
]

MASTER = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC))

KEYWORDS = {
  'module', 'fn', 'let', 'set', 'return', 'if', 'else', 'while', 'match', 'enum',
  'for', 'in', 'by', 'break', 'continue',
  'true', 'false',
}

def normalize_newlines(source: str) -> str:
  return source.replace('\r\n', '\n').replace('\r', '\n')

def tokenize(source: str) -> List[Token]:
  source = normalize_newlines(source)
  tokens: List[Token] = []
  line_num = 1
  line_start = 0
  pos = 0
  length = len(source)

  while pos < length:
    mo = MASTER.match(source, pos)
    if not mo:
      column = pos - line_start + 1
      bad_char = source[pos]
      raise LexError(f"Unexpected character {bad_char!r}", line_num, column)
    kind = mo.lastgroup
    value = mo.group()
    column = pos - line_start + 1
    pos = mo.end()

    if kind == 'NEWLINE':
      line_num += 1
      line_start = pos
      continue
    if kind in ('SKIP', 'COMMENT'):
      continue
    if kind == 'IDENT' and value in KEYWORDS:
      kind = value.upper()
    tokens.append(Token(kind, value, line_num, column))

  tokens.append(Token('EOF', '', line_num, 0))
  return tokens

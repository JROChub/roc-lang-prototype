import sys
from . import ast
from .diagnostics import render_diagnostic
from .lexer import normalize_newlines, tokenize, LexError
from .parser import Parser, ParseError
from .interpreter import Interpreter, RuntimeError
from .typechecker import check_program, TypeError

def run_path(path: str, check_only: bool = False) -> int:
  try:
    with open(path, 'r', encoding='utf-8') as f:
      source = f.read()
  except OSError as e:
    print(f"Error reading {path}: {e}")
    return 1
  return run_source(source, path, check_only=check_only)

def run_source(source: str, path: str, check_only: bool = False) -> int:
  normalized = normalize_newlines(source)
  try:
    tokens = tokenize(normalized)
    parser = Parser(tokens)
    program = parser.parse_program()
    check_program(program)
    if check_only:
      return 0
    interp = Interpreter(program)
    interp.execute()
    return 0
  except LexError as e:
    loc = ast.SourceLoc(line=e.line, column=e.column)
    message = getattr(e, "message", str(e))
    print(render_diagnostic("Lex error", message, normalized, loc, path))
    return 1
  except TypeError as e:
    message = getattr(e, "message", str(e))
    print(render_diagnostic("Type error", message, normalized, e.loc, path))
    return 1
  except ParseError as e:
    message = getattr(e, "message", str(e))
    print(render_diagnostic("Parse error", message, normalized, e.loc, path))
    return 1
  except RuntimeError as e:
    if getattr(e, "loc", None) is not None:
      message = getattr(e, "message", str(e))
      print(render_diagnostic("Runtime error", message, normalized, e.loc, path))
    else:
      print(f"Runtime error: {e}")
    return 1

def main(argv=None):
  if argv is None:
    argv = sys.argv[1:]
  if not argv:
    print("Usage: python -m roc.cli <file.roc>")
    return 1
  if argv[0] in ("--help", "-h", "help"):
    print("Usage: python -m roc.cli <file.roc>")
    return 0
  return run_path(argv[0], check_only=False)

if __name__ == '__main__':
  raise SystemExit(main())

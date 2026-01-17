import sys
from . import ast
from .diagnostics import render_diagnostic
from .lexer import normalize_newlines, tokenize, LexError
from .parser import Parser, ParseError
from .interpreter import Interpreter, RuntimeError
from .typechecker import check_program, TypeError

HELP_TEXT = """Usage: python -m roc.cli [--all-errors] <file.roc>

Options:
  --all-errors  Show all parse errors instead of the first.
"""

def run_path(path: str, check_only: bool = False, all_errors: bool = False) -> int:
  try:
    with open(path, 'r', encoding='utf-8') as f:
      source = f.read()
  except OSError as e:
    print(f"Error reading {path}: {e}")
    return 1
  return run_source(source, path, check_only=check_only, all_errors=all_errors)

def run_source(source: str, path: str, check_only: bool = False, all_errors: bool = False) -> int:
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
    errors = getattr(e, "errors", None)
    if errors and all_errors:
      rendered = [
        render_diagnostic("Parse error", err.message, normalized, err.loc, path)
        for err in errors
      ]
      print("\n\n".join(rendered))
      return 1
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
    print(HELP_TEXT.strip())
    return 1
  all_errors = False
  if "--all-errors" in argv:
    all_errors = True
    argv = [arg for arg in argv if arg != "--all-errors"]
  if argv[0] in ("--help", "-h", "help"):
    print(HELP_TEXT.strip())
    return 0
  return run_path(argv[0], check_only=False, all_errors=all_errors)

if __name__ == '__main__':
  raise SystemExit(main())

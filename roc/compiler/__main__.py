import sys
from .. import ast
from ..diagnostics import render_diagnostic
from ..lexer import normalize_newlines, tokenize, LexError
from ..parser import Parser, ParseError
from ..interpreter import RuntimeError
from ..typechecker import check_program, TypeError
from .frontend import lower_program

def main(argv=None):
  if argv is None:
    argv = sys.argv[1:]
  if not argv:
    print("Usage: python -m roc.compiler <file.roc>")
    return 1
  if argv[0] in ("--help", "-h", "help"):
    print("Usage: python -m roc.compiler <file.roc>")
    return 0
  path = argv[0]
  try:
    with open(path, 'r', encoding='utf-8') as f:
      source = f.read()
  except OSError as e:
    print(f"Error reading {path}: {e}")
    return 1

  normalized = normalize_newlines(source)
  try:
    tokens = tokenize(normalized)
    parser = Parser(tokens)
    program = parser.parse_program()
    check_program(program)
    ir_mod = lower_program(program)
    print(ir_mod.pretty())
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
      print(render_diagnostic("Runtime error during lowering", message, normalized, e.loc, path))
    else:
      print(f"Runtime error during lowering: {e}")
    return 1

if __name__ == "__main__":
  raise SystemExit(main())

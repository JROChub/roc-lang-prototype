import sys
from typing import Optional

from .. import ast
from ..diagnostics import render_diagnostic
from ..interpreter import RuntimeError
from ..loader import LoadError, load_program
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
    result = load_program(path)
    program = result.program
    sources = result.sources
    check_program(program, modules=result.modules, root_module=result.root_module)
    ir_mod = lower_program(program)
    print(ir_mod.pretty())
    return 0
  except LoadError as e:
    print(render_diagnostic(e.kind, e.message, e.source, e.loc, e.path))
    return 1
  except TypeError as e:
    source, path = _lookup_source(e.loc, path, sources)
    message = getattr(e, "message", str(e))
    print(render_diagnostic("Type error", message, source, e.loc, path))
    return 1
  except RuntimeError as e:
    if getattr(e, "loc", None) is not None:
      source, path = _lookup_source(e.loc, path, sources)
      message = getattr(e, "message", str(e))
      print(render_diagnostic("Runtime error during lowering", message, source, e.loc, path))
    else:
      print(f"Runtime error during lowering: {e}")
    return 1


def _lookup_source(loc: Optional[ast.SourceLoc], default_path: str, sources):
  if loc is not None and loc.file:
    source = sources.get(loc.file, "")
    return source or "", loc.file
  return sources.get(default_path, ""), default_path

if __name__ == "__main__":
  raise SystemExit(main())

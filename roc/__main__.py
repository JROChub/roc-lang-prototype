import sys

from . import __version__
from . import cli as roc_cli
from .compiler import __main__ as roc_compiler

HELP_TEXT = """Usage:
  roc <file.roc>
  roc run <file.roc>
  roc check <file.roc>
  roc ir <file.roc>
  roc --version
  roc --help
"""

def main(argv=None):
  if argv is None:
    argv = sys.argv[1:]
  if not argv:
    print(HELP_TEXT.strip())
    return 1
  cmd = argv[0]
  if cmd in ("--help", "-h", "help"):
    print(HELP_TEXT.strip())
    return 0
  if cmd in ("--version", "-V", "version"):
    print(__version__)
    return 0
  if cmd in ("run", "check", "ir"):
    if len(argv) < 2:
      print(f"Usage: python -m roc {cmd} <file.roc>")
      return 1
    path = argv[1]
    if cmd == "run":
      return roc_cli.run_path(path, check_only=False)
    if cmd == "check":
      return roc_cli.run_path(path, check_only=True)
    if cmd == "ir":
      return roc_compiler.main([path])
  return roc_cli.run_path(cmd, check_only=False)


if __name__ == "__main__":
  raise SystemExit(main())

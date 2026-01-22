import sys

from . import __version__
from . import cli as greyalien_cli
from .compiler import __main__ as greyalien_compiler

HELP_TEXT = """Usage:
  greyalien <file.grl>
  greyalien run <file.grl>
  greyalien check <file.grl>
  greyalien ir <file.grl>
  greyalien --all-errors <file.grl>
  greyalien run --all-errors <file.grl>
  greyalien check --all-errors <file.grl>
  greyalien --version
  greyalien --help

Options:
  --all-errors  Show all parse errors instead of the first.
"""


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
    cmd = argv[0]
    if cmd in ("--help", "-h", "help"):
        print(HELP_TEXT.strip())
        return 0
    if cmd in ("--version", "-V", "version"):
        print(__version__)
        return 0
    if cmd in ("run", "check", "ir"):
        if len(argv) < 2:
            print(f"Usage: python -m greyalien {cmd} <file.grl>")
            return 1
        path = argv[1]
        if cmd == "run":
            return greyalien_cli.run_path(path, check_only=False, all_errors=all_errors)
        if cmd == "check":
            return greyalien_cli.run_path(path, check_only=True, all_errors=all_errors)
        if cmd == "ir":
            return greyalien_compiler.main([path])
    return greyalien_cli.run_path(cmd, check_only=False, all_errors=all_errors)


if __name__ == "__main__":
    raise SystemExit(main())

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import ast
from .lexer import normalize_newlines, tokenize, LexError
from .parser import Parser, ParseError


@dataclass
class LoadError(Exception):
  kind: str
  message: str
  loc: Optional[ast.SourceLoc]
  path: Optional[str]
  source: str
  errors: Optional[List[ParseError]] = None


@dataclass
class LoadResult:
  program: ast.Program
  sources: Dict[str, str]


def load_program(path: str) -> LoadResult:
  abs_path = os.path.abspath(path)
  sources: Dict[str, str] = {}
  loaded: Dict[str, ast.Program] = {}
  load_order: List[ast.Program] = []

  def record_load(program: ast.Program):
    load_order.append(program)

  def load_module(
    file_path: str,
    expected_name: Optional[str] = None,
    import_loc: Optional[ast.SourceLoc] = None,
    importer_path: Optional[str] = None,
    importer_source: Optional[str] = None,
    ancestry: Optional[List[str]] = None,
  ) -> ast.Program:
    if ancestry is None:
      ancestry = []
    if file_path in ancestry:
      chain = " -> ".join(ancestry + [file_path])
      raise LoadError(
        kind="Import error",
        message=f"Import cycle detected: {chain}",
        loc=import_loc,
        path=importer_path,
        source=importer_source or "",
      )
    if file_path in loaded:
      program = loaded[file_path]
      if expected_name and program.module_name and program.module_name != expected_name:
        raise LoadError(
          kind="Import error",
          message=(
            f"Module name '{program.module_name}' does not match import '{expected_name}'"
          ),
          loc=import_loc,
          path=importer_path,
          source=importer_source or "",
        )
      return program
    try:
      with open(file_path, "r", encoding="utf-8") as handle:
        raw_source = handle.read()
    except OSError as exc:
      raise LoadError(
        kind="Import error",
        message=f"Unable to read module '{file_path}': {exc}",
        loc=import_loc,
        path=importer_path,
        source=importer_source or "",
      ) from None

    source = normalize_newlines(raw_source)
    sources[file_path] = source
    try:
      tokens = tokenize(source)
    except LexError as exc:
      loc = ast.SourceLoc(line=exc.line, column=exc.column, file=file_path)
      raise LoadError("Lex error", exc.message, loc, file_path, source) from None

    parser = Parser(tokens, source_path=file_path)
    try:
      program = parser.parse_program()
    except ParseError as exc:
      raise LoadError("Parse error", exc.message, exc.loc, file_path, source, errors=exc.errors) from None

    if expected_name and program.module_name and program.module_name != expected_name:
      raise LoadError(
        kind="Import error",
        message=f"Module name '{program.module_name}' does not match import '{expected_name}'",
        loc=import_loc,
        path=importer_path,
        source=importer_source or "",
      )

    loaded[file_path] = program
    base_dir = os.path.dirname(file_path)
    for imp in program.imports:
      import_path = os.path.join(base_dir, f"{imp.name}.roc")
      if not os.path.exists(import_path):
        raise LoadError(
          kind="Import error",
          message=f"Module '{imp.name}' not found (expected {import_path})",
          loc=imp.loc,
          path=file_path,
          source=source,
        )
      load_module(
        import_path,
        expected_name=imp.name,
        import_loc=imp.loc,
        importer_path=file_path,
        importer_source=source,
        ancestry=ancestry + [file_path],
      )
    record_load(program)
    return program

  root_program = load_module(abs_path)

  enums: List[ast.EnumDef] = []
  functions: List[ast.FunctionDef] = []
  for program in load_order:
    enums.extend(program.enums)
    functions.extend(program.functions)

  combined = ast.Program(
    module_name=root_program.module_name,
    functions=functions,
    enums=enums,
    imports=root_program.imports,
  )
  return LoadResult(program=combined, sources=sources)

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import ast
from .lexer import normalize_newlines, tokenize, LexError
from .modules import ModuleExports, ModuleInfo
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
  modules: Dict[str, ModuleInfo]
  root_module: str


def load_program(path: str) -> LoadResult:
  abs_path = os.path.abspath(path)
  sources: Dict[str, str] = {}
  loaded: Dict[str, ast.Program] = {}
  load_order: List[Tuple[ast.Program, str]] = []
  module_names: Dict[str, Optional[str]] = {}

  def record_load(program: ast.Program, file_path: str):
    load_order.append((program, file_path))

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

    module_name = program.module_name or expected_name
    if module_name is None:
      module_name = os.path.splitext(os.path.basename(file_path))[0]
    module_names[file_path] = module_name
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
    record_load(program, file_path)
    return program

  root_program = load_module(abs_path)

  root_module = module_names.get(abs_path)
  if root_module is None:
    root_module = root_program.module_name or os.path.splitext(os.path.basename(abs_path))[0]

  module_exports: Dict[str, ModuleExports] = {}
  module_paths: Dict[str, str] = {}
  for program, file_path in load_order:
    module_name = module_names.get(file_path)
    if module_name is None:
      continue
    existing_path = module_paths.get(module_name)
    if existing_path and existing_path != file_path:
      raise LoadError(
        kind="Import error",
        message=f"Module '{module_name}' already loaded from {existing_path}",
        loc=None,
        path=file_path,
        source=sources.get(file_path, ""),
      )
    module_paths[module_name] = file_path
    functions_by_name = {fn.name: fn for fn in program.functions}
    enums_by_name = {enum_def.name: enum_def for enum_def in program.enums}
    variants: Dict[str, str] = {}
    for enum_def in program.enums:
      for variant in enum_def.variants:
        variants[variant.name] = enum_def.name
    exported_names: List[str] = []
    export_locs: Dict[str, Optional[ast.SourceLoc]] = {}
    if program.exports:
      seen_exports = set()
      for decl in program.exports:
        for name in decl.names:
          if name in seen_exports:
            raise LoadError(
              kind="Export error",
              message=f"Export '{name}' already listed in module '{module_name}'",
              loc=decl.loc,
              path=file_path,
              source=sources.get(file_path, ""),
            )
          seen_exports.add(name)
          export_locs[name] = decl.loc
          exported_names.append(name)
    exported_functions: Dict[str, ast.FunctionDef] = {}
    exported_enums: Dict[str, ast.EnumDef] = {}
    exported_variants: Dict[str, str] = {}
    for name in exported_names:
      matches: List[str] = []
      if name in functions_by_name:
        matches.append("function")
      if name in enums_by_name:
        matches.append("enum")
      if name in variants:
        matches.append("variant")
      if not matches:
        raise LoadError(
          kind="Export error",
          message=f"Unknown export '{name}' in module '{module_name}'",
          loc=export_locs.get(name),
          path=file_path,
          source=sources.get(file_path, ""),
        )
      if len(matches) > 1:
        kinds = ", ".join(matches)
        raise LoadError(
          kind="Export error",
          message=f"Export '{name}' in module '{module_name}' is ambiguous ({kinds})",
          loc=export_locs.get(name),
          path=file_path,
          source=sources.get(file_path, ""),
        )
      if name in functions_by_name:
        exported_functions[name] = functions_by_name[name]
        continue
      if name in enums_by_name:
        exported_enums[name] = enums_by_name[name]
        continue
      exported_variants[name] = variants[name]
    module_exports[module_name] = ModuleExports(
      name=module_name,
      functions=functions_by_name,
      enums=enums_by_name,
      variants=variants,
      exported_functions=exported_functions,
      exported_enums=exported_enums,
      exported_variants=exported_variants,
    )

  module_imports: Dict[str, Dict[str, str]] = {}
  for program, file_path in load_order:
    module_name = module_names.get(file_path)
    if module_name is None:
      continue
    aliases: Dict[str, str] = {}
    exports = module_exports.get(module_name)
    for imp in program.imports:
      alias = imp.alias or imp.name
      if alias in aliases:
        raise LoadError(
          kind="Import error",
          message=f"Import alias '{alias}' already used in module '{module_name}'",
          loc=imp.loc,
          path=file_path,
          source=sources.get(file_path, ""),
        )
      if exports is not None:
        if alias in exports.functions or alias in exports.variants:
          raise LoadError(
            kind="Import error",
            message=f"Import alias '{alias}' conflicts with local definition",
            loc=imp.loc,
            path=file_path,
            source=sources.get(file_path, ""),
          )
      aliases[alias] = imp.name
    module_imports[module_name] = aliases

  modules: Dict[str, ModuleInfo] = {}
  for program, file_path in load_order:
    module_name = module_names.get(file_path)
    if module_name is None:
      continue
    exports = module_exports.get(module_name)
    if exports is None:
      raise LoadError(
        kind="Import error",
        message=f"Module '{module_name}' not loaded",
        loc=None,
        path=file_path,
        source=sources.get(file_path, ""),
      )
    imports = module_imports.get(module_name, {})
    modules[module_name] = ModuleInfo(
      name=module_name,
      program=program,
      path=file_path,
      imports=imports,
      exports=exports,
    )

  return LoadResult(
    program=root_program,
    sources=sources,
    modules=modules,
    root_module=root_module,
  )

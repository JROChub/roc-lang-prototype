from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from . import ast
from .modules import ModuleExports, ModuleInfo


class TypeError(Exception):
  def __init__(self, message: str, loc: Optional[ast.SourceLoc] = None):
    super().__init__(message)
    self.message = message
    self.loc = loc

  def __str__(self) -> str:
    if self.loc is not None:
      return f"{self.loc.line}:{self.loc.column}: {self.message}"
    return self.message


@dataclass(frozen=True)
class SimpleType:
  name: str

  def __str__(self) -> str:
    return self.name


INT = SimpleType("Int")
BOOL = SimpleType("Bool")
STRING = SimpleType("String")
UNIT = SimpleType("Unit")

TypeLike = Union[SimpleType, "TypeVar", "RecordType", "ListType", "EnumType"]


class TypeVar:
  _counter = 0

  def __init__(self, name: Optional[str] = None):
    self.id = TypeVar._counter
    TypeVar._counter += 1
    self.name = name or f"t{self.id}"
    self.instance: Optional[TypeLike] = None

  def __str__(self) -> str:
    resolved = resolve(self)
    if isinstance(resolved, TypeVar):
      return resolved.name
    return str(resolved)


def resolve(t: TypeLike) -> TypeLike:
  if isinstance(t, TypeVar) and t.instance is not None:
    t.instance = resolve(t.instance)
    return t.instance
  return t


@dataclass(frozen=True)
class RecordType:
  fields: Dict[str, TypeLike]

  def __str__(self) -> str:
    parts = ", ".join(f"{name}: {value}" for name, value in self.fields.items())
    return "{" + parts + "}"


@dataclass(frozen=True)
class ListType:
  element: TypeLike

  def __str__(self) -> str:
    return f"[{self.element}]"


@dataclass(frozen=True)
class EnumType:
  name: str
  variants: Dict[str, Optional["TypeLike"]]

  def __str__(self) -> str:
    return self.name


def _format_record_fields(record_type: "RecordType") -> str:
  return "{" + ", ".join(record_type.fields.keys()) + "}"


def unify(left: TypeLike, right: TypeLike, context: str, loc: Optional[ast.SourceLoc] = None) -> TypeLike:
  l_res = resolve(left)
  r_res = resolve(right)
  if l_res is r_res:
    return l_res
  if isinstance(l_res, TypeVar):
    l_res.instance = r_res
    return r_res
  if isinstance(r_res, TypeVar):
    r_res.instance = l_res
    return l_res
  if isinstance(l_res, RecordType) and isinstance(r_res, RecordType):
    if l_res.fields.keys() != r_res.fields.keys():
      left_fields = _format_record_fields(l_res)
      right_fields = _format_record_fields(r_res)
      raise TypeError(f"Record fields mismatch: {left_fields} vs {right_fields} ({context})", loc)
    for name, left_field in l_res.fields.items():
      unify(left_field, r_res.fields[name], f"record field '{name}'", loc)
    return l_res
  if isinstance(l_res, ListType) and isinstance(r_res, ListType):
    unify(l_res.element, r_res.element, "list element", loc)
    return l_res
  if isinstance(l_res, EnumType) and isinstance(r_res, EnumType):
    if l_res.name != r_res.name:
      raise TypeError(f"Type mismatch: {l_res} vs {r_res} ({context})", loc)
    return l_res
  if l_res != r_res:
    raise TypeError(f"Type mismatch: {l_res} vs {r_res} ({context})", loc)
  return l_res


class TypeEnv:
  def __init__(self, parent: Optional["TypeEnv"] = None):
    self.parent = parent
    self.values: Dict[str, TypeLike] = {}

  def define(self, name: str, value_type: TypeLike, loc: Optional[ast.SourceLoc] = None):
    if name in self.values:
      raise TypeError(f"Variable '{name}' already defined in this scope", loc)
    self.values[name] = value_type

  def get(self, name: str, loc: Optional[ast.SourceLoc] = None) -> TypeLike:
    if name in self.values:
      return self.values[name]
    if self.parent is not None:
      return self.parent.get(name, loc)
    raise TypeError(f"Undefined variable '{name}'", loc)

  def assign(self, name: str, value_type: TypeLike, loc: Optional[ast.SourceLoc] = None):
    if name in self.values:
      unify(self.values[name], value_type, f"assignment to '{name}'", loc)
      return
    if self.parent is not None:
      self.parent.assign(name, value_type, loc)
      return
    raise TypeError(f"Undefined variable '{name}'", loc)

  def has(self, name: str) -> bool:
    if name in self.values:
      return True
    if self.parent is not None:
      return self.parent.has(name)
    return False


@dataclass
class FunctionType:
  name: str
  params: List[TypeLike]
  return_type: TypeLike


@dataclass
class ModuleTypes:
  name: str
  enums: Dict[str, EnumType]
  variants: Dict[str, EnumType]
  functions: Dict[str, FunctionType]
  imports: Dict[str, str]
  exported_functions: Dict[str, FunctionType]
  exported_enums: Dict[str, EnumType]
  exported_variants: Dict[str, EnumType]


class TypeChecker:
  def __init__(
    self,
    program: ast.Program,
    modules: Optional[Dict[str, ModuleInfo]] = None,
    root_module: Optional[str] = None,
  ):
    self.program = program
    self.modules_info = modules or {}
    self.root_module = root_module or program.module_name or "<root>"
    if not self.modules_info:
      if self.program.imports:
        loc = self.program.imports[0].loc if self.program.imports else None
        raise TypeError("Imports require the loader", loc)
      exports = self._collect_exports(self.program, self.root_module)
      self.modules_info = {
        self.root_module: ModuleInfo(
          name=self.root_module,
          program=self.program,
          path="<memory>",
          imports={},
          exports=exports,
        )
      }
    if self.root_module not in self.modules_info:
      if self.program.module_name and self.program.module_name in self.modules_info:
        self.root_module = self.program.module_name
      else:
        self.root_module = next(iter(self.modules_info.keys()))

    self.modules: Dict[str, ModuleTypes] = {}
    self._collect_modules()

  def _enum_key(self, module_name: str, enum_name: str) -> str:
    return f"{module_name}.{enum_name}"

  def _collect_exports(self, program: ast.Program, module_name: str) -> ModuleExports:
    functions_by_name = {fn.name: fn for fn in program.functions}
    enums_by_name = {enum_def.name: enum_def for enum_def in program.enums}
    variants: Dict[str, str] = {}
    for enum_def in program.enums:
      for variant in enum_def.variants:
        variants[variant.name] = enum_def.name
    exported_names: List[str] = []
    if program.exports:
      seen_exports = set()
      for decl in program.exports:
        for name in decl.names:
          if name in seen_exports:
            raise TypeError(f"Export '{name}' already listed in module '{module_name}'", decl.loc)
          seen_exports.add(name)
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
        raise TypeError(f"Unknown export '{name}' in module '{module_name}'", None)
      if len(matches) > 1:
        kinds = ", ".join(matches)
        raise TypeError(
          f"Export '{name}' in module '{module_name}' is ambiguous ({kinds})",
          None,
        )
      if name in functions_by_name:
        exported_functions[name] = functions_by_name[name]
        continue
      if name in enums_by_name:
        exported_enums[name] = enums_by_name[name]
        continue
      exported_variants[name] = variants[name]
    return ModuleExports(
      name=module_name,
      functions=functions_by_name,
      enums=enums_by_name,
      variants=variants,
      exported_functions=exported_functions,
      exported_enums=exported_enums,
      exported_variants=exported_variants,
    )

  def _type_from_ref(
    self,
    type_ref: ast.TypeRef,
    enums: Dict[str, EnumType],
    imports: Dict[str, str],
  ) -> TypeLike:
    if type_ref.module is not None:
      target_name = imports.get(type_ref.module)
      if target_name is None:
        raise TypeError(f"Unknown module '{type_ref.module}'", type_ref.loc)
      target_types = self.modules.get(target_name)
      if target_types is None:
        raise TypeError(f"Unknown module '{type_ref.module}'", type_ref.loc)
      enum_type = target_types.exported_enums.get(type_ref.name)
      if enum_type is None:
        raise TypeError(
          f"Module '{type_ref.module}' has no export '{type_ref.name}'",
          type_ref.loc,
        )
      return enum_type
    name = type_ref.name
    if name == "Int":
      return INT
    if name == "Bool":
      return BOOL
    if name == "String":
      return STRING
    if name == "Unit":
      return UNIT
    if name in enums:
      return enums[name]
    raise TypeError(f"Unknown type '{name}'", type_ref.loc)

  def _collect_modules(self):
    for module_name, info in self.modules_info.items():
      enums: Dict[str, EnumType] = {}
      variants: Dict[str, EnumType] = {}
      for enum_def in info.exports.enums.values():
        if enum_def.name in enums:
          raise TypeError(f"Enum '{enum_def.name}' already defined", enum_def.loc)
        enums[enum_def.name] = EnumType(name=self._enum_key(module_name, enum_def.name), variants={})
      for enum_def in info.exports.enums.values():
        variant_payloads: Dict[str, Optional[TypeLike]] = {}
        for variant in enum_def.variants:
          if variant.name in variants:
            raise TypeError(f"Enum variant '{variant.name}' already defined", variant.loc)
          if variant.name == "print":
            raise TypeError("Enum variant 'print' conflicts with built-in function", variant.loc)
          payload_type = None
          if variant.payload_type is not None:
            payload_type = self._type_from_ref(variant.payload_type, enums, info.imports)
          variant_payloads[variant.name] = payload_type
        enum_type = EnumType(
          name=self._enum_key(module_name, enum_def.name),
          variants=variant_payloads,
        )
        enums[enum_def.name] = enum_type
        for variant_name in variant_payloads.keys():
          variants[variant_name] = enum_type

      functions: Dict[str, FunctionType] = {}
      for fn in info.exports.functions.values():
        if fn.name in functions:
          raise TypeError(f"Function '{fn.name}' already defined", fn.loc)
        if fn.name in enums:
          raise TypeError(f"Function '{fn.name}' conflicts with enum name", fn.loc)
        if fn.name in variants:
          raise TypeError(f"Function '{fn.name}' conflicts with enum variant", fn.loc)
        params: List[TypeLike] = []
        for param in fn.params:
          if param.type_ann is not None:
            params.append(self._type_from_ref(param.type_ann, enums, info.imports))
          else:
            params.append(TypeVar(f"{fn.name}.{param.name}"))
        if fn.return_type is not None:
          ret_type: TypeLike = self._type_from_ref(fn.return_type, enums, info.imports)
        else:
          ret_type = TypeVar(f"{fn.name}.ret")
        functions[fn.name] = FunctionType(name=fn.name, params=params, return_type=ret_type)

      exported_functions: Dict[str, FunctionType] = {}
      for name in info.exports.exported_functions.keys():
        fn_type = functions.get(name)
        if fn_type is None:
          raise TypeError(f"Unknown export '{name}'", None)
        exported_functions[name] = fn_type

      exported_enums: Dict[str, EnumType] = {}
      for name in info.exports.exported_enums.keys():
        enum_type = enums.get(name)
        if enum_type is None:
          raise TypeError(f"Unknown export '{name}'", None)
        exported_enums[name] = enum_type

      exported_variants: Dict[str, EnumType] = {}
      for name in info.exports.exported_variants.keys():
        variant_type = variants.get(name)
        if variant_type is None:
          raise TypeError(f"Unknown export '{name}'", None)
        exported_variants[name] = variant_type

      self.modules[module_name] = ModuleTypes(
        name=module_name,
        enums=enums,
        variants=variants,
        functions=functions,
        imports=info.imports,
        exported_functions=exported_functions,
        exported_enums=exported_enums,
        exported_variants=exported_variants,
      )

  def check(self):
    for module_name, module_types in self.modules.items():
      info = self.modules_info[module_name]
      for fn in info.exports.functions.values():
        self._check_function(fn, module_types)

  def _check_function(self, fn: ast.FunctionDef, module_types: ModuleTypes):
    fn_type = module_types.functions[fn.name]
    env = TypeEnv()
    for param, t in zip(fn.params, fn_type.params):
      env.define(param.name, t, param.loc)
    has_return = False
    for stmt in fn.body.statements:
      if self._check_stmt(stmt, env, fn_type.return_type, in_loop=False, module_types=module_types):
        has_return = True
    if not has_return:
      unify(fn_type.return_type, UNIT, f"implicit return in '{fn.name}'", fn.loc)

  def _check_stmt(
    self,
    stmt: ast.Stmt,
    env: TypeEnv,
    expected_return: TypeLike,
    in_loop: bool,
    module_types: ModuleTypes,
    allow_return: bool = True,
  ) -> bool:
    if isinstance(stmt, ast.LetStmt):
      value_type = self._check_expr(stmt.expr, env, in_loop=in_loop, module_types=module_types)
      if stmt.type_ann is not None:
        annotated = self._type_from_ref(
          stmt.type_ann,
          module_types.enums,
          module_types.imports,
        )
        unify(annotated, value_type, f"let '{stmt.name}'", stmt.loc)
        env.define(stmt.name, annotated, stmt.loc)
      else:
        env.define(stmt.name, value_type, stmt.loc)
      return False
    if isinstance(stmt, ast.SetStmt):
      value_type = self._check_expr(stmt.expr, env, in_loop=in_loop, module_types=module_types)
      env.assign(stmt.name, value_type, stmt.loc)
      return False
    if isinstance(stmt, ast.ForStmt):
      start_t = self._check_expr(stmt.start, env, in_loop=in_loop, module_types=module_types)
      end_t = self._check_expr(stmt.end, env, in_loop=in_loop, module_types=module_types)
      unify(start_t, INT, "for range start", stmt.start.loc)
      unify(end_t, INT, "for range end", stmt.end.loc)
      if stmt.step is not None:
        step_t = self._check_expr(stmt.step, env, in_loop=in_loop, module_types=module_types)
        unify(step_t, INT, "for range step", stmt.step.loc)
      loop_env = TypeEnv(parent=env)
      loop_env.define(stmt.var_name, INT, stmt.loc)
      for inner in stmt.body.statements:
        self._check_stmt(
          inner,
          loop_env,
          expected_return,
          in_loop=True,
          module_types=module_types,
          allow_return=allow_return,
        )
      return False
    if isinstance(stmt, ast.BreakStmt):
      if not in_loop:
        raise TypeError("break used outside of a loop", stmt.loc)
      return False
    if isinstance(stmt, ast.ContinueStmt):
      if not in_loop:
        raise TypeError("continue used outside of a loop", stmt.loc)
      return False
    if isinstance(stmt, ast.ReturnStmt):
      if not allow_return:
        raise TypeError("return is not allowed inside expression block", stmt.loc)
      value_type = self._check_expr(stmt.expr, env, in_loop=in_loop, module_types=module_types)
      unify(expected_return, value_type, "return", stmt.loc)
      return True
    if isinstance(stmt, ast.ExprStmt):
      self._check_expr(stmt.expr, env, in_loop=in_loop, module_types=module_types)
      return False
    if isinstance(stmt, ast.WhileStmt):
      cond_t = self._check_expr(stmt.cond, env, in_loop=in_loop, module_types=module_types)
      unify(cond_t, BOOL, "while condition", stmt.cond.loc)
      for inner in stmt.body.statements:
        self._check_stmt(
          inner,
          env,
          expected_return,
          in_loop=True,
          module_types=module_types,
          allow_return=allow_return,
        )
      return False
    raise TypeError(f"Unknown statement type: {stmt}", getattr(stmt, "loc", None))

  def _check_block_expr(
    self,
    block: ast.Block,
    env: TypeEnv,
    in_loop: bool,
    module_types: ModuleTypes,
  ) -> TypeLike:
    last_type: TypeLike = UNIT
    for stmt in block.statements:
      if isinstance(stmt, ast.LetStmt):
        value_type = self._check_expr(stmt.expr, env, in_loop=in_loop, module_types=module_types)
        if stmt.type_ann is not None:
          annotated = self._type_from_ref(
            stmt.type_ann,
            module_types.enums,
            module_types.imports,
          )
          unify(annotated, value_type, f"let '{stmt.name}'", stmt.loc)
          env.define(stmt.name, annotated, stmt.loc)
        else:
          env.define(stmt.name, value_type, stmt.loc)
        continue
      if isinstance(stmt, ast.SetStmt):
        value_type = self._check_expr(stmt.expr, env, in_loop=in_loop, module_types=module_types)
        env.assign(stmt.name, value_type, stmt.loc)
        continue
      if isinstance(stmt, ast.ExprStmt):
        last_type = self._check_expr(stmt.expr, env, in_loop=in_loop, module_types=module_types)
        continue
      if isinstance(stmt, (ast.ForStmt, ast.WhileStmt)):
        self._check_stmt(
          stmt,
          env,
          TypeVar("expr_block_return"),
          in_loop=in_loop,
          module_types=module_types,
          allow_return=False,
        )
        continue
      if isinstance(stmt, (ast.BreakStmt, ast.ContinueStmt)):
        self._check_stmt(
          stmt,
          env,
          TypeVar("expr_block_return"),
          in_loop=in_loop,
          module_types=module_types,
          allow_return=False,
        )
        continue
      if isinstance(stmt, ast.ReturnStmt):
        raise TypeError("return is not allowed inside expression block", stmt.loc)
      raise TypeError(f"Unsupported statement in expression block: {stmt}", getattr(stmt, "loc", None))
    return last_type

  def _check_pattern(
    self,
    pattern: ast.Pattern,
    subject_t: TypeLike,
    env: TypeEnv,
    module_types: ModuleTypes,
  ):
    if isinstance(pattern, ast.WildcardPattern):
      return
    if isinstance(pattern, ast.BindingPattern):
      if pattern.name in module_types.variants:
        enum_type = module_types.variants[pattern.name]
        unify(subject_t, enum_type, "match pattern", pattern.loc)
        return
      env.define(pattern.name, subject_t, pattern.loc)
      return
    if isinstance(pattern, ast.IntPattern):
      unify(subject_t, INT, "match pattern", pattern.loc)
      return
    if isinstance(pattern, ast.StringPattern):
      unify(subject_t, STRING, "match pattern", pattern.loc)
      return
    if isinstance(pattern, ast.BoolPattern):
      unify(subject_t, BOOL, "match pattern", pattern.loc)
      return
    if isinstance(pattern, ast.EnumPattern):
      if pattern.module is not None:
        target_name = module_types.imports.get(pattern.module)
        if target_name is None:
          raise TypeError(f"Unknown module '{pattern.module}'", pattern.loc)
        target_types = self.modules.get(target_name)
        if target_types is None:
          raise TypeError(f"Unknown module '{pattern.module}'", pattern.loc)
        if pattern.name not in target_types.exported_variants:
          raise TypeError(
            f"Module '{pattern.module}' has no export '{pattern.name}'",
            pattern.loc,
          )
        enum_type = target_types.exported_variants[pattern.name]
      else:
        if pattern.name not in module_types.variants:
          raise TypeError(f"Unknown enum variant '{pattern.name}'", pattern.loc)
        enum_type = module_types.variants[pattern.name]
      if pattern.name not in enum_type.variants:
        raise TypeError(f"Unknown enum variant '{pattern.name}'", pattern.loc)
      unify(subject_t, enum_type, "match pattern", pattern.loc)
      payload_type = enum_type.variants.get(pattern.name)
      if pattern.payload is None:
        return
      if payload_type is None:
        raise TypeError(f"Enum variant '{pattern.name}' has no payload", pattern.loc)
      self._check_pattern(pattern.payload, payload_type, env, module_types)
      return
    raise TypeError(f"Unknown match pattern: {pattern}", getattr(pattern, "loc", None))

  def _check_module_field_access(
    self,
    module_alias: str,
    field: str,
    loc: Optional[ast.SourceLoc],
    module_types: ModuleTypes,
  ) -> TypeLike:
    target_name = module_types.imports.get(module_alias)
    if target_name is None:
      raise TypeError(f"Unknown module '{module_alias}'", loc)
    target_types = self.modules.get(target_name)
    if target_types is None:
      raise TypeError(f"Unknown module '{module_alias}'", loc)
    if field in target_types.exported_variants:
      enum_type = target_types.exported_variants.get(field)
      if enum_type is None:
        raise TypeError(f"Unknown enum variant '{field}'", loc)
      payload_type = enum_type.variants.get(field)
      if payload_type is not None:
        raise TypeError(f"Enum variant '{field}' requires a payload", loc)
      return enum_type
    if field in target_types.exported_functions:
      raise TypeError(f"Function '{field}' is not a value", loc)
    raise TypeError(f"Module '{module_alias}' has no export '{field}'", loc)

  def _check_named_call(
    self,
    name: str,
    args: List[ast.Expr],
    env: TypeEnv,
    in_loop: bool,
    loc: Optional[ast.SourceLoc],
    module_types: ModuleTypes,
    check_env: bool = True,
  ) -> TypeLike:
    if name in module_types.variants:
      enum_type = module_types.variants[name]
      payload_type = enum_type.variants.get(name)
      if payload_type is None:
        if args:
          raise TypeError(
            f"Enum variant '{name}' expects 0 args, got {len(args)}",
            loc,
          )
        return enum_type
      if len(args) != 1:
        raise TypeError(
          f"Enum variant '{name}' expects 1 arg, got {len(args)}",
          loc,
        )
      arg_t = self._check_expr(args[0], env, in_loop=in_loop, module_types=module_types)
      unify(arg_t, payload_type, f"enum payload for '{name}'", args[0].loc)
      return enum_type
    if check_env and env.has(name):
      raise TypeError(f"'{name}' is not callable", loc)
    if name == 'print':
      for arg in args:
        self._check_expr(arg, env, in_loop=in_loop, module_types=module_types)
      return UNIT
    if name not in module_types.functions:
      raise TypeError(f"Unknown function '{name}'", loc)
    fn_type = module_types.functions[name]
    if len(args) != len(fn_type.params):
      raise TypeError(
        f"Function '{name}' expects {len(fn_type.params)} args, got {len(args)}",
        loc,
      )
    for arg_expr, param_t in zip(args, fn_type.params):
      arg_t = self._check_expr(arg_expr, env, in_loop=in_loop, module_types=module_types)
      unify(arg_t, param_t, f"call to '{name}'", arg_expr.loc)
    return fn_type.return_type

  def _check_module_call(
    self,
    callee: ast.FieldAccess,
    args: List[ast.Expr],
    env: TypeEnv,
    in_loop: bool,
    module_types: ModuleTypes,
  ) -> TypeLike:
    if not isinstance(callee.base, ast.VarRef):
      raise TypeError("Call target is not callable", callee.loc)
    base_name = callee.base.name
    if env.has(base_name):
      raise TypeError("Call target is not callable", callee.loc)
    target_name = module_types.imports.get(base_name)
    if target_name is None:
      raise TypeError(f"Unknown module '{base_name}'", callee.base.loc)
    target_types = self.modules.get(target_name)
    if target_types is None:
      raise TypeError(f"Unknown module '{base_name}'", callee.base.loc)
    field = callee.field
    if field in target_types.exported_variants:
      return self._check_named_call(
        field,
        args,
        env,
        in_loop=in_loop,
        loc=callee.loc,
        module_types=target_types,
        check_env=False,
      )
    if field in target_types.exported_functions:
      return self._check_named_call(
        field,
        args,
        env,
        in_loop=in_loop,
        loc=callee.loc,
        module_types=target_types,
        check_env=False,
      )
    raise TypeError(f"Module '{base_name}' has no export '{field}'", callee.loc)

  def _check_expr(
    self,
    expr: ast.Expr,
    env: TypeEnv,
    in_loop: bool = False,
    module_types: Optional[ModuleTypes] = None,
  ) -> TypeLike:
    if module_types is None:
      raise TypeError("Missing module context for expression", getattr(expr, "loc", None))
    if isinstance(expr, ast.IntLiteral):
      return INT
    if isinstance(expr, ast.StringLiteral):
      return STRING
    if isinstance(expr, ast.BoolLiteral):
      return BOOL
    if isinstance(expr, ast.RecordLiteral):
      fields: Dict[str, TypeLike] = {}
      for field in expr.fields:
        if field.name in fields:
          raise TypeError(f"Duplicate field '{field.name}' in record literal", field.loc)
        fields[field.name] = self._check_expr(field.expr, env, in_loop=in_loop, module_types=module_types)
      return RecordType(fields=fields)
    if isinstance(expr, ast.ListLiteral):
      if not expr.elements:
        return ListType(element=TypeVar("list_elem"))
      elem_type = self._check_expr(expr.elements[0], env, in_loop=in_loop, module_types=module_types)
      for elem in expr.elements[1:]:
        elem_t = self._check_expr(elem, env, in_loop=in_loop, module_types=module_types)
        unify(elem_type, elem_t, "list literal", getattr(elem, "loc", None))
      return ListType(element=elem_type)
    if isinstance(expr, ast.VarRef):
      if expr.name in module_types.functions:
        raise TypeError(f"Function '{expr.name}' is not a value", expr.loc)
      if expr.name in module_types.variants:
        enum_type = module_types.variants[expr.name]
        payload_type = enum_type.variants.get(expr.name)
        if payload_type is not None:
          raise TypeError(f"Enum variant '{expr.name}' requires a payload", expr.loc)
        return enum_type
      if env.has(expr.name):
        return env.get(expr.name, expr.loc)
      if expr.name in module_types.imports:
        raise TypeError(f"Module '{expr.name}' is not a value", expr.loc)
      return env.get(expr.name, expr.loc)
    if isinstance(expr, ast.FieldAccess):
      if (
        isinstance(expr.base, ast.VarRef)
        and not env.has(expr.base.name)
        and expr.base.name in module_types.imports
      ):
        return self._check_module_field_access(expr.base.name, expr.field, expr.loc, module_types)
      base_t = self._check_expr(expr.base, env, in_loop=in_loop, module_types=module_types)
      base_res = resolve(base_t)
      if isinstance(base_res, TypeVar):
        field_t = TypeVar(f"field.{expr.field}")
        record_t = RecordType(fields={expr.field: field_t})
        unify(base_res, record_t, "field access", expr.loc)
        return field_t
      if not isinstance(base_res, RecordType):
        raise TypeError("Field access expects a record", expr.loc)
      if expr.field not in base_res.fields:
        available = ", ".join(base_res.fields.keys())
        raise TypeError(f"Unknown field '{expr.field}' (available: {available})", expr.loc)
      return base_res.fields[expr.field]
    if isinstance(expr, ast.IndexExpr):
      base_t = self._check_expr(expr.base, env, in_loop=in_loop, module_types=module_types)
      index_t = self._check_expr(expr.index, env, in_loop=in_loop, module_types=module_types)
      unify(index_t, INT, "list index", expr.index.loc)
      base_res = resolve(base_t)
      if isinstance(base_res, TypeVar):
        elem_t = TypeVar("list_elem")
        list_t = ListType(element=elem_t)
        unify(base_res, list_t, "list index", expr.loc)
        return elem_t
      if not isinstance(base_res, ListType):
        raise TypeError("Indexing expects a list", expr.loc)
      return base_res.element
    if isinstance(expr, ast.UnaryOp):
      value_type = self._check_expr(expr.expr, env, in_loop=in_loop, module_types=module_types)
      if expr.op == '-':
        unify(value_type, INT, "unary -", expr.loc)
        return INT
      if expr.op == '!':
        unify(value_type, BOOL, "unary !", expr.loc)
        return BOOL
      raise TypeError(f"Unknown unary operator {expr.op}", expr.loc)
    if isinstance(expr, ast.BinaryOp):
      left_t = self._check_expr(expr.left, env, in_loop=in_loop, module_types=module_types)
      right_t = self._check_expr(expr.right, env, in_loop=in_loop, module_types=module_types)
      op = expr.op
      if op == '+':
        left_res = resolve(left_t)
        right_res = resolve(right_t)
        if left_res == STRING or right_res == STRING:
          return STRING
        if left_res == BOOL or right_res == BOOL or left_res == UNIT or right_res == UNIT:
          raise TypeError("Operator '+' expects integers or a string operand", expr.loc)
        unify(left_t, INT, "binary +", expr.loc)
        unify(right_t, INT, "binary +", expr.loc)
        return INT
      if op in ('-', '*', '/'):
        unify(left_t, INT, f"binary {op}", expr.loc)
        unify(right_t, INT, f"binary {op}", expr.loc)
        return INT
      if op in ('<', '<=', '>', '>='):
        unify(left_t, INT, f"binary {op}", expr.loc)
        unify(right_t, INT, f"binary {op}", expr.loc)
        return BOOL
      if op in ('==', '!='):
        unify(left_t, right_t, f"binary {op}", expr.loc)
        return BOOL
      if op in ('&&', '||'):
        unify(left_t, BOOL, f"binary {op}", expr.loc)
        unify(right_t, BOOL, f"binary {op}", expr.loc)
        return BOOL
      raise TypeError(f"Unknown operator {op}", expr.loc)
    if isinstance(expr, ast.IfExpr):
      cond_t = self._check_expr(expr.cond, env, in_loop=in_loop, module_types=module_types)
      unify(cond_t, BOOL, "if condition", expr.cond.loc)
      then_env = TypeEnv(parent=env)
      else_env = TypeEnv(parent=env)
      then_t = self._check_block_expr(expr.then_block, then_env, in_loop=in_loop, module_types=module_types)
      else_t = self._check_block_expr(expr.else_block, else_env, in_loop=in_loop, module_types=module_types)
      return unify(then_t, else_t, "if expression", expr.loc)
    if isinstance(expr, ast.MatchExpr):
      subject_t = self._check_expr(expr.subject, env, in_loop=in_loop, module_types=module_types)
      if not expr.arms:
        raise TypeError("match expression requires at least one arm", expr.loc)
      result_t: Optional[TypeLike] = None
      for arm in expr.arms:
        arm_env = TypeEnv(parent=env)
        self._check_pattern(arm.pattern, subject_t, arm_env, module_types)
        arm_t = self._check_block_expr(arm.body, arm_env, in_loop=in_loop, module_types=module_types)
        if result_t is None:
          result_t = arm_t
        else:
          result_t = unify(result_t, arm_t, "match expression", arm.loc)
      return result_t if result_t is not None else UNIT
    if isinstance(expr, ast.CallExpr):
      if isinstance(expr.callee, ast.VarRef):
        return self._check_named_call(
          expr.callee.name,
          expr.args,
          env,
          in_loop=in_loop,
          loc=expr.loc,
          module_types=module_types,
        )
      if isinstance(expr.callee, ast.FieldAccess):
        return self._check_module_call(
          expr.callee,
          expr.args,
          env,
          in_loop=in_loop,
          module_types=module_types,
        )
      raise TypeError("Call target is not callable", expr.loc)
    raise TypeError(f"Unknown expression type: {expr}", getattr(expr, "loc", None))


def check_program(
  program: ast.Program,
  modules: Optional[Dict[str, ModuleInfo]] = None,
  root_module: Optional[str] = None,
):
  checker = TypeChecker(program, modules=modules, root_module=root_module)
  checker.check()

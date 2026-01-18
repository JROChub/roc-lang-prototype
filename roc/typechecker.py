from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from . import ast


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

TypeLike = Union[SimpleType, "TypeVar", "RecordType", "ListType"]


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


class TypeChecker:
  def __init__(self, program: ast.Program):
    self.program = program
    self.functions: Dict[str, FunctionType] = {}
    self._collect_functions()

  def _type_from_ref(self, type_ref: ast.TypeRef) -> SimpleType:
    name = type_ref.name
    if name == "Int":
      return INT
    if name == "Bool":
      return BOOL
    if name == "String":
      return STRING
    if name == "Unit":
      return UNIT
    raise TypeError(f"Unknown type '{name}'", type_ref.loc)

  def _collect_functions(self):
    for fn in self.program.functions:
      if fn.name in self.functions:
        raise TypeError(f"Function '{fn.name}' already defined", fn.loc)
      params: List[TypeLike] = []
      for param in fn.params:
        if param.type_ann is not None:
          params.append(self._type_from_ref(param.type_ann))
        else:
          params.append(TypeVar(f"{fn.name}.{param.name}"))
      if fn.return_type is not None:
        ret_type: TypeLike = self._type_from_ref(fn.return_type)
      else:
        ret_type = TypeVar(f"{fn.name}.ret")
      self.functions[fn.name] = FunctionType(name=fn.name, params=params, return_type=ret_type)

  def check(self):
    for fn in self.program.functions:
      self._check_function(fn)

  def _check_function(self, fn: ast.FunctionDef):
    fn_type = self.functions[fn.name]
    env = TypeEnv()
    for param, t in zip(fn.params, fn_type.params):
      env.define(param.name, t, param.loc)
    has_return = False
    for stmt in fn.body.statements:
      if self._check_stmt(stmt, env, fn_type.return_type, in_loop=False):
        has_return = True
    if not has_return:
      unify(fn_type.return_type, UNIT, f"implicit return in '{fn.name}'", fn.loc)

  def _check_stmt(
    self,
    stmt: ast.Stmt,
    env: TypeEnv,
    expected_return: TypeLike,
    in_loop: bool,
    allow_return: bool = True,
  ) -> bool:
    if isinstance(stmt, ast.LetStmt):
      value_type = self._check_expr(stmt.expr, env, in_loop=in_loop)
      if stmt.type_ann is not None:
        annotated = self._type_from_ref(stmt.type_ann)
        unify(annotated, value_type, f"let '{stmt.name}'", stmt.loc)
        env.define(stmt.name, annotated, stmt.loc)
      else:
        env.define(stmt.name, value_type, stmt.loc)
      return False
    if isinstance(stmt, ast.SetStmt):
      value_type = self._check_expr(stmt.expr, env, in_loop=in_loop)
      env.assign(stmt.name, value_type, stmt.loc)
      return False
    if isinstance(stmt, ast.ForStmt):
      start_t = self._check_expr(stmt.start, env, in_loop=in_loop)
      end_t = self._check_expr(stmt.end, env, in_loop=in_loop)
      unify(start_t, INT, "for range start", stmt.start.loc)
      unify(end_t, INT, "for range end", stmt.end.loc)
      if stmt.step is not None:
        step_t = self._check_expr(stmt.step, env, in_loop=in_loop)
        unify(step_t, INT, "for range step", stmt.step.loc)
      loop_env = TypeEnv(parent=env)
      loop_env.define(stmt.var_name, INT, stmt.loc)
      for inner in stmt.body.statements:
        self._check_stmt(inner, loop_env, expected_return, in_loop=True, allow_return=allow_return)
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
      value_type = self._check_expr(stmt.expr, env, in_loop=in_loop)
      unify(expected_return, value_type, "return", stmt.loc)
      return True
    if isinstance(stmt, ast.ExprStmt):
      self._check_expr(stmt.expr, env, in_loop=in_loop)
      return False
    if isinstance(stmt, ast.WhileStmt):
      cond_t = self._check_expr(stmt.cond, env, in_loop=in_loop)
      unify(cond_t, BOOL, "while condition", stmt.cond.loc)
      for inner in stmt.body.statements:
        self._check_stmt(inner, env, expected_return, in_loop=True, allow_return=allow_return)
      return False
    raise TypeError(f"Unknown statement type: {stmt}", getattr(stmt, "loc", None))

  def _check_block_expr(self, block: ast.Block, env: TypeEnv, in_loop: bool) -> TypeLike:
    last_type: TypeLike = UNIT
    for stmt in block.statements:
      if isinstance(stmt, ast.LetStmt):
        value_type = self._check_expr(stmt.expr, env, in_loop=in_loop)
        if stmt.type_ann is not None:
          annotated = self._type_from_ref(stmt.type_ann)
          unify(annotated, value_type, f"let '{stmt.name}'", stmt.loc)
          env.define(stmt.name, annotated, stmt.loc)
        else:
          env.define(stmt.name, value_type, stmt.loc)
        continue
      if isinstance(stmt, ast.SetStmt):
        value_type = self._check_expr(stmt.expr, env, in_loop=in_loop)
        env.assign(stmt.name, value_type, stmt.loc)
        continue
      if isinstance(stmt, ast.ExprStmt):
        last_type = self._check_expr(stmt.expr, env, in_loop=in_loop)
        continue
      if isinstance(stmt, (ast.ForStmt, ast.WhileStmt)):
        self._check_stmt(
          stmt,
          env,
          TypeVar("expr_block_return"),
          in_loop=in_loop,
          allow_return=False,
        )
        continue
      if isinstance(stmt, (ast.BreakStmt, ast.ContinueStmt)):
        self._check_stmt(
          stmt,
          env,
          TypeVar("expr_block_return"),
          in_loop=in_loop,
          allow_return=False,
        )
        continue
      if isinstance(stmt, ast.ReturnStmt):
        raise TypeError("return is not allowed inside expression block", stmt.loc)
      raise TypeError(f"Unsupported statement in expression block: {stmt}", getattr(stmt, "loc", None))
    return last_type

  def _check_expr(self, expr: ast.Expr, env: TypeEnv, in_loop: bool = False) -> TypeLike:
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
        fields[field.name] = self._check_expr(field.expr, env, in_loop=in_loop)
      return RecordType(fields=fields)
    if isinstance(expr, ast.ListLiteral):
      if not expr.elements:
        return ListType(element=TypeVar("list_elem"))
      elem_type = self._check_expr(expr.elements[0], env, in_loop=in_loop)
      for elem in expr.elements[1:]:
        elem_t = self._check_expr(elem, env, in_loop=in_loop)
        unify(elem_type, elem_t, "list literal", getattr(elem, "loc", None))
      return ListType(element=elem_type)
    if isinstance(expr, ast.VarRef):
      if expr.name in self.functions:
        raise TypeError(f"Function '{expr.name}' is not a value", expr.loc)
      return env.get(expr.name, expr.loc)
    if isinstance(expr, ast.FieldAccess):
      base_t = self._check_expr(expr.base, env, in_loop=in_loop)
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
      base_t = self._check_expr(expr.base, env, in_loop=in_loop)
      index_t = self._check_expr(expr.index, env, in_loop=in_loop)
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
      value_type = self._check_expr(expr.expr, env, in_loop=in_loop)
      if expr.op == '-':
        unify(value_type, INT, "unary -", expr.loc)
        return INT
      if expr.op == '!':
        unify(value_type, BOOL, "unary !", expr.loc)
        return BOOL
      raise TypeError(f"Unknown unary operator {expr.op}", expr.loc)
    if isinstance(expr, ast.BinaryOp):
      left_t = self._check_expr(expr.left, env, in_loop=in_loop)
      right_t = self._check_expr(expr.right, env, in_loop=in_loop)
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
      cond_t = self._check_expr(expr.cond, env, in_loop=in_loop)
      unify(cond_t, BOOL, "if condition", expr.cond.loc)
      then_env = TypeEnv(parent=env)
      else_env = TypeEnv(parent=env)
      then_t = self._check_block_expr(expr.then_block, then_env, in_loop=in_loop)
      else_t = self._check_block_expr(expr.else_block, else_env, in_loop=in_loop)
      return unify(then_t, else_t, "if expression", expr.loc)
    if isinstance(expr, ast.MatchExpr):
      subject_t = self._check_expr(expr.subject, env, in_loop=in_loop)
      if not expr.arms:
        raise TypeError("match expression requires at least one arm", expr.loc)
      result_t: Optional[TypeLike] = None
      for arm in expr.arms:
        if isinstance(arm.pattern, ast.IntPattern):
          unify(subject_t, INT, "match pattern", arm.loc)
        elif isinstance(arm.pattern, ast.StringPattern):
          unify(subject_t, STRING, "match pattern", arm.loc)
        elif isinstance(arm.pattern, ast.BoolPattern):
          unify(subject_t, BOOL, "match pattern", arm.loc)
        elif isinstance(arm.pattern, ast.WildcardPattern):
          pass
        else:
          raise TypeError(f"Unknown match pattern: {arm.pattern}", arm.loc)
        arm_env = TypeEnv(parent=env)
        arm_t = self._check_block_expr(arm.body, arm_env, in_loop=in_loop)
        if result_t is None:
          result_t = arm_t
        else:
          result_t = unify(result_t, arm_t, "match expression", arm.loc)
      return result_t if result_t is not None else UNIT
    if isinstance(expr, ast.CallExpr):
      if env.has(expr.callee):
        raise TypeError(f"'{expr.callee}' is not callable", expr.loc)
      if expr.callee == 'print':
        for arg in expr.args:
          self._check_expr(arg, env, in_loop=in_loop)
        return UNIT
      if expr.callee not in self.functions:
        raise TypeError(f"Unknown function '{expr.callee}'", expr.loc)
      fn_type = self.functions[expr.callee]
      if len(expr.args) != len(fn_type.params):
        raise TypeError(
          f"Function '{expr.callee}' expects {len(fn_type.params)} args, got {len(expr.args)}",
          expr.loc,
        )
      for arg_expr, param_t in zip(expr.args, fn_type.params):
        arg_t = self._check_expr(arg_expr, env, in_loop=in_loop)
        unify(arg_t, param_t, f"call to '{expr.callee}'", arg_expr.loc)
      return fn_type.return_type
    raise TypeError(f"Unknown expression type: {expr}", getattr(expr, "loc", None))


def check_program(program: ast.Program):
  checker = TypeChecker(program)
  checker.check()

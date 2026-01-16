from typing import Any, Dict, List, Optional
from . import ast

class RuntimeError(Exception):
  def __init__(self, message: str, loc: Optional[ast.SourceLoc] = None):
    super().__init__(message)
    self.message = message
    self.loc = loc

  def __str__(self) -> str:
    if self.loc is not None:
      return f"{self.loc.line}:{self.loc.column}: {self.message}"
    return self.message

class BreakSignal(Exception):
  def __init__(self, loc: Optional[ast.SourceLoc] = None):
    super().__init__()
    self.loc = loc

class ContinueSignal(Exception):
  def __init__(self, loc: Optional[ast.SourceLoc] = None):
    super().__init__()
    self.loc = loc

class Environment:
  def __init__(self, parent: Optional['Environment'] = None):
    self.parent = parent
    self.values: Dict[str, Any] = {}

  def define(self, name: str, value: Any, loc: Optional[ast.SourceLoc] = None):
    if name in self.values:
      raise RuntimeError(f"Variable '{name}' already defined in this scope", loc)
    self.values[name] = value

  def get(self, name: str, loc: Optional[ast.SourceLoc] = None) -> Any:
    if name in self.values:
      return self.values[name]
    if self.parent is not None:
      return self.parent.get(name, loc)
    raise RuntimeError(f"Undefined variable '{name}'", loc)

  def assign(self, name: str, value: Any, loc: Optional[ast.SourceLoc] = None):
    if name in self.values:
      self.values[name] = value
      return
    if self.parent is not None:
      self.parent.assign(name, value, loc)
      return
    raise RuntimeError(f"Undefined variable '{name}'", loc)

class FunctionValue:
  def __init__(self, func_def: ast.FunctionDef, interpreter: 'Interpreter'):
    self.func_def = func_def
    self.interpreter = interpreter

  def call(self, args: List[Any], loc: Optional[ast.SourceLoc] = None) -> Any:
    if len(args) != len(self.func_def.params):
      raise RuntimeError(
        f"Function '{self.func_def.name}' expected {len(self.func_def.params)} args, got {len(args)}",
        loc,
      )
    env = Environment(parent=self.interpreter.global_env)
    for param, value in zip(self.func_def.params, args):
      env.define(param.name, value, param.loc)
    return self.interpreter.execute_block(self.func_def.body, env)

class Interpreter:
  def __init__(self, program: ast.Program):
    self.program = program
    self.global_env = Environment()
    self.functions: Dict[str, FunctionValue] = {}
    self._install_builtins()
    # Register functions
    for fn in self.program.functions:
      if fn.name in self.functions or fn.name in self.global_env.values:
        raise RuntimeError(f"Function '{fn.name}' already defined", fn.loc)
      fv = FunctionValue(fn, self)
      self.functions[fn.name] = fv
      self.global_env.define(fn.name, fv, fn.loc)

  def _install_builtins(self):
    def builtin_print(args: List[Any]) -> Any:
      if len(args) == 0:
        s = ''
      elif len(args) == 1:
        s = self._to_string(args[0])
      else:
        s = ' '.join(self._to_string(a) for a in args)
      print(s)
      return None

    self.global_env.define('print', builtin_print)

  def _to_string(self, value: Any) -> str:
    if isinstance(value, bool):
      return "true" if value else "false"
    return str(value)

  def execute(self):
    if 'main' not in self.functions:
      raise RuntimeError("No 'main' function defined")
    main_fn = self.functions['main']
    return main_fn.call([])

  def execute_block(self, block: ast.Block, env: Environment) -> Any:
    for stmt in block.statements:
      try:
        result, should_return = self.execute_stmt(stmt, env)
      except BreakSignal as e:
        raise RuntimeError("break used outside of a loop", e.loc) from None
      except ContinueSignal as e:
        raise RuntimeError("continue used outside of a loop", e.loc) from None
      if should_return:
        return result
    return None

  def execute_stmt(self, stmt: ast.Stmt, env: Environment):
    if isinstance(stmt, ast.LetStmt):
      value = self.eval_expr(stmt.expr, env)
      env.define(stmt.name, value, stmt.loc)
      return None, False
    if isinstance(stmt, ast.SetStmt):
      value = self.eval_expr(stmt.expr, env)
      env.assign(stmt.name, value, stmt.loc)
      return None, False
    if isinstance(stmt, ast.ForStmt):
      start = self._require_int(self.eval_expr(stmt.start, env), "for range expects integers", stmt.start.loc)
      end = self._require_int(self.eval_expr(stmt.end, env), "for range expects integers", stmt.end.loc)
      if stmt.step is not None:
        step_value = self._require_int(self.eval_expr(stmt.step, env), "for step expects integer", stmt.step.loc)
        if step_value == 0:
          raise RuntimeError("for step cannot be zero", stmt.step.loc)
        step = step_value
      else:
        step = 1 if start <= end else -1
      current = start
      def in_range(value: int) -> bool:
        if stmt.inclusive:
          return value <= end if step > 0 else value >= end
        return value < end if step > 0 else value > end
      while in_range(current):
        loop_env = Environment(parent=env)
        loop_env.define(stmt.var_name, current, stmt.loc)
        try:
          for inner in stmt.body.statements:
            result, should_return = self.execute_stmt(inner, loop_env)
            if should_return:
              return result, True
        except ContinueSignal:
          current += step
          continue
        except BreakSignal:
          break
        current += step
      return None, False
    if isinstance(stmt, ast.BreakStmt):
      raise BreakSignal(stmt.loc)
    if isinstance(stmt, ast.ContinueStmt):
      raise ContinueSignal(stmt.loc)
    if isinstance(stmt, ast.ReturnStmt):
      value = self.eval_expr(stmt.expr, env)
      return value, True
    if isinstance(stmt, ast.ExprStmt):
      _ = self.eval_expr(stmt.expr, env)
      return None, False
    if isinstance(stmt, ast.WhileStmt):
      # While loop with ability to return from inside
      while self._is_truthy(self.eval_expr(stmt.cond, env)):
        try:
          for inner in stmt.body.statements:
            result, should_return = self.execute_stmt(inner, env)
            if should_return:
              return result, True
        except ContinueSignal:
          continue
        except BreakSignal:
          break
      return None, False
    raise RuntimeError(f"Unknown statement type: {stmt}", getattr(stmt, "loc", None))

  def eval_block_expr(self, block: ast.Block, env: Environment):
    """Evaluate a block as an expression.

    The result is the value of the last expression statement in the block,
    or None if there is no such statement.
    """
    last_value: Any = None
    for stmt in block.statements:
      if isinstance(stmt, ast.LetStmt):
        value = self.eval_expr(stmt.expr, env)
        env.define(stmt.name, value, stmt.loc)
      elif isinstance(stmt, ast.SetStmt):
        value = self.eval_expr(stmt.expr, env)
        env.assign(stmt.name, value, stmt.loc)
      elif isinstance(stmt, ast.ExprStmt):
        last_value = self.eval_expr(stmt.expr, env)
      elif isinstance(stmt, (ast.ForStmt, ast.WhileStmt, ast.BreakStmt, ast.ContinueStmt)):
        _res, should_return = self.execute_stmt(stmt, env)
        if should_return:
          raise RuntimeError("return inside loop is not allowed in expression block", stmt.loc)
      elif isinstance(stmt, ast.ReturnStmt):
        raise RuntimeError("return is not allowed inside expression block", stmt.loc)
      else:
        raise RuntimeError(f"Unsupported statement in expression block: {stmt}", getattr(stmt, "loc", None))
    return last_value

  def eval_expr(self, expr: ast.Expr, env: Environment) -> Any:
    if isinstance(expr, ast.IntLiteral):
      return expr.value
    if isinstance(expr, ast.StringLiteral):
      return expr.value
    if isinstance(expr, ast.BoolLiteral):
      return expr.value
    if isinstance(expr, ast.VarRef):
      return env.get(expr.name, expr.loc)
    if isinstance(expr, ast.UnaryOp):
      value = self.eval_expr(expr.expr, env)
      if expr.op == '-':
        return -self._ensure_int(value, expr.op, expr.loc)
      if expr.op == '!':
        return not self._ensure_bool(value, expr.op, expr.loc)
      raise RuntimeError(f"Unknown unary operator {expr.op}", expr.loc)
    if isinstance(expr, ast.BinaryOp):
      op = expr.op
      if op in ('&&', '||'):
        left = self.eval_expr(expr.left, env)
        left_bool = self._ensure_bool(left, op, expr.loc)
        if op == '&&':
          if not left_bool:
            return False
          right = self.eval_expr(expr.right, env)
          return self._ensure_bool(right, op, expr.loc)
        if left_bool:
          return True
        right = self.eval_expr(expr.right, env)
        return self._ensure_bool(right, op, expr.loc)
      left = self.eval_expr(expr.left, env)
      right = self.eval_expr(expr.right, env)
      if op == '+':
        if isinstance(left, str) or isinstance(right, str):
          return self._to_string(left) + self._to_string(right)
        return self._ensure_int(left, op, expr.loc) + self._ensure_int(right, op, expr.loc)
      if op == '-':
        return self._ensure_int(left, op, expr.loc) - self._ensure_int(right, op, expr.loc)
      if op == '*':
        return self._ensure_int(left, op, expr.loc) * self._ensure_int(right, op, expr.loc)
      if op == '/':
        return self._int_div(
          self._ensure_int(left, op, expr.loc),
          self._ensure_int(right, op, expr.loc),
          expr.loc,
        )
      if op == '==':
        self._ensure_same_type(left, right, op, expr.loc)
        return left == right
      if op == '!=':
        self._ensure_same_type(left, right, op, expr.loc)
        return left != right
      if op == '<':
        self._ensure_int(left, op, expr.loc)
        self._ensure_int(right, op, expr.loc)
        return left < right
      if op == '<=':
        self._ensure_int(left, op, expr.loc)
        self._ensure_int(right, op, expr.loc)
        return left <= right
      if op == '>':
        self._ensure_int(left, op, expr.loc)
        self._ensure_int(right, op, expr.loc)
        return left > right
      if op == '>=':
        self._ensure_int(left, op, expr.loc)
        self._ensure_int(right, op, expr.loc)
        return left >= right
      raise RuntimeError(f"Unknown operator {op}", expr.loc)
    if isinstance(expr, ast.IfExpr):
      cond_val = self.eval_expr(expr.cond, env)
      truthy = self._is_truthy(cond_val)
      block = expr.then_block if truthy else expr.else_block
      child_env = Environment(parent=env)
      return self.eval_block_expr(block, child_env)
    if isinstance(expr, ast.CallExpr):
      callee_val = env.get(expr.callee, expr.loc)
      args = [self.eval_expr(a, env) for a in expr.args]
      if isinstance(callee_val, FunctionValue):
        return callee_val.call(args, expr.loc)
      if callable(callee_val):
        return callee_val(args)
      raise RuntimeError(f"'{expr.callee}' is not callable", expr.loc)
    raise RuntimeError(f"Unknown expression type: {expr}", getattr(expr, "loc", None))

  def _is_truthy(self, value: Any) -> bool:
    if isinstance(value, bool):
      return value
    if isinstance(value, int):
      return value != 0
    if isinstance(value, str):
      return value != ""
    return bool(value)

  def _ensure_int(self, value: Any, op: str, loc: Optional[ast.SourceLoc]) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
      raise RuntimeError(f"Operator '{op}' expects integers", loc)
    return value

  def _ensure_same_type(self, left: Any, right: Any, op: str, loc: Optional[ast.SourceLoc]):
    if type(left) is not type(right):
      raise RuntimeError(f"Operator '{op}' expects matching types", loc)

  def _ensure_bool(self, value: Any, op: str, loc: Optional[ast.SourceLoc]) -> bool:
    if not isinstance(value, bool):
      raise RuntimeError(f"Operator '{op}' expects booleans", loc)
    return value

  def _int_div(self, left: int, right: int, loc: Optional[ast.SourceLoc]) -> int:
    if right == 0:
      raise RuntimeError("Division by zero", loc)
    quotient = left // right
    if (left < 0) != (right < 0) and left % right != 0:
      quotient += 1
    return quotient

  def _require_int(self, value: Any, message: str, loc: Optional[ast.SourceLoc]) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
      raise RuntimeError(message, loc)
    return value

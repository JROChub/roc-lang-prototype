from typing import List
from .. import ast
from .ir import IRModule, IRFunction

def lower_program(program: ast.Program) -> IRModule:
  mod = IRModule()
  for fn in program.functions:
    mod.functions.append(lower_function(fn))
  return mod

def lower_function(fn: ast.FunctionDef) -> IRFunction:
  params = [describe_param(p) for p in fn.params]
  return_type = describe_type(fn.return_type) if fn.return_type is not None else None
  ir_fn = IRFunction(name=fn.name, params=params, return_type=return_type)
  for stmt in fn.body.statements:
    ir_fn.body.append(describe_stmt(stmt))
  return ir_fn

def describe_param(param: ast.Param) -> str:
  if param.type_ann is None:
    return param.name
  return f"{param.name}: {describe_type(param.type_ann)}"

def describe_type(type_ref: ast.TypeRef) -> str:
  return type_ref.name

def describe_stmt(stmt: ast.Stmt) -> str:
  if isinstance(stmt, ast.LetStmt):
    type_ann = f": {describe_type(stmt.type_ann)}" if stmt.type_ann is not None else ""
    return f"let {stmt.name}{type_ann} = {describe_expr(stmt.expr)};"
  if isinstance(stmt, ast.SetStmt):
    return f"set {stmt.name} = {describe_expr(stmt.expr)};"
  if isinstance(stmt, ast.ForStmt):
    range_op = '..=' if stmt.inclusive else '..'
    step = f" by {describe_expr(stmt.step)}" if stmt.step is not None else ""
    body_lines = [describe_stmt(s) for s in stmt.body.statements]
    inner = ' '.join(body_lines)
    return f"for {stmt.var_name} in {describe_expr(stmt.start)} {range_op} {describe_expr(stmt.end)}{step} {{ {inner} }}"
  if isinstance(stmt, ast.BreakStmt):
    return "break;"
  if isinstance(stmt, ast.ContinueStmt):
    return "continue;"
  if isinstance(stmt, ast.ReturnStmt):
    return f"return {describe_expr(stmt.expr)};"
  if isinstance(stmt, ast.ExprStmt):
    return f"{describe_expr(stmt.expr)};"
  if isinstance(stmt, ast.WhileStmt):
    body_lines = [describe_stmt(s) for s in stmt.body.statements]
    inner = ' '.join(body_lines)
    return f"while ({describe_expr(stmt.cond)}) {{ {inner} }}"
  return f"<unknown stmt {stmt.__class__.__name__}>"

def describe_expr(expr: ast.Expr) -> str:
  if isinstance(expr, ast.IntLiteral):
    return str(expr.value)
  if isinstance(expr, ast.StringLiteral):
    return repr(expr.value)
  if isinstance(expr, ast.BoolLiteral):
    return "true" if expr.value else "false"
  if isinstance(expr, ast.RecordLiteral):
    fields = ", ".join(f"{field.name}: {describe_expr(field.expr)}" for field in expr.fields)
    return "{" + fields + "}"
  if isinstance(expr, ast.ListLiteral):
    elements = ", ".join(describe_expr(elem) for elem in expr.elements)
    return "[" + elements + "]"
  if isinstance(expr, ast.VarRef):
    return expr.name
  if isinstance(expr, ast.FieldAccess):
    return f"{describe_expr(expr.base)}.{expr.field}"
  if isinstance(expr, ast.IndexExpr):
    return f"{describe_expr(expr.base)}[{describe_expr(expr.index)}]"
  if isinstance(expr, ast.UnaryOp):
    return f"({expr.op}{describe_expr(expr.expr)})"
  if isinstance(expr, ast.BinaryOp):
    return f"({describe_expr(expr.left)} {expr.op} {describe_expr(expr.right)})"
  if isinstance(expr, ast.IfExpr):
    then_inner = ' '.join(describe_stmt(s) for s in expr.then_block.statements)
    else_inner = ' '.join(describe_stmt(s) for s in expr.else_block.statements)
    return f"if {describe_expr(expr.cond)} {{ {then_inner} }} else {{ {else_inner} }}"
  if isinstance(expr, ast.MatchExpr):
    arm_parts: List[str] = []
    for arm in expr.arms:
      body_inner = ' '.join(describe_stmt(s) for s in arm.body.statements)
      arm_parts.append(f"{describe_pattern(arm.pattern)} => {{ {body_inner} }}")
    arms = '; '.join(arm_parts)
    return f"match {describe_expr(expr.subject)} {{ {arms} }}"
  if isinstance(expr, ast.CallExpr):
    args = ', '.join(describe_expr(a) for a in expr.args)
    return f"{expr.callee}({args})"
  return f"<unknown expr {expr.__class__.__name__}>"

def describe_pattern(pattern: ast.Pattern) -> str:
  if isinstance(pattern, ast.WildcardPattern):
    return "_"
  if isinstance(pattern, ast.IntPattern):
    return str(pattern.value)
  if isinstance(pattern, ast.StringPattern):
    return repr(pattern.value)
  if isinstance(pattern, ast.BoolPattern):
    return "true" if pattern.value else "false"
  return f"<unknown pattern {pattern.__class__.__name__}>"

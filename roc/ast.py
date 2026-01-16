from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class Program:
  module_name: Optional[str]
  functions: List['FunctionDef']

@dataclass(frozen=True)
class SourceLoc:
  line: int
  column: int

@dataclass
class TypeRef:
  name: str
  loc: Optional[SourceLoc] = None

@dataclass
class Param:
  name: str
  type_ann: Optional[TypeRef] = None
  loc: Optional[SourceLoc] = None

@dataclass
class FunctionDef:
  name: str
  params: List[Param]
  body: 'Block'
  return_type: Optional[TypeRef] = None
  loc: Optional[SourceLoc] = None

@dataclass
class Block:
  statements: List['Stmt']
  loc: Optional[SourceLoc] = None

class Stmt:
  pass

@dataclass
class LetStmt(Stmt):
  name: str
  expr: 'Expr'
  type_ann: Optional[TypeRef] = None
  loc: Optional[SourceLoc] = None

@dataclass
class SetStmt(Stmt):
  name: str
  expr: 'Expr'
  loc: Optional[SourceLoc] = None

@dataclass
class ForStmt(Stmt):
  var_name: str
  start: 'Expr'
  end: 'Expr'
  inclusive: bool
  step: Optional['Expr']
  body: Block
  loc: Optional[SourceLoc] = None

@dataclass
class BreakStmt(Stmt):
  loc: Optional[SourceLoc] = None

@dataclass
class ContinueStmt(Stmt):
  loc: Optional[SourceLoc] = None

@dataclass
class ReturnStmt(Stmt):
  expr: 'Expr'
  loc: Optional[SourceLoc] = None

@dataclass
class ExprStmt(Stmt):
  expr: 'Expr'
  loc: Optional[SourceLoc] = None

@dataclass
class WhileStmt(Stmt):
  cond: 'Expr'
  body: Block
  loc: Optional[SourceLoc] = None

class Expr:
  pass

@dataclass
class IntLiteral(Expr):
  value: int
  loc: Optional[SourceLoc] = None

@dataclass
class StringLiteral(Expr):
  value: str
  loc: Optional[SourceLoc] = None

@dataclass
class BoolLiteral(Expr):
  value: bool
  loc: Optional[SourceLoc] = None

@dataclass
class VarRef(Expr):
  name: str
  loc: Optional[SourceLoc] = None

@dataclass
class UnaryOp(Expr):
  op: str
  expr: Expr
  loc: Optional[SourceLoc] = None

@dataclass
class BinaryOp(Expr):
  op: str
  left: Expr
  right: Expr
  loc: Optional[SourceLoc] = None

@dataclass
class IfExpr(Expr):
  cond: Expr
  then_block: Block
  else_block: Block
  loc: Optional[SourceLoc] = None

@dataclass
class CallExpr(Expr):
  callee: str
  args: List[Expr]
  loc: Optional[SourceLoc] = None

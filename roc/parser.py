from typing import List, Optional
from .lexer import Token
from . import ast

class ParseError(Exception):
  def __init__(self, message: str, loc: Optional[ast.SourceLoc] = None):
    super().__init__(message)
    self.message = message
    self.loc = loc

  def __str__(self) -> str:
    if self.loc is not None:
      return f"{self.loc.line}:{self.loc.column}: {self.message}"
    return self.message

class Parser:
  def __init__(self, tokens: List[Token]):
    self.tokens = tokens
    self.pos = 0

  def loc(self, tok: Token) -> ast.SourceLoc:
    return ast.SourceLoc(line=tok.line, column=tok.column)

  def current(self) -> Token:
    return self.tokens[self.pos]

  def match(self, *kinds):
    tok = self.current()
    if tok.kind in kinds:
      self.pos += 1
      return tok
    expected = ' or '.join(kinds)
    raise ParseError(f"Expected {expected}, got {tok.kind}", self.loc(tok))

  def try_match(self, *kinds):
    tok = self.current()
    if tok.kind in kinds:
      self.pos += 1
      return tok
    return None

  def parse_program(self) -> ast.Program:
    module_name: Optional[str] = None
    if self.current().kind == 'MODULE':
      self.match('MODULE')
      ident = self.match('IDENT')
      module_name = ident.value

    functions: List[ast.FunctionDef] = []
    while self.current().kind != 'EOF':
      functions.append(self.parse_function())
    return ast.Program(module_name=module_name, functions=functions)

  def parse_function(self) -> ast.FunctionDef:
    tok_fn = self.current()
    if tok_fn.kind != 'FN':
      raise ParseError(f"Expected FN, got {tok_fn.kind}", self.loc(tok_fn))
    fn_tok = self.match('FN')
    name_tok = self.match('IDENT')
    name = name_tok.value
    self.match('LPAREN')
    params: List[ast.Param] = []
    if self.current().kind != 'RPAREN':
      while True:
        param_tok = self.match('IDENT')
        type_ann = None
        if self.current().kind == 'COLON':
          self.match('COLON')
          type_ann = self.parse_type()
        params.append(ast.Param(name=param_tok.value, type_ann=type_ann, loc=self.loc(param_tok)))
        if self.try_match('COMMA') is None:
          break
    self.match('RPAREN')
    return_type = None
    if self.current().kind == 'ARROW':
      self.match('ARROW')
      return_type = self.parse_type()
    body = self.parse_block()
    return ast.FunctionDef(
      name=name,
      params=params,
      body=body,
      return_type=return_type,
      loc=self.loc(fn_tok),
    )

  def parse_type(self) -> ast.TypeRef:
    type_tok = self.match('IDENT')
    return ast.TypeRef(name=type_tok.value, loc=self.loc(type_tok))

  def parse_block(self) -> ast.Block:
    lbrace_tok = self.match('LBRACE')
    statements: List[ast.Stmt] = []
    while self.current().kind != 'RBRACE':
      if self.current().kind == 'EOF':
        tok = self.current()
        raise ParseError("Expected RBRACE, got EOF", self.loc(tok))
      statements.append(self.parse_statement())
    self.match('RBRACE')
    return ast.Block(statements=statements, loc=self.loc(lbrace_tok))

  def parse_statement(self) -> ast.Stmt:
    tok = self.current()
    if tok.kind == 'LET':
      return self.parse_let()
    if tok.kind == 'SET':
      return self.parse_set()
    if tok.kind == 'FOR':
      return self.parse_for()
    if tok.kind == 'BREAK':
      return self.parse_break()
    if tok.kind == 'CONTINUE':
      return self.parse_continue()
    if tok.kind == 'RETURN':
      return self.parse_return()
    if tok.kind == 'WHILE':
      return self.parse_while()
    expr = self.parse_expr()
    semicol_tok = self.match('SEMICOL')
    return ast.ExprStmt(expr=expr, loc=self.loc(semicol_tok))

  def parse_let(self) -> ast.LetStmt:
    let_tok = self.match('LET')
    name_tok = self.match('IDENT')
    type_ann = None
    if self.current().kind == 'COLON':
      self.match('COLON')
      type_ann = self.parse_type()
    self.match('EQUALS')
    expr = self.parse_expr()
    self.match('SEMICOL')
    return ast.LetStmt(
      name=name_tok.value,
      expr=expr,
      type_ann=type_ann,
      loc=self.loc(let_tok),
    )

  def parse_set(self) -> ast.SetStmt:
    set_tok = self.match('SET')
    name_tok = self.match('IDENT')
    self.match('EQUALS')
    expr = self.parse_expr()
    self.match('SEMICOL')
    return ast.SetStmt(name=name_tok.value, expr=expr, loc=self.loc(set_tok))

  def parse_for(self) -> ast.ForStmt:
    for_tok = self.match('FOR')
    name_tok = self.match('IDENT')
    self.match('IN')
    start_expr = self.parse_expr()
    op_tok = self.current()
    if op_tok.kind != 'OP' or op_tok.value not in ('..', '..='):
      raise ParseError(f"Expected '..' or '..=', got {op_tok.value}", self.loc(op_tok))
    self.match('OP')
    inclusive = op_tok.value == '..='
    end_expr = self.parse_expr()
    step_expr = None
    if self.current().kind == 'BY':
      self.match('BY')
      step_expr = self.parse_expr()
    body = self.parse_block()
    return ast.ForStmt(
      var_name=name_tok.value,
      start=start_expr,
      end=end_expr,
      inclusive=inclusive,
      step=step_expr,
      body=body,
      loc=self.loc(for_tok),
    )

  def parse_break(self) -> ast.BreakStmt:
    break_tok = self.match('BREAK')
    self.match('SEMICOL')
    return ast.BreakStmt(loc=self.loc(break_tok))

  def parse_continue(self) -> ast.ContinueStmt:
    cont_tok = self.match('CONTINUE')
    self.match('SEMICOL')
    return ast.ContinueStmt(loc=self.loc(cont_tok))

  def parse_return(self) -> ast.ReturnStmt:
    ret_tok = self.match('RETURN')
    expr = self.parse_expr()
    self.match('SEMICOL')
    return ast.ReturnStmt(expr=expr, loc=self.loc(ret_tok))

  def parse_while(self) -> ast.WhileStmt:
    while_tok = self.match('WHILE')
    cond = self.parse_expr()
    body = self.parse_block()
    return ast.WhileStmt(cond=cond, body=body, loc=self.loc(while_tok))

  # Expressions

  def parse_expr(self):
    return self.parse_if_expr()

  def parse_if_expr(self):
    if self.current().kind == 'IF':
      if_tok = self.match('IF')
      cond = self.parse_expr()
      then_block = self.parse_block()
      self.match('ELSE')
      if self.current().kind == 'IF':
        else_expr = self.parse_if_expr()
        else_block = ast.Block(
          statements=[ast.ExprStmt(expr=else_expr, loc=else_expr.loc)],
          loc=else_expr.loc,
        )
      else:
        else_block = self.parse_block()
      return ast.IfExpr(
        cond=cond,
        then_block=then_block,
        else_block=else_block,
        loc=self.loc(if_tok),
      )
    return self.parse_logical_or()

  def parse_logical_or(self):
    expr = self.parse_logical_and()
    while self.current().kind == 'OP' and self.current().value == '||':
      op_tok = self.match('OP')
      right = self.parse_logical_and()
      expr = ast.BinaryOp(op=op_tok.value, left=expr, right=right, loc=self.loc(op_tok))
    return expr

  def parse_logical_and(self):
    expr = self.parse_equality()
    while self.current().kind == 'OP' and self.current().value == '&&':
      op_tok = self.match('OP')
      right = self.parse_equality()
      expr = ast.BinaryOp(op=op_tok.value, left=expr, right=right, loc=self.loc(op_tok))
    return expr

  def parse_equality(self):
    expr = self.parse_relational()
    while self.current().kind == 'OP' and self.current().value in ('==', '!='):
      op_tok = self.match('OP')
      right = self.parse_relational()
      expr = ast.BinaryOp(op=op_tok.value, left=expr, right=right, loc=self.loc(op_tok))
    return expr

  def parse_relational(self):
    expr = self.parse_additive()
    while self.current().kind == 'OP' and self.current().value in ('<', '<=', '>', '>='):
      op_tok = self.match('OP')
      right = self.parse_additive()
      expr = ast.BinaryOp(op=op_tok.value, left=expr, right=right, loc=self.loc(op_tok))
    return expr

  def parse_additive(self):
    expr = self.parse_multiplicative()
    while self.current().kind == 'OP' and self.current().value in ('+', '-'):
      op_tok = self.match('OP')
      right = self.parse_multiplicative()
      expr = ast.BinaryOp(op=op_tok.value, left=expr, right=right, loc=self.loc(op_tok))
    return expr

  def parse_multiplicative(self):
    expr = self.parse_unary()
    while self.current().kind == 'OP' and self.current().value in ('*', '/'):
      op_tok = self.match('OP')
      right = self.parse_unary()
      expr = ast.BinaryOp(op=op_tok.value, left=expr, right=right, loc=self.loc(op_tok))
    return expr

  def parse_unary(self):
    tok = self.current()
    if tok.kind == 'OP' and tok.value in ('-', '!'):
      op_tok = self.match('OP')
      expr = self.parse_unary()
      return ast.UnaryOp(op=op_tok.value, expr=expr, loc=self.loc(op_tok))
    return self.parse_postfix()

  def parse_postfix(self):
    expr = self.parse_primary()
    while True:
      if self.current().kind == 'DOT':
        self.match('DOT')
        field_tok = self.match('IDENT')
        expr = ast.FieldAccess(base=expr, field=field_tok.value, loc=self.loc(field_tok))
        continue
      if self.current().kind == 'LBRACKET':
        lbrack_tok = self.match('LBRACKET')
        index_expr = self.parse_expr()
        self.match('RBRACKET')
        expr = ast.IndexExpr(base=expr, index=index_expr, loc=self.loc(lbrack_tok))
        continue
      break
    return expr

  def parse_primary(self):
    tok = self.current()
    if tok.kind == 'LBRACKET':
      return self.parse_list_literal()
    if tok.kind == 'LBRACE':
      return self.parse_record_literal()
    if tok.kind in ('TRUE', 'FALSE'):
      bool_tok = self.match(tok.kind)
      return ast.BoolLiteral(value=(tok.kind == 'TRUE'), loc=self.loc(bool_tok))
    if tok.kind == 'NUMBER':
      num_tok = self.match('NUMBER')
      return ast.IntLiteral(int(num_tok.value), loc=self.loc(num_tok))
    if tok.kind == 'STRING':
      str_tok = self.match('STRING')
      raw = str_tok.value[1:-1]
      try:
        value = bytes(raw, 'utf-8').decode('unicode_escape')
      except UnicodeDecodeError as e:
        raise ParseError(f"Invalid string escape: {e}", self.loc(str_tok)) from None
      return ast.StringLiteral(value, loc=self.loc(str_tok))
    if tok.kind == 'IDENT':
      ident = tok.value
      ident_tok = self.match('IDENT')
      if self.current().kind == 'LPAREN':
        self.match('LPAREN')
        args = []
        if self.current().kind != 'RPAREN':
          while True:
            args.append(self.parse_expr())
            if self.try_match('COMMA') is None:
              break
        self.match('RPAREN')
        return ast.CallExpr(callee=ident, args=args, loc=self.loc(ident_tok))
      return ast.VarRef(name=ident, loc=self.loc(ident_tok))
    if tok.kind == 'LPAREN':
      self.match('LPAREN')
      expr = self.parse_expr()
      self.match('RPAREN')
      return expr
    raise ParseError(f"Unexpected token {tok.kind} ('{tok.value}')", self.loc(tok))

  def parse_list_literal(self):
    lbrack_tok = self.match('LBRACKET')
    elements: List[ast.Expr] = []
    if self.current().kind != 'RBRACKET':
      while True:
        elements.append(self.parse_expr())
        if self.try_match('COMMA') is None:
          break
    self.match('RBRACKET')
    return ast.ListLiteral(elements=elements, loc=self.loc(lbrack_tok))

  def parse_record_literal(self):
    lbrace_tok = self.match('LBRACE')
    fields: List[ast.RecordField] = []
    seen = set()
    if self.current().kind != 'RBRACE':
      while True:
        name_tok = self.match('IDENT')
        if name_tok.value in seen:
          raise ParseError(f"Duplicate field '{name_tok.value}' in record literal", self.loc(name_tok))
        seen.add(name_tok.value)
        self.match('COLON')
        value_expr = self.parse_expr()
        fields.append(ast.RecordField(name=name_tok.value, expr=value_expr, loc=self.loc(name_tok)))
        if self.try_match('COMMA') is None:
          break
    self.match('RBRACE')
    return ast.RecordLiteral(fields=fields, loc=self.loc(lbrace_tok))

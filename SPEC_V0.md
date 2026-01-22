# Greyalien v0 Core Spec (Interpreter Subset)

This document specifies the exact Greyalien subset implemented by the Python
interpreter in `greyalien/`. It is intentionally small and focused.

## 1. Syntax overview

- Optional module header: `module main`
- Enum definitions: `enum Color { Red, Green, Blue }`
- Import declarations: `import math_utils;` or `import math_utils as math;`
- Export declarations: `export { add, Color, Red };`
- Function definitions: `fn name(params) { ... }`
- Optional type annotations on parameters, returns, and `let` bindings.
- Statements:
  - `let name = expr;`
  - `set name = expr;`
  - `return expr;`
  - `while expr { ... }`
  - `for name in start .. end { ... }`
  - `for name in start ..= end { ... }`
  - `for name in start .. end by step { ... }`
  - `for name in start ..= end by step { ... }`
  - `break;`
  - `continue;`
  - expression statements: `expr;`
- Expressions:
  - Literals: integers, strings, booleans (`true`, `false`)
  - Record literals: `{x: 1, y: 2}`
  - List literals: `[1, 2, 3]`
  - Unary `-`, `!`
  - Binary `+`, `-`, `*`, `/`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`
  - Field access: `expr.field`
  - Indexing: `expr[index]`
  - Parentheses: `(expr)`
  - `if` expressions with `else`
  - `match` expressions with literal patterns, bindings, and `_` wildcard
  - Function calls: `expr(arg1, arg2)`

## 2. Grammar (subset)

```text
program      ::= module_decl? (import_decl | export_decl)* (enum_def | fn_def)*

module_decl  ::= "module" IDENT

import_decl  ::= "import" IDENT ("as" IDENT)? ";"

export_decl  ::= "export" "{" export_list "}" ";"

export_list  ::= IDENT ("," IDENT)*

enum_def     ::= "enum" IDENT "{" enum_variants "}"

enum_variants ::= enum_variant ("," enum_variant)*

enum_variant ::= IDENT ("(" type_ref ")")?

fn_def       ::= "fn" IDENT "(" param_list? ")" return_type? block

param_list   ::= param ("," param)*

param        ::= IDENT (":" type_ref)?

return_type  ::= "->" type_ref

block        ::= "{" statement* "}"

statement    ::= let_stmt
               | set_stmt
               | for_stmt
               | break_stmt
               | continue_stmt
               | return_stmt
               | while_stmt
               | expr_stmt

let_stmt     ::= "let" IDENT (":" type_ref)? "=" expr ";"

set_stmt     ::= "set" IDENT "=" expr ";"

return_stmt  ::= "return" expr ";"

while_stmt   ::= "while" expr block

for_stmt     ::= "for" IDENT "in" expr range_op expr ("by" expr)? block

range_op     ::= ".." | "..="

break_stmt   ::= "break" ";"

continue_stmt ::= "continue" ";"

expr_stmt    ::= expr ";"

expr         ::= match_expr
               | if_expr
               | logical_or

if_expr      ::= "if" expr block "else" block

match_expr   ::= "match" expr "{" match_arm+ "}"

match_arm    ::= pattern "=>" block ";"?

pattern      ::= INT | STRING | TRUE | FALSE | "_" | binding_pattern | enum_pattern

binding_pattern ::= IDENT

enum_pattern ::= IDENT ("(" pattern ")")?
             | IDENT "." IDENT ("(" pattern ")")?

logical_or   ::= logical_and ("||" logical_and)*

logical_and  ::= equality_expr ("&&" equality_expr)*

equality_expr ::= relational_expr (("==" | "!=") relational_expr)*

relational_expr ::= additive_expr (("<" | "<=" | ">" | ">=") additive_expr)*

additive_expr ::= multiplicative_expr (("+" | "-") multiplicative_expr)*

multiplicative_expr ::= unary (("*" | "/") unary)*

unary        ::= "-" unary
               | "!" unary
               | postfix

postfix      ::= primary (call_suffix | field_suffix | index_suffix)*

call_suffix  ::= "(" arg_list? ")"

field_suffix ::= "." IDENT

index_suffix ::= "[" expr "]"

primary      ::= INT
               | STRING
               | TRUE
               | FALSE
               | record_literal
               | list_literal
               | IDENT
               | "(" expr ")"

record_literal ::= "{" field_list? "}"

field_list   ::= field ("," field)*

field        ::= IDENT ":" expr

list_literal ::= "[" expr_list? "]"

expr_list    ::= expr ("," expr)*

arg_list     ::= expr ("," expr)*

type_ref     ::= IDENT
             | IDENT "." IDENT
```

`else if` is accepted as sugar for `else { if ... }`.

## 3. Semantics

- Execution begins at `fn main()`.
- Each function call creates a new scope.
- Imports load sibling `.grl` files by name (e.g., `import math_utils;` loads `math_utils.grl`).
- `import name as alias;` binds the module namespace to `alias`; `import name;` binds it to `name`.
- `export { ... };` lists the functions, enums, and enum variants that are visible to other modules.
- Exporting an enum name does not export its variants; list variants explicitly to allow `module.Variant` access.
- Module namespaces support qualified access to exported functions and enum variants (for example, `math.add(1, 2)` or `math.Some(1)`).
- Type annotations may refer to exported enums via module qualification (e.g., `colors.Color`).
- Unexported definitions are private to their module.
- If no `export` declarations are present, the module exports nothing.
- Unqualified names resolve only within the current module.
- `let` defines a binding in the current scope. Redefining a name in the same
  scope is an error.
- `set` updates an existing binding in the nearest enclosing scope.
- `while` loops evaluate the condition before each iteration and execute in the
  current scope.
- `for` loops iterate over integer ranges:
  - `start .. end` excludes `end`.
  - `start ..= end` includes `end`.
  - If `start` is greater than `end`, the loop counts down by 1.
  - `by step` overrides the step size (must be a non-zero integer).
- `if` expressions evaluate to the value of the last expression statement in
  the chosen branch.
- `if` blocks evaluate in a child scope, so `let` bindings inside do not leak.
- `match` expressions evaluate the first arm whose pattern matches the subject.
- Match arms evaluate in child scopes like `if` blocks.
- `_` matches any value; literal patterns match values of the same type.
- Identifier patterns bind a new variable unless they match a known enum variant.
- Enum definitions introduce new types and variants.
- Enum variants are values available in expressions and `match` patterns.
- Enum variants may carry a single payload value.
- Payload constructors use call syntax (e.g., `Some(1)`).
- Payload patterns use `Variant(pattern)` (e.g., `Some(1)` or `Some(_)`).
- Payload bindings use `Variant(name)` to bind (e.g., `Some(x)`).
- Enum patterns may be qualified with a module alias (e.g., `math.Some(x)`).
- `break` exits the nearest loop; `continue` skips to the next iteration.
- Record literals evaluate to records with named fields.
- Field access reads a record field; missing fields are a runtime error.
- List literals evaluate to lists with ordered elements.
- Indexing reads a list element by integer index.
- Supported type names: `Int`, `Bool`, `String`, `Unit`, plus enum names.
- Truthiness: `false` is false, `true` is true, integer `0` is false, empty
  strings are false; everything else is truthy in this prototype.

Operators:

- `+` concatenates if either operand is a string, otherwise it adds integers.
- `-`, `*`, `/`, `<`, `<=`, `>`, `>=` require integers.
- `!`, `&&`, `||` require booleans; `&&`/`||` short-circuit.
- `/` performs integer division with truncation toward zero.
- `==` and `!=` require matching operand types.
- All comparison operators yield booleans.

Built-ins:

- `print(...)` prints zero or more values separated by spaces.

Errors:

- Invalid characters cause a lex error.
- Invalid syntax causes a parse error.
- Undefined variables, wrong arity, and division by zero raise runtime errors.
- Type mismatches are reported by the type checker (with runtime checks as a backstop).
- `for` ranges require integers; `break`/`continue` outside loops are runtime errors.
- Record literals require unique field names.
- Field access on non-record values is a runtime error.
- Indexing requires integer indices and list operands.
- Indexing out of bounds is a runtime error.
- Non-exhaustive `match` expressions are runtime errors.
- A minimal static type checker runs before execution and reports type errors.
- Type errors include line/column locations where available.

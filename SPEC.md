# Roc Language v0 Specification (Conceptual)

Roc is a new, experimental systems language intended to be:

- **Statically typed and compiled** (in its full form).
- **Memory-safe by default**, with explicit `unsafe` for low-level work.
- **Concurrency-friendly**, with lightweight tasks and channels.
- **Effect-aware**, so side effects are visible in type signatures.
- **Pleasant to use**, with algebraic data types, pattern matching, traits, and generics.

This document describes the *conceptual* v0 spec. The included interpreter
implements only a small, untyped subset.

---

## 1. Design goals

1. **Surpass C++ and Rust for new projects**:

   - No undefined behavior in safe Roc.
   - Clear, modern module system.
   - Ownership and lifetimes made simpler via lexical regions.

2. **First-class concurrency**:

   - Lightweight tasks (`spawn`).
   - Typed channels.
   - Data-race freedom enforced by the type system.

3. **Effect-aware design**:

   - Effects like I/O, randomness, and global mutation are tracked in
     function signatures via `effect` annotations.

The current interpreter does **not** implement the type/ownership/effect
system; it focuses on surface syntax and basic evaluation.

---

## 2. Core language concepts (intended full Roc)

### 2.1. Modules

Each `.roc` file starts with a module declaration:

```roc
module my.project.module
```

Module names are hierarchical and match directory structure.

### 2.2. Types (planned)

- Built-in scalar types: `Int`, `Bool`, `String`.
- `type` for records.
- `enum` for algebraic data types.
- Generics with type parameters.
- Traits and implementations via `trait` / `impl`.

### 2.3. Ownership and memory (planned)

- Single-owner semantics (similar to Rust).
- Borrows `&T` and `&mut T` with mostly inferred lifetimes.
- Safe subset guarantees no use-after-free or data races.

### 2.4. Concurrency (planned)

- Built-in `spawn` for tasks.
- Channels for message passing.
- Structured concurrency: tasks tied to scopes.

### 2.5. Effects (planned)

- `effect` clause in function signatures describes allowed side effects:

  ```roc
  fn read_file(path: String) -> Result<String, io::Error> effect [io]
  ```

---

## 3. Roc v0 interpreter subset

The included interpreter supports:

- A single module per file (optional `module` header).
- Function definitions: `fn name(args) { ... }`
- Function signatures and `let` bindings may include optional type annotations.
- `let` bindings, `set` assignments, and `return` statements inside function bodies.
- `while` loops.
- `for` loops over integer ranges (optional `by` step).
- `break` and `continue`.
- Expressions:
  - Integers, strings, booleans (`true`, `false`)
  - Unary `-`, `!`
  - Binary `+`, `-`, `*`, `/`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`
  - Parentheses
  - `if` expressions with `else`:
    `if cond { expr; } else { expr; }`
- Function calls with positional arguments.
- Built-in `print` for console output (0 or more args).

Execution starts at `fn main()` with no arguments.

---

## 4. Informal grammar (subset)

```text
program      ::= module_decl? fn_def*

module_decl  ::= "module" IDENT

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

expr         ::= if_expr
               | logical_or

if_expr      ::= "if" expr block "else" block

logical_or   ::= logical_and ("||" logical_and)*

logical_and  ::= equality_expr ("&&" equality_expr)*

equality_expr ::= relational_expr (("==" | "!=") relational_expr)*

relational_expr ::= additive_expr (("<" | "<=" | ">" | ">=") additive_expr)*

additive_expr ::= multiplicative_expr (("+" | "-") multiplicative_expr)*

multiplicative_expr ::= unary (("*" | "/") unary)*

unary        ::= "-" unary
               | "!" unary
               | primary

primary      ::= INT
               | STRING
               | TRUE
               | FALSE
               | IDENT
               | IDENT "(" arg_list? ")"
               | "(" expr ")"

arg_list     ::= expr ("," expr)*

type_ref     ::= IDENT
```

`else if` is accepted as sugar for `else { if ... }`.

---

## 5. Semantics (subset)

- `main` is the entry point.
- Each function call creates a new scope with its own variables.
- `let` defines a binding in the current scope (redefining in the same scope is an error).
- `set` updates an existing binding in the nearest enclosing scope.
- `return` exits the function with a value.
- `if` expressions evaluate to the value of either branch.
- `if` blocks evaluate in a child scope, so `let` bindings inside do not leak.
- `while` loops evaluate the condition before each iteration and run in the current scope.
- `for` loops iterate over integer ranges:
  - `start .. end` excludes `end`.
  - `start ..= end` includes `end`.
  - If `start` is greater than `end`, the loop counts down by 1.
  - `by step` overrides the step size (must be a non-zero integer).
- `break` exits the nearest loop; `continue` skips to the next iteration.

Type annotations:

- Optional annotations are supported on parameters, returns, and `let` bindings.
- Supported type names: `Int`, `Bool`, `String`, `Unit`.

Truthiness for `if`:

- Booleans: `false` is false, `true` is true.
- Integers: `0` is false, non-zero is true.
- Strings: empty is false, non-empty is true.
- Other values: use the host language truthiness (Python in this prototype).

Operators:

- `+` concatenates if either operand is a string, otherwise it adds integers.
- `-`, `*`, `/`, `<`, `<=`, `>`, `>=` require integers.
- `!`, `&&`, `||` require booleans; `&&`/`||` short-circuit.
- `/` performs integer division with truncation toward zero.
- `==` and `!=` require matching operand types.
- All comparison operators yield booleans.

Errors:

- A minimal static type checker runs before execution and reports type errors.
- Type errors include line/column locations where available.
- Type mismatches are reported by the type checker (with runtime checks as a backstop).
- Division by zero raises a runtime error.
- `for` ranges require integers; `break`/`continue` outside loops are runtime errors.

---

This spec is intentionally lightweight to match the interpreter. A full
compiler would extend this with types, ownership, effects, and a standard
library.

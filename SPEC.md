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

### 2.3. Ownership and borrowing (draft)

Roc uses a single-owner model to make memory safety explicit and teachable.
The goal is predictable rules with diagnostics that explain "why" and "how".

#### 2.3.1. Core rules

- Every value has exactly one owner at a time.
- Moving a value transfers ownership to a new binding.
- After a move, the previous binding is invalid.
- Values are dropped when their owner goes out of scope.

#### 2.3.2. Moves and copies

- Small scalar types (e.g., `Int`, `Bool`) are `Copy` by default.
- Non-`Copy` values move on assignment or pass-by-value.
- Explicit `clone` is required for non-`Copy` duplication.

#### 2.3.3. Borrowing

- `&T` is a shared (read-only) borrow.
- `&mut T` is an exclusive (read/write) borrow.
- You can have many shared borrows or one mutable borrow, but not both.
- Shared borrows cannot mutate, mutable borrows are exclusive.

#### 2.3.4. Regions and lifetimes

- Borrows are tied to lexical regions inferred from scope.
- A borrow cannot outlive its owner.
- Reborrowing is allowed but cannot extend the lifetime beyond the owner.

#### 2.3.5. Diagnostics

- Use-after-move errors point to the move site and the invalid use.
- Borrow conflicts explain both the active borrow and the conflicting access.
- Error messages include suggestions such as "borrow instead of move".

#### 2.3.6. Examples

Move and use-after-move:

```roc
fn main() {
  let data = make_buffer();
  let moved = data;
  print(moved);
  print(data); // error: use-after-move
}
```

Shared vs mutable borrow conflict:

```roc
fn main() {
  let mut x = 1;
  let r1 = &x;
  let r2 = &x;
  let m = &mut x; // error: cannot borrow mutably while shared borrows are active
  print(r1);
  print(r2);
}
```

Valid scoped mutable borrow:

```roc
fn main() {
  let mut x = 1;
  {
    let m = &mut x;
    *m = 2;
  }
  print(x); // ok: mutable borrow ended
}
```

### 2.4. Concurrency (planned)

- Built-in `spawn` for tasks.
- Channels for message passing.
- Structured concurrency: tasks tied to scopes.

### 2.5. Effects (draft)

Effects make side effects explicit in type signatures. Roc aims for a small
effect system that is easy to read and easy to teach.

#### 2.5.1. Effect annotations

Functions default to pure. Effectful functions declare a set of effects:

```roc
fn read_file(path: String) -> Result<String, io::Error> effect [io]
```

#### 2.5.2. Effect rules

- Pure functions cannot call effectful functions.
- A caller must include all effects of its callees.
- The effect set is part of the function type.

#### 2.5.3. Effect inference

- If a function body uses an effectful operation, the effect is inferred.
- Explicit annotations are allowed and must be satisfied by the body.

#### 2.5.4. Standard effect set (initial sketch)

- `io`: console and file IO.
- `net`: networking.
- `time`: clocks and timers.
- `rng`: randomness.
- `unsafe`: explicit unsafe operations.

#### 2.5.5. Examples

```roc
fn add(a: Int, b: Int) -> Int { a + b }

fn read_name() -> String effect [io] {
  return input(); // effectful builtin
}

fn main() -> Unit effect [io] {
  let name = read_name();
  print("Hello " + name);
}
```

Calling an effectful function from a pure one is an error:

```roc
fn pure() -> Int {
  let name = read_name(); // error: effect [io] not allowed here
  return 0;
}
```

#### 2.5.6. Open questions

- Should effects be row-polymorphic (e.g., `effect [io | e]`)?
- How should effect handlers or capabilities be modeled?
- Are effects attached to expressions, blocks, or only function boundaries?

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
  - Record literals: `{x: 1, y: 2}`
  - List literals: `[1, 2, 3]`
  - Unary `-`, `!`
  - Binary `+`, `-`, `*`, `/`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`
  - Field access: `expr.field`
  - Indexing: `expr[index]`
  - Parentheses
  - `if` expressions with `else`:
    `if cond { expr; } else { expr; }`
  - `match` expressions with literal patterns and `_` wildcard:
    `match expr { 1 => { expr; } _ => { expr; } }`
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

expr         ::= match_expr
               | if_expr
               | logical_or

if_expr      ::= "if" expr block "else" block

match_expr   ::= "match" expr "{" match_arm+ "}"

match_arm    ::= pattern "=>" block ";"?

pattern      ::= INT | STRING | TRUE | FALSE | "_"

logical_or   ::= logical_and ("||" logical_and)*

logical_and  ::= equality_expr ("&&" equality_expr)*

equality_expr ::= relational_expr (("==" | "!=") relational_expr)*

relational_expr ::= additive_expr (("<" | "<=" | ">" | ">=") additive_expr)*

additive_expr ::= multiplicative_expr (("+" | "-") multiplicative_expr)*

multiplicative_expr ::= unary (("*" | "/") unary)*

unary        ::= "-" unary
               | "!" unary
               | postfix

postfix      ::= primary (("." IDENT) | ("[" expr "]"))*

primary      ::= INT
               | STRING
               | TRUE
               | FALSE
               | record_literal
               | list_literal
               | IDENT
               | IDENT "(" arg_list? ")"
               | "(" expr ")"

record_literal ::= "{" field_list? "}"

field_list   ::= field ("," field)*

field        ::= IDENT ":" expr

list_literal ::= "[" expr_list? "]"

expr_list    ::= expr ("," expr)*

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
- `match` expressions evaluate the first arm whose pattern matches the subject.
- Match arms evaluate in child scopes like `if` blocks.
- Record literals evaluate to records with named fields.
- Field access reads a record field; missing fields are a runtime error.
- List literals evaluate to lists with ordered elements.
- Indexing reads a list element by integer index.
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
- Record literals require unique field names.
- Field access on non-record values is a runtime error.
- Indexing requires integer indices and list operands.
- Indexing out of bounds is a runtime error.
- Non-exhaustive `match` expressions are runtime errors.

---

This spec is intentionally lightweight to match the interpreter. A full
compiler would extend this with types, ownership, effects, and a standard
library.

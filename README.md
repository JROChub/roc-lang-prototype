# Roc Language (Prototype)

[![CI](https://github.com/JROChub/roc-lang-prototype/actions/workflows/ci.yml/badge.svg)](https://github.com/JROChub/roc-lang-prototype/actions/workflows/ci.yml)

This is a **prototype implementation** of the Roc language concept:
a new, experimental programming language designed to surpass traditional
systems languages in clarity and safety.

This ZIP includes:

- `SPEC.md` – Roc v0 conceptual language design.
- `SPEC_V0.md` – the subset spec implemented by this interpreter.
- `ROC_CORE.md` – core design principles.
- `ROC_VISION.md` – long-term vision and roadmap.
- `compiler_architecture.md` – high-level architecture for a future native Roc compiler.
- `LICENSE` – MIT license.
- `CONTRIBUTING.md` – contribution guide.
- `CHANGELOG.md` – release notes.
- `RELEASE.md` – release checklist.
- `ROADMAP.md` – v0.2 scope and priorities.
- `TRIAGE.md` – issue triage guide.
- `Makefile` – release helper targets.
- `roc/` – a minimal Roc interpreter implemented in Python for a **small v0 subset**.
- `examples/` – runnable `.roc` programs.

> Note: The interpreter is intentionally small. It runs a Roc *subset* with
> functions, conditionals, loops, arithmetic, booleans, and printing. It is
> meant as a working playground, not a production compiler.
>
> A minimal static type checker for `Int`, `Bool`, and `String` runs before
> execution and reports type errors.

## Requirements

- Python 3.9+

## Install from source

```bash
python -m pip install -e .
```

Then run:

```bash
roc run examples/hello.roc
```

## Running examples

From the directory where you unpack the ZIP:

```bash
python -m roc.cli examples/hello.roc
```

Or with the unified CLI:

```bash
python -m roc run examples/hello.roc
```

You should see:

```text
Hello from Roc!
```

Another example:

```bash
python -m roc.cli examples/math.roc
```

Or:

```bash
python -m roc run examples/math.roc
```

Expected output:

```text
Result is 42
```

Logic example:

```bash
python -m roc.cli examples/logic.roc
```

For-loop example:

```bash
python -m roc.cli examples/for_demo.roc
```

Typed example:

```bash
python -m roc.cli examples/typed.roc
```

Record example:

```bash
python -m roc.cli examples/records.roc
```

List example:

```bash
python -m roc.cli examples/list_demo.roc
```

## Running tests

```bash
python -m unittest discover -s tests
```

## Maintainer notes

- Issue triage flow and labels: `TRIAGE.md`
- Label definitions live in `.github/labels.yml` and sync via the `Label Sync` workflow

## Type checking only

```bash
python -m roc check examples/typed.roc
```

## CLI quick reference

```text
roc <file.roc>
roc run <file.roc>
roc check <file.roc>
roc ir <file.roc>
roc --all-errors <file.roc>
roc run --all-errors <file.roc>
roc check --all-errors <file.roc>
roc --version
roc --help
```

## CLI help example

```bash
roc --help
```

```text
Usage:
  roc <file.roc>
  roc run <file.roc>
  roc check <file.roc>
  roc ir <file.roc>
  roc --all-errors <file.roc>
  roc run --all-errors <file.roc>
  roc check --all-errors <file.roc>
  roc --version
  roc --help

Options:
  --all-errors  Show all parse errors instead of the first.
```

## Parse error diagnostics

Use `--all-errors` to report every parse error in one run:

```bash
roc check --all-errors examples/for_demo.roc
```

## Subset supported by the interpreter

- Optional `module` declaration (ignored at runtime):

  ```roc
  module main
  ```

- Function definitions:

  ```roc
  fn main() {
    print("Hello");
  }

  fn add(a, b) {
    return a + b;
  }
  ```

- Optional type annotations (checked before execution):

  ```roc
  fn add(a: Int, b: Int) -> Int {
    return a + b;
  }

  fn main() {
    let x: Int = 1;
    print("x = " + x);
  }
  ```

  Type errors include line/column locations where available.

- `let` bindings inside functions:

  ```roc
  fn demo() {
    let x = 10;
    let y = x * 2;
    print(y);
  }
  ```

- `set` assignments to update existing bindings:

  ```roc
  fn demo() {
    let count = 0;
    set count = count + 1;
  }
  ```

- `while` loops:

  ```roc
  fn demo() {
    let i = 0;
    while i < 3 {
      print(i);
      set i = i + 1;
    }
  }
  ```

- `for` loops over integer ranges:

  ```roc
  fn demo() {
    for i in 0..10 by 2 {
      print(i);
    }
  }
  ```

  Use `start..end` for exclusive ranges or `start..=end` for inclusive ranges.
  Add `by step` to control the step size.

- `break` and `continue` inside loops:

  ```roc
  fn demo() {
    for i in 0..10 {
      if i == 2 { continue; } else { print(i); };
      if i == 5 { break; } else { 0; };
    }
  }
  ```

  ```roc
  fn demo() {
    let i = 0;
    while true {
      set i = i + 1;
      if i == 2 { continue; } else { 0; };
      if i == 4 { break; } else { 0; };
    }
  }
  ```

- `return` statements in functions.
- Expressions:
  - Integer literals: `1`, `42`
  - String literals: `"hello"`
  - Boolean literals: `true`, `false`
  - Record literals: `{x: 1, y: 2}`
  - List literals: `[1, 2, 3]`
  - Unary operators: `-expr`, `!expr`
  - Binary operators: `+`, `-`, `*`, `/`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`, `||`
  - Field access: `expr.field`
  - Indexing: `expr[index]`
  - Parentheses: `(expr)`
  - `if` expressions: `if cond { expr; } else { expr; }`
  - `else if` is supported as sugar for `else { if ... }`
- Function calls: `name(arg1, arg2)`
- Built-in `print(...)` for output.

Types supported by the checker: `Int`, `Bool`, `String`, `Unit`.

Anything else will result in a parse or runtime error.

## Example Roc program

```roc
module main

fn main() {
  let a = 40;
  let b = 2;
  let result = a + b;
  print("Result is " + result);
}
```

This runs on the interpreter and prints:

```text
Result is 42
```

Enjoy experimenting with Roc!

# Greyalien Language (Prototype)

[![CI](https://github.com/JROChub/greyalien-prototype/actions/workflows/ci.yml/badge.svg)](https://github.com/JROChub/greyalien-prototype/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/greyalien-prototype.svg)](https://pypi.org/project/greyalien-prototype/)

This is a **prototype implementation** of the Greyalien language concept:
a new, experimental programming language designed to surpass traditional
systems languages in clarity and safety.

This ZIP includes:

- `SPEC.md` – Greyalien v0 conceptual language design.
- `SPEC_V0.md` – the subset spec implemented by this interpreter.
- `GREYALIEN_CORE.md` – core design principles.
- `GREYALIEN_VISION.md` – long-term vision and roadmap.
- `compiler_architecture.md` – high-level architecture for a future native Greyalien compiler.
- `LICENSE` – MIT license.
- `CONTRIBUTING.md` – contribution guide.
- `CHANGELOG.md` – release notes.
- `RELEASE.md` – release checklist.
- `ROADMAP.md` – v0.2 scope and priorities.
- `TRIAGE.md` – issue triage guide.
- `Makefile` – release helper targets.
- `greyalien/` – a minimal Greyalien interpreter implemented in Python for a **small v0 subset**.
- `examples/` – runnable `.grl` programs.

> Note: The interpreter is intentionally small. It runs a Greyalien *subset* with
> functions, conditionals, loops, records, lists, match expressions, enums,
> imports,
> arithmetic, booleans, and printing. It is meant as a working playground,
> not a production compiler.
>
> A minimal static type checker for `Int`, `Bool`, and `String` runs before
> execution and reports type errors.

## What's new in v0.3.0

- `match` expressions, enums, and enum payloads.
- Module imports with a minimal loader.
- Conformance fixtures and parser fuzz coverage.

## Unreleased (main branch)

- Scoped module namespaces (imports require qualification, e.g. `math.add(...)`).
- Explicit exports (`export { ... }`) control module visibility.
- Exported enums are type-only; variants must be listed explicitly.
- Enum payload bindings in match patterns (for example, `Some(x)`).
- Module-qualified enum types in annotations (for example, `colors.Color`).

## Requirements

- Python 3.9+

## Install from PyPI

```bash
python -m pip install greyalien-prototype
```

Create a file `hello.grl`:

```grl
fn main() {
  print("Hello from Greyalien!");
}
```

Run it:

```bash
greyalien run hello.grl
```

## Install from source

```bash
python -m pip install -e .
```

Then run:

```bash
greyalien run examples/hello.grl
```

## Running examples

From the directory where you unpack the ZIP:

```bash
python -m greyalien.cli examples/hello.grl
```

Or with the unified CLI:

```bash
python -m greyalien run examples/hello.grl
```

You should see:

```text
Hello from Greyalien!
```

Another example:

```bash
python -m greyalien.cli examples/math.grl
```

Or:

```bash
python -m greyalien run examples/math.grl
```

Expected output:

```text
Result is 42
```

Module example with qualified enum types:

```bash
python -m greyalien run examples/modules/type_qual_demo.grl
```

Expected output:

```text
red
```

Logic example:

```bash
python -m greyalien.cli examples/logic.grl
```

For-loop example:

```bash
python -m greyalien.cli examples/for_demo.grl
```

Typed example:

```bash
python -m greyalien.cli examples/typed.grl
```

Record example:

```bash
python -m greyalien.cli examples/records.grl
```

List example:

```bash
python -m greyalien.cli examples/list_demo.grl
```

Match example:

```bash
python -m greyalien.cli examples/match_demo.grl
```

Enum example:

```bash
python -m greyalien.cli examples/enum_demo.grl
```

Enum payload example:

```bash
python -m greyalien.cli examples/enum_payload_demo.grl
```

Module/import example:

```bash
python -m greyalien.cli examples/modules/module_demo.grl
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
python -m greyalien check examples/typed.grl
```

## CLI quick reference

```text
greyalien <file.grl>
greyalien run <file.grl>
greyalien check <file.grl>
greyalien ir <file.grl>
greyalien --all-errors <file.grl>
greyalien run --all-errors <file.grl>
greyalien check --all-errors <file.grl>
greyalien --version
greyalien --help
```

## CLI help example

```bash
greyalien --help
```

```text
Usage:
  greyalien <file.grl>
  greyalien run <file.grl>
  greyalien check <file.grl>
  greyalien ir <file.grl>
  greyalien --all-errors <file.grl>
  greyalien run --all-errors <file.grl>
  greyalien check --all-errors <file.grl>
  greyalien --version
  greyalien --help

Options:
  --all-errors  Show all parse errors instead of the first.
```

## Parse error diagnostics

Use `--all-errors` to report every parse error in one run:

```bash
greyalien check --all-errors examples/for_demo.grl
```

## Subset supported by the interpreter

- Optional `module` declaration (ignored at runtime):

  ```grl
  module main
  ```

- Function definitions:

  ```grl
  fn main() {
    print("Hello");
  }

  fn add(a, b) {
    return a + b;
  }
  ```

- Optional type annotations (checked before execution):

  ```grl
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

  ```grl
  fn demo() {
    let x = 10;
    let y = x * 2;
    print(y);
  }
  ```

- `set` assignments to update existing bindings:

  ```grl
  fn demo() {
    let count = 0;
    set count = count + 1;
  }
  ```

- `while` loops:

  ```grl
  fn demo() {
    let i = 0;
    while i < 3 {
      print(i);
      set i = i + 1;
    }
  }
  ```

- `for` loops over integer ranges:

  ```grl
  fn demo() {
    for i in 0..10 by 2 {
      print(i);
    }
  }
  ```

  Use `start..end` for exclusive ranges or `start..=end` for inclusive ranges.
  Add `by step` to control the step size.

- `break` and `continue` inside loops:

  ```grl
  fn demo() {
    for i in 0..10 {
      if i == 2 { continue; } else { print(i); };
      if i == 5 { break; } else { 0; };
    }
  }
  ```

  ```grl
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

## Example Greyalien program

```grl
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

Enjoy experimenting with Greyalien!

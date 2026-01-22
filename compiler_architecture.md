# Greyalien Compiler Architecture (Conceptual)

This document sketches a future native Greyalien compiler. The current codebase
contains only a small interpreter, but the architecture here assumes a full
compiler written in a systems language like Rust.

---

## 1. Major stages

1. **Front-end**
   - Lexing
   - Parsing
   - AST construction
   - Early desugaring

2. **Middle-end**
   - Name resolution
   - Type inference and checking
   - Ownership / borrow checking
   - Effect analysis
   - IR generation

3. **Back-end**
   - IR optimization
   - Target-specific codegen (via LLVM / Cranelift)
   - Linking (executables, libraries)

4. **Tooling**
   - CLI (`greyalien`)
   - Language Server Protocol (LSP)
   - Formatter, linter, package manager

---

## 2. Front-end

### 2.1. Lexer

- Tokenizes source into identifiers, keywords, literals, operators, and
  punctuation.
- Handles comments and whitespace.
- Produces rich location info (line/column) for diagnostics.

### 2.2. Parser

- Builds an Abstract Syntax Tree (AST) using a recursive-descent or Pratt
  parser.
- Enforces basic syntax rules and recovers from certain errors to continue
  parsing.

### 2.3. AST and desugaring

- AST nodes represent modules, functions, types, statements, expressions.
- Syntactic sugar (certain shorthand forms of `if`, pattern matches, etc.) can
  be lowered to simpler core forms ahead of type checking.

---

## 3. Middle-end

### 3.1. Name resolution

- Resolves identifiers to declarations, abiding by lexical scoping rules.
- Detects undefined variables and conflicting definitions.

### 3.2. Type inference and checking

- Assigns types to expressions via global type inference.
- Verifies that operations are type-correct and trait constraints are satisfied.
- Reports precise, user-friendly type errors.

### 3.3. Ownership and borrow checking

- Tracks ownership of values and references.
- Ensures that references do not outlive their owners.
- Prevents data races and use-after-free in safe code.

### 3.4. Effects

- Uses effect annotations (e.g., `effect [io]`) in function signatures
  to track side effects.
- Helps ensure pure functions remain pure and side effects are explicit.

### 3.5. IR generation

- Translates AST into a lower-level, SSA-like Intermediate Representation.
- This IR is used for optimizations and code generation.

---

## 4. Back-end

### 4.1. Optimization

- Performs classic compiler optimizations:
  - Constant folding
  - Dead code elimination
  - Inlining
  - Loop optimizations
  - Escape analysis and stack allocation

### 4.2. Code generation

- Compiles IR down to machine code via LLVM/Cranelift.
- Handles calling conventions, data layout, and platform-specific details.

### 4.3. Linking

- Produces final build artifacts:
  - Static executables
  - Shared libraries
  - Object files

---

## 5. Tooling

### 5.1. CLI (`greyalien`)

- `greyalien build main.grl`
- `greyalien run main.grl`
- `greyalien fmt` for formatting.
- `greyalien check` for type-checking without building.

### 5.2. Language Server

- Provides IDE integration for:
  - Autocomplete
  - Go-to-definition
  - Hover type info
  - Inline diagnostics

### 5.3. Package manager

- Resolves dependencies and versions.
- Integrates with the build system to produce reproducible builds.

---

## 6. Current prototype

The current interpreter is a very small subset of the full vision:

- It tokenizes and parses basic Greyalien syntax.
- It evaluates a simplified AST using a tree-walk interpreter.
- It supports only integers, strings, functions, conditionals, and printing.

This is intended as a stepping stone toward the full compiler described above.
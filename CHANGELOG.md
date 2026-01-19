# Changelog

## Unreleased

- Add import aliases with module-qualified access to functions and enum variants.
- Allow call expressions on any expression (enables `module.func(...)`).
- Add enum payload bindings in match patterns.
- Scope imports to module namespaces (no global flattening of imported definitions).
- Add explicit `export { ... };` declarations to control module visibility.
- Exported enums no longer implicitly export their variants.
- Allow module-qualified enum types in annotations (for example, `colors.Color`).

## 0.3.0

- Add `match` expressions with literal patterns and `_` wildcard.
- Add enum definitions with variant values and enum pattern matching.
- Add enum payload constructors and payload patterns.
- Add import declarations for single-file modules.
- Add conformance fixtures and parser fuzz coverage.

## 0.2.0

- Records and lists with field access and indexing in the interpreter subset.
- Parser diagnostics with recovery plus `--all-errors`.
- Expanded examples, golden outputs, and automated example tests.
- Documentation updates for specs, roadmap, and contribution flow.
- Packaging polish with a single version source and CI build step.

## 0.1.0

- Initial publishable prototype with parser, interpreter, and type checker.
- Unified CLI (`roc`) plus examples and specs.

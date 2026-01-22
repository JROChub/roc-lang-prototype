# Greyalien Roadmap (Prototype)

This roadmap focuses on the Python interpreter subset and its supporting docs.
For long-term direction, see `GREYALIEN_VISION.md`. For the conceptual language
design, see `SPEC.md`.

## Scope and versioning

- v0.x is a prototype subset. Semantics and syntax can change as the spec
  evolves.
- The goal is correctness, clarity, and teachable error messages over speed.
- Each milestone should keep `SPEC_V0.md` aligned with the interpreter.

## v0.2 goals (target)

P0 (must)

- Records and field access: `{x: 1}` and `p.x` with parser, interpreter, and
  type checker support, plus `SPEC_V0.md` updates.
- Ownership and borrowing draft in `SPEC.md` that defines core terms and rules.
- Effects system sketch in `SPEC.md` covering purity and IO at a minimum.
- Canonical examples with golden outputs and tests that verify them.

P1 (should, if time)

- List literals and indexing with clear runtime bounds errors and type checks.
- Runtime errors include line/column spans with snippet context.
- Parser error recovery for common mistakes (missing semicolons, braces).

## Non-goals for v0.2

- Full ownership/borrow checker implementation.
- Effects implementation or effect handlers.
- Optimizing native compiler, LSP, or package manager.
- Standard library beyond the current `print` built-in.

## Success criteria

- `make test` passes on CI and locally.
- `SPEC_V0.md` matches the interpreter behavior for all v0.2 features.
- At least five examples ship with expected outputs.

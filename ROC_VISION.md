# Roc Vision

Roc is a next-generation systems language that targets the sweet spot between
low-level control and high-level safety. The goal is a language that teams can
trust for foundational infrastructure without sacrificing clarity or velocity.

## North star

- Match or exceed Rust and C++ in safety and performance.
- Make effects, ownership, and concurrency visible and teachable.
- Provide a joyful developer experience with uncompromising tooling.

## What makes Roc different

- Effects are explicit and part of the type system.
- Ownership and borrowing are simplified with region-based reasoning.
- Concurrency is structured, with scoped tasks and safe communication.

## Roadmap (high level)

1. Solidify the core language and module system.
2. Build a fast, precise type and effect checker.
3. Implement ownership and borrow analysis with great diagnostics.
4. Ship a minimal standard library and package manager.
5. Produce an optimizing native compiler and LSP.

## Developer experience goals

- Compiler errors should include "why" and "how to fix".
- Formatting and linting are first-class, not add-ons.
- Fast builds, reproducible outputs, and deterministic tooling.

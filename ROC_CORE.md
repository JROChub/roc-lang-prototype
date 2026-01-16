# Roc Core Principles

Roc aims to be a systems language that is simultaneously safe, expressive, and
pleasant to use. These are the non-negotiable principles that shape the design.

## 1. Safety by default

- No undefined behavior in safe Roc.
- Explicit `unsafe` blocks for low-level escape hatches.
- Memory safety and data-race freedom are enforced by the compiler.

## 2. Clarity over cleverness

- Syntax favors readability and uniformity.
- Features must pay their complexity cost with real user value.
- Error messages should teach, not merely report.

## 3. Explicit effects

- Side effects are visible in function signatures.
- Pure functions stay pure; impure functions declare their capabilities.

## 4. Predictable ownership

- Single-owner semantics with clear, local rules.
- Borrowing is explicit and verifiable.
- Lifetimes should be inferred where possible, never mysterious.

## 5. Small, composable core

- Keep the core language minimal and orthogonal.
- Prefer desugaring to adding new primitives.
- Avoid magic or implicit control flow.

## 6. Structured concurrency

- Concurrency is a first-class, safe construct.
- Task lifetimes are scoped; cancellation is explicit.
- Communication is via typed channels and shared immutable data.

## 7. Performance without compromise

- Zero-cost abstractions where possible.
- Predictable codegen and layout.
- Tooling that makes performance visible and debuggable.

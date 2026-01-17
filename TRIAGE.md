# Issue Triage

This doc explains how we label and route issues so the prototype stays aligned
with the vision and spec.

## Goals

- Keep the backlog actionable and aligned with `ROC_VISION.md` and `SPEC.md`.
- Make clear entry points for contributors.
- Keep implementation and docs in sync.

## Workflow

1. Read the issue and confirm there is a repro or clear scope.
2. Apply a type label: `bug`, `enhancement`, `documentation`, or `question`.
3. Set one primary `area:` label:
   - Prefer the explicit checkbox in the issue template.
   - Otherwise use the auto-labeler output.
   - Add a second area only if the work is truly cross-cutting.
4. Add contributor tags when appropriate:
   - `good first issue` for small, bounded tasks with hints.
   - `help wanted` for tasks needing extra attention or expertise.
5. Assign a milestone if it matches a roadmap item.
6. Close with context and links when duplicate, invalid, or out of scope.

## Labels

### Type

- `bug`: runtime errors, incorrect behavior, crashes.
- `enhancement`: new language or tooling features.
- `documentation`: docs/spec changes or clarifications.
- `question`: needs clarification or discussion.

### Area

- `area: docs`: docs, guides, README.
- `area: spec`: `SPEC.md`, language rules, grammar.
- `area: parser`: parsing, syntax, lexer.
- `area: interpreter`: runtime and evaluation semantics.
- `area: typechecker`: type rules, inference, diagnostics.
- `area: compiler`: IR or compilation pipeline.
- `area: cli`: command-line interface and tools.
- `area: tests`: tests and CI.

### Meta

- `good first issue`
- `help wanted`
- `duplicate`
- `invalid`
- `wontfix`

## Automation

- Auto-labeler runs on issue open/edit/reopen in
  `.github/workflows/issue-labeler.yml`.
- Labels are defined in `.github/labels.yml`; run the Label Sync workflow after
  edits.

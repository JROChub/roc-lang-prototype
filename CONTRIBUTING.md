# Contributing to Roc (Prototype)

Thanks for helping with Roc. This repository is a prototype interpreter plus
design docs, so changes should keep implementation and specs aligned.

## Quick start

1. Fork the repo and create a branch.
2. Make small, focused changes.
3. Run tests:

```bash
python -m unittest discover -s tests
```

4. Update docs and examples when behavior changes.

## Coding guidelines

- Follow the existing formatting and indentation in each file.
- Keep behavior explicit and error messages clear.
- Add tests for new syntax, runtime semantics, and edge cases.
- Keep the subset spec and README in sync with interpreter behavior.

## Doc changes

- If you add or change syntax, update both `SPEC.md` and `SPEC_V0.md`.
- Keep `ROC_CORE.md` and `ROC_VISION.md` aligned with the direction you intend.

## Reporting issues

- Include a small repro program and the expected vs actual output.
- Note the interpreter version (commit hash) when possible.

## Issue triage

- Confirm the report is reproducible or request missing details.
- Apply a type label (`bug`, `enhancement`, `documentation`, or `question`).
- Verify one primary `area:` label; override auto-labeling if needed.
- Add `good first issue` or `help wanted` when appropriate.
- Assign a milestone when the work aligns with the roadmap.
- Close with context if duplicate, invalid, or out of scope.

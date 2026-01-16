# Release Checklist

Use this checklist to cut a new release.

1. Update `CHANGELOG.md`
   - Move items from "Unreleased" into a new version section.
2. Bump version numbers
   - `pyproject.toml`
   - `roc/__init__.py`
3. Run tests
   - `python -m unittest discover -s tests`
4. Tag the release
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
5. Create a GitHub release
   - Use the changelog entry as the release notes.

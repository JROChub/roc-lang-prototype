.PHONY: test release

test:
	python -m unittest discover -s tests

release:
	@echo "1) Update CHANGELOG.md"
	@echo "2) Bump version in pyproject.toml"
	@echo "3) Run: make test"
	@echo "4) Tag and push: git tag vX.Y.Z && git push origin vX.Y.Z"
	@echo "5) Create GitHub release with changelog notes"

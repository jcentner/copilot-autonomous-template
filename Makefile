.PHONY: test test-hooks test-smoke test-all

test: test-hooks

test-hooks:
	cd tests/hooks && python3 -m unittest discover -p "test_*.py" -v

test-smoke:
	bash tests/smoke.sh

test-all: test-hooks test-smoke

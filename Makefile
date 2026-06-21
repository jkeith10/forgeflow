.PHONY: install test lint demo clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

demo:
	bash scripts/demo.sh

clean:
	rm -rf .forgeflow .pytest_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

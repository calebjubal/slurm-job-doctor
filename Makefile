.PHONY: install dev test lint typecheck fmt clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

fmt:
	ruff check --fix .
	ruff format .

typecheck:
	mypy src

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

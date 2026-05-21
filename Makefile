PYTHON ?= $(shell if [ -x .venv/bin/python ]; then printf ".venv/bin/python"; else printf "python"; fi)
PRODUCTPULSE ?= $(PYTHON) -m main

.PHONY: setup run dashboard demo status test lint format typecheck coverage ci clean-cache

setup:
	$(PYTHON) -m pip install -e ".[dev]"

run:
	PYTHONDONTWRITEBYTECODE=1 $(PRODUCTPULSE) run

dashboard:
	PYTHONDONTWRITEBYTECODE=1 $(PRODUCTPULSE) dashboard

demo: run
	PYTHONDONTWRITEBYTECODE=1 $(PRODUCTPULSE) dashboard

status:
	PYTHONDONTWRITEBYTECODE=1 $(PRODUCTPULSE) status

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest

lint:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m ruff check src app tests

format:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m ruff format src app tests

typecheck:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pyrefly check

coverage:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest --cov=src --cov=app --cov-report=term-missing

ci:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m compileall -q src app tests
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m ruff check src app tests
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pyrefly check
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest --cov=src --cov=app --cov-report=term-missing

clean-cache:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .coverage

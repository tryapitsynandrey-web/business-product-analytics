PYTHON ?= $(shell if [ -x .venv/bin/python ]; then printf ".venv/bin/python"; else printf "python"; fi)
PRODUCTPULSE ?= $(PYTHON) -m main

.PHONY: setup run dashboard status test ci clean-cache

setup:
	$(PYTHON) -m pip install -e ".[dev]"

run:
	PYTHONDONTWRITEBYTECODE=1 $(PRODUCTPULSE) run

dashboard:
	PYTHONDONTWRITEBYTECODE=1 $(PRODUCTPULSE) dashboard

status:
	PYTHONDONTWRITEBYTECODE=1 $(PRODUCTPULSE) status

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest

ci:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m compileall -q src app tests
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest

clean-cache:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .coverage

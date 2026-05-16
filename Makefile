PYTHON ?= python

.PHONY: setup run dashboard status test clean-cache

setup:
	$(PYTHON) -m pip install -r requirements.txt

run:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src $(PYTHON) src/main.py run

dashboard:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src $(PYTHON) -m streamlit run app/streamlit_app.py

status:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src $(PYTHON) src/main.py status

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest

clean-cache:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .coverage

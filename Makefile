PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff

.PHONY: install test lint verify demo fundamentals-panel fundamentals-research

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements-lock.txt
	$(PYTHON) -m pip install -e . --no-deps

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	$(RUFF) check .

verify: lint test
	$(PYTHON) scripts/verify_public_repo.py
	$(PYTHON) scripts/run_example_pipeline.py --check

demo:
	$(PYTHON) scripts/run_example_pipeline.py

fundamentals-panel:
	$(PYTHON) scripts/build_point_in_time_fundamental_panel.py

fundamentals-research: fundamentals-panel
	$(PYTHON) scripts/run_point_in_time_fundamental_ablation.py

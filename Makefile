.PHONY: setup test eval demo samples
PYTHON ?= python
setup:
	$(PYTHON) -m pip install -r requirements.txt
test:
	$(PYTHON) -m pytest -q
eval:
	$(PYTHON) -m evals.run_evals --mock
demo:
	$(PYTHON) -m research_agent "Compare the top 3 open-source vector databases for a startup building RAG products." --mock
samples:
	$(PYTHON) scripts/generate_samples.py

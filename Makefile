.PHONY: install export ingest normalize classify enrich pipeline coverage

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

export:
	# Recent sample by default; normalize still filters issued_date >= 2021-01-01
	$(PYTHON) scripts/export_arcgis_sample.py --max-records 5000 --since 2024-01-01

ingest:
	$(PYTHON) scripts/02_ingest.py --jurisdiction fl_miami_dade_county

normalize:
	$(PYTHON) scripts/03_normalize.py --jurisdiction fl_miami_dade_county --replace

classify:
	$(PYTHON) scripts/04_classify.py --jurisdiction fl_miami_dade_county

enrich:
	$(PYTHON) scripts/05_enrich.py --jurisdiction fl_miami_dade_county --geocode-sample 100

pipeline: ingest normalize classify enrich

coverage:
	@python -c "from pathlib import Path; p=Path('data/reference/coverage_fl_miami_dade_county.md'); print(p.read_text() if p.exists() else 'Run make enrich first')"

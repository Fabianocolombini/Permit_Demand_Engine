.PHONY: install export export-full discover probe ingest normalize classify enrich pipeline coverage manifest

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

# Small recent Miami-Dade sample (compat)
export:
	$(PYTHON) scripts/export_arcgis_sample.py --max-records 5000 --since 2024-01-01

# Full post-2021 Tier A extracts (large; CSVs gitignored)
export-full:
	$(PYTHON) scripts/export_permits_csv.py --all-tier-a --since 2021-01-01 --monthly

discover:
	$(PYTHON) scripts/00_discover.py

probe:
	$(PYTHON) scripts/01_probe.py --all

ingest:
	$(PYTHON) scripts/02_ingest.py --jurisdiction fl_miami_dade_county

normalize:
	$(PYTHON) scripts/03_normalize.py --jurisdiction fl_miami_dade_county --replace

classify:
	$(PYTHON) scripts/04_classify.py --jurisdiction fl_miami_dade_county

enrich:
	$(PYTHON) scripts/05_enrich.py --jurisdiction fl_miami_dade_county --geocode-sample 100

pipeline: ingest normalize classify enrich

manifest:
	$(PYTHON) scripts/build_extract_manifest.py

coverage:
	@python -c "from pathlib import Path; p=Path('data/reference/coverage_fl_miami_dade_county.md'); print(p.read_text() if p.exists() else 'Run make enrich first')"

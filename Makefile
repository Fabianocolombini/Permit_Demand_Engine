.PHONY: install export export-full discover probe ingest normalize classify enrich pipeline coverage manifest census material bronze-pipeline valuation

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
	$(PYTHON) scripts/04_classify.py --all

enrich:
	$(PYTHON) scripts/05_enrich.py --jurisdiction fl_miami_dade_county --geocode-sample 100

pipeline: ingest normalize classify enrich

# Ingest+normalize+classify every Tier A bronze CSV present on disk
tier-a-pipeline:
	$(PYTHON) scripts/run_tier_a_pipeline.py

# Tier A + open Tier B bronze → silver → classify (excludes Shovels stubs)
bronze-pipeline:
	$(PYTHON) scripts/run_bronze_pipeline.py --exclude fl_cape_coral_city --exclude fl_manatee_active_residential

census:
	$(PYTHON) scripts/06_census.py

valuation:
	$(PYTHON) scripts/report_valuation_tom_sam.py

material:
	$(PYTHON) scripts/07_model_material.py

manifest:
	$(PYTHON) scripts/build_extract_manifest.py

coverage:
	@python -c "from pathlib import Path; p=Path('data/reference/bps_bronze_coverage_fl.md'); print(p.read_text() if p.exists() else 'Run make census first')"

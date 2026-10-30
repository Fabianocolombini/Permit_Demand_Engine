# Permit Demand Engine

Turn Florida building permits into fittings demand signals for a Tigre / Dura demo.

**This PR (slice 1):** greenfield scaffold + **CSV/XLS file ingest** for Miami-Dade → normalize → DuckDB `silver.permits`. Map/Streamlit, statewide discovery, and Tier C imputation are deferred.

Source of truth for structure/schema: V1.1 statewide FL spec (project docs). Scope here is Miami-Dade unincorporated only; statewide waves come later.

---

## Hard decisions (this slice)

| Topic | Decision |
|---|---|
| Ingest | **CSV/XLS first** (`src/ingest/file_csv.py`). Live ArcGIS/Socrata connectors deferred. |
| Identity | `PermitNumber` → `permit_id` |
| ZIP | Site/city ZIP from address or geocode — **never** `ContractorZip` |
| Valuation | `EstimatedValue` parsed as **USD dollars** (string → float) |
| Window | Post-pandemic from **2021-01-01** (configurable in `config/`) |
| UI | No Streamlit / map yet |

---

## Layout

```
config/           jurisdictions.yaml, assumptions.yaml, taxonomy.yaml
src/ingest/       file_csv.py (primary); arcgis/socrata stubs deferred
src/normalize/    Pydantic Permit + field_map mapper
src/classify/     regex rules stub
src/enrich/       Census batch geocode helper + coverage stats
scripts/          export_arcgis_sample, 02_ingest, 03_normalize, 04_classify, 05_enrich
data/bronze/      preferred local file drop (per jurisdiction_id)
data/raw/         alternate drop / bootstrap exports
data/reference/   schema & coverage reports
calibration/      actual_sales stub
permits.duckdb    local DuckDB (gitignored)
```

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Bootstrap a manageable recent sample from the public FeatureServer → CSV
python3 scripts/export_arcgis_sample.py --max-records 5000 --since 2024-01-01
# Writes: data/bronze/fl_miami_dade_county/miami_dade_sample.csv
# Post-pandemic full window: --since 2021-01-01 (huge — raise --max-records / paginate).
# Normalize still keeps issued_date >= 2021-01-01 via config.

# Or drop your own CSV/XLS into data/bronze/fl_miami_dade_county/ (or data/raw/…).

# 2) File ingest → stage JSONL
python3 scripts/02_ingest.py --jurisdiction fl_miami_dade_county

# 3) Normalize → silver.permits (DuckDB)
python3 scripts/03_normalize.py --jurisdiction fl_miami_dade_county --replace

# 4) Optional classify + geography enrich (Census sample for missing site ZIP)
python3 scripts/04_classify.py --jurisdiction fl_miami_dade_county
python3 scripts/05_enrich.py --jurisdiction fl_miami_dade_county --geocode-sample 100
```

Or: `make install && make export && make pipeline`

### XLS / custom files

```bash
# Place files under data/bronze/fl_miami_dade_county/*.xlsx (or *.csv)
python3 scripts/02_ingest.py --jurisdiction fl_miami_dade_county
python3 scripts/03_normalize.py --jurisdiction fl_miami_dade_county --replace
```

Column names should match the ArcGIS Hub table (or adjust `field_map` in `config/jurisdictions.yaml`).

---

## Config

- `config/jurisdictions.yaml` — Miami-Dade entry with `connector: file`, FeatureServer URL documented for later live pull, and `field_map` from the probed schema report.
- `config/assumptions.yaml` — material/timing/logistics stubs (V1.1); window defaults.
- Filters: `--since` on normalize, or `issued_date_min` on the jurisdiction / `window.issued_date_min` in assumptions.

---

## Limitations (honest)

- **Unincorporated Miami-Dade only** — Hub layer does not cover incorporated cities.
- **No native geometry / site ZIP** on the chosen FeatureServer table; city is present. Site ZIP may be parsed from address text or filled for a **small Census geocode sample**; `ContractorZip` is ignored.
- Live API connectors, statewide 67-county discovery, Tier C imputation, Streamlit/map: **not in this PR**.
- Sample export caps rows by default (`--max-records 5000`) so bootstrap stays manageable.

---

## DuckDB

After normalize:

```sql
SELECT COUNT(*), 
       AVG(zip IS NOT NULL)::DOUBLE AS pct_zip_approx,
       AVG(declared_valuation IS NOT NULL)::DOUBLE AS pct_val
FROM silver.permits
WHERE jurisdiction_id = 'fl_miami_dade_county';
```

DB file: `permits.duckdb` (local, gitignored).

# Permit Demand Engine

Turn Florida building permits into fittings demand signals for **Tigre × Dura**.

## Executive dashboard

Next.js app in [`dashboard/`](dashboard/) — TOM / SAM / SOM analytics for Florida (permits ≥ 2021).

```bash
# Rebuild DuckDB from bronze CSVs, then metrics JSON
python3 scripts/run_bronze_pipeline.py \
  --exclude fl_cape_coral_city --exclude fl_manatee_active_residential
python3 scripts/07_model_material.py
python3 scripts/build_dashboard_metrics.py

cd dashboard && npm install && npm run dev
```

Deploy: set Vercel **Root Directory** to `dashboard/`, or `cd dashboard && npx vercel --prod`.

Metrics ship as static `dashboard/public/data/metrics.json` (DuckDB stays local / gitignored).

---

## Hard decisions

| Topic | Decision |
|---|---|
| Extract first | Dump **raw/full** permits to CSV under `data/bronze/<id>/` before classify |
| Identity | `PermitNumber` (or local equivalent) |
| ZIP | Site/city ZIP from address/geocode — **never** contractor ZIP |
| Valuation | USD dollars; missing → peer median (category×county) |
| Window | Issued ≥ **2021-01-01** |
| TOM / SAM / SOM | TOM = all permits; SAM = plumbing + pool/spa + irrigation + new residential; SOM = 5% of SAM $ |
| No paid Shovels | Open ArcGIS / Socrata / file dumps only |

---

## Pipeline

```bash
python3 -m pip install -r requirements.txt
python3 scripts/export_permits_csv.py --jurisdiction fl_miami_dade_county --since 2021-01-01
python3 scripts/02_ingest.py --jurisdiction fl_miami_dade_county
python3 scripts/03_normalize.py --jurisdiction fl_miami_dade_county --replace
python3 scripts/04_classify.py --all
python3 scripts/07_model_material.py
python3 scripts/build_dashboard_metrics.py
```

Large bronze CSVs are gitignored; commit scripts, sample previews, and reference manifests.

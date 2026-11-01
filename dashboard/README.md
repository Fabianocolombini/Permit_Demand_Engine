# Tigre × Dura — Florida Permit Demand Engine (dashboard)

Executive Next.js dashboard answering TOM / SAM / SOM questions for Florida permits.

## Local

```bash
# From repo root — rebuild DuckDB + metrics when bronze CSVs exist
python3 scripts/run_bronze_pipeline.py --exclude fl_cape_coral_city --exclude fl_manatee_active_residential
python3 scripts/07_model_material.py
python3 scripts/build_dashboard_metrics.py

cd dashboard && npm install && npm run dev
```

## Deploy

Root of the Vercel project should be `dashboard/`. Static metrics ship in `public/data/metrics.json`.

```bash
cd dashboard && npx vercel --prod
```

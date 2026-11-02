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

## CARTO

API base (Workspace → Developers): `https://gcp-us-east1.api.carto.com`

Copy `.env.example` → `.env.local` (and Vercel project env) and set:

- `CARTO_API_BASE` — already defaults to the host above
- `CARTO_ACCESS_TOKEN` — API Access Token (Maps + SQL)
- `CARTO_CONNECTION_NAME` — optional, default `carto_dw`

County choropleth uses CARTO dark basemap tiles + local FL GeoJSON + demand metrics.  
Status endpoint: `GET /api/carto/status` (never returns the token).

## Deploy

Root of the Vercel project should be `dashboard/`. Static metrics ship in `public/data/metrics.json`.

```bash
cd dashboard && npx vercel --prod
```

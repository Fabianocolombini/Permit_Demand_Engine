# Permit Demand Engine

Turn Florida building permits into fittings demand signals for a Tigre / Dura demo.

**This PR:** robust ArcGIS + Socrata CSV extract for Onda 1 Tier A jurisdictions (post-2021), expanded `jurisdictions.yaml`, extract manifest + sample preview. Streamlit/map deferred.

---

## Hard decisions

| Topic | Decision |
|---|---|
| Extract first | Dump **raw/full** permits to CSV under `data/bronze/<id>/` before classify |
| Identity | `PermitNumber` (or local equivalent) |
| ZIP | Site/city ZIP from address/geocode — **never** contractor ZIP |
| Valuation | USD dollars |
| Window | Issued ≥ **2021-01-01** (configurable) |
| Miami-Dade Hub | **Unincorporated only** — City of Miami is a separate feed |
| Large files | Bronze CSVs gitignored; commit scripts + preview + manifest |

---

## Quick start

```bash
python3 -m pip install -r requirements.txt

# Probe curated Onda 1 candidates
python3 scripts/00_discover.py
python3 scripts/01_probe.py --all

# Full post-2021 extract for one or all Tier A jurisdictions
python3 scripts/export_permits_csv.py --jurisdiction fl_miami_dade_county --monthly
python3 scripts/export_permits_csv.py --all-tier-a --since 2021-01-01 --monthly

# Build markdown manifest from bronze *_extract_meta.json
python3 scripts/build_extract_manifest.py
```

Optional file → DuckDB path (from prior scaffold):

```bash
python3 scripts/02_ingest.py --jurisdiction fl_miami_dade_county
python3 scripts/03_normalize.py --jurisdiction fl_miami_dade_county --replace
```

---

## Tier A extracts in this wave

See `data/reference/extract_manifest.md` for row counts, date spans, and absolute CSV paths.

| ID | Source | Covers |
|---|---|---|
| `fl_miami_dade_county` | ArcGIS Hub table | Unincorporated only |
| `fl_miami_city` | City of Miami AGOL | City |
| `fl_orlando_city` | Socrata | City |
| `fl_hillsborough_county` | TPC MapServer | Full county (multi-jurisdiction labels) |
| `fl_cape_coral_city` | Cape Coral MapServer | Active permits (city) |
| `fl_broward_county` | HCED Posse points | Small / engineering-leaning subset |
| `fl_manatee_active_residential` | Manatee MapServer | Active residential only |

**Tier B (blocked — no open record API found quickly):** Palm Beach building, Orange County unincorporated, Duval/Jacksonville, Pinellas, Lee unincorporated, Polk, Brevard, Volusia, Pasco, Osceola, Sarasota, full Broward BCS.

---

## Layout

```
config/jurisdictions.yaml     Onda 1 registry (Tier A + B stubs)
src/ingest/arcgis.py          paginated FeatureServer/MapServer client
src/ingest/socrata.py         SODA client
scripts/export_permits_csv.py full CSV dump (monthly slices, retry)
scripts/00_discover.py        curated endpoint probe
scripts/01_probe.py           registry probe
data/bronze/<id>/             large CSVs (gitignored) + sample_preview.csv
data/reference/               extract_manifest.md, probe JSON, committed preview
```

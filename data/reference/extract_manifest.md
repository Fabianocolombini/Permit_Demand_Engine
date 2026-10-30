# Permit extract manifest — Florida Onda 1

Generated: 2026-10-30 17:09 UTC · Updated: 2026-10-30 17:35 UTC (Shovels connector)

Window: **issued ≥ 2021-01-01** (post-pandemic). Raw/full permits — no market classification filter.

## Completed extracts (Tier A)

| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |
|---|---|---:|---|---|---|---:|---|
| fl_broward_county | unknown | 2,350 | 2021-01-06 | 2026-10-29 | `/workspace/data/bronze/fl_broward_county/fl_broward_county_permits_2021-01-01_20261030.csv` | 2.1 MB | Geocoded HCED Posse permits (Broward). Small universe (~7.4k total / ~2.3k post-2021) — appears skewed to engineering/ROW-style jobs (e.g. driveway), not full A |
| fl_cape_coral_city | city | 14,385 | 2021-01-04 | 2026-10-30 | `/workspace/data/bronze/fl_cape_coral_city/fl_cape_coral_city_permits_2021-01-01_20261030.csv` | 7.9 MB | Active Building Permits layer (polygons) — not a full historical archive. ~14.5k active; nearly all issued >= 2021. Lee County unincorporated still Tier B. Site |
| fl_hillsborough_county | full_county | 40,329 | 2021 | 2026 | `/workspace/data/bronze/fl_hillsborough_county/fl_hillsborough_county_permits_2021-01-01_20261030.csv` | 35.5 MB | Hillsborough Planning Commission layer labeled with jurisdictions including Hillsborough County, Tampa, Plant City, Temple Terrace — treat as full_county until  |
| fl_manatee_active_residential | unknown | 4,357 | 2021-01-05 | 2026-10-29 | `/workspace/data/bronze/fl_manatee_active_residential/fl_manatee_active_residential_permits_2021-01-01_20261030.csv` | 0.9 MB | Active residential permits only (MapServer layer 0). Not full historical Manatee feed — portal/webapp Tier B for complete history. |
| fl_miami_city | city | 169,827 | 2021-01-01 | 2026-10-29 | `/workspace/data/bronze/fl_miami_city/fl_miami_city_permits_2021-01-01_20261030.csv` | 91.8 MB | City of Miami Building Department permits since 2014 (owner CityMiamiFL). Complements Miami-Dade unincorporated Hub. Attributes include Miami21Zone. IssuedDate  |
| fl_miami_dade_county | unincorporated_only | 420,160 | 2021-01-01 | 2026-10-26 | `/workspace/data/bronze/fl_miami_dade_county/fl_miami_dade_county_permits_2021-01-01_20261030.csv` | 195.9 MB | Unincorporated county only — incorporated cities (Miami, Hialeah, etc.) emit separately. Hub table has no native geometry or site ZIP; never use ContractorZip.  |
| fl_orlando_city | city | 191,615 | 2021-01-01 | 2026-10-30 | `/workspace/data/bronze/fl_orlando_city/fl_orlando_city_permits_2021-01-01_20261030.csv` | 98.2 MB | Socrata Permit Applications. City of Orlando only — Orange County unincorporated (FastTrack portal) is Tier B. Post-2021 ≈192k rows (probed). |

## Shovels Tier B extracts (connector wired; pulls blocked)

| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |
|---|---|---:|---|---|---|---:|---|
| fl_palm_beach_county | full_county | — | — | — | — | — | `connector: shovels` · county_q=Palm Beach · **not pulled** |
| fl_orange_county | full_county | — | — | — | — | — | `connector: shovels` · county_q=Orange · **not pulled** |
| fl_duval_jacksonville | full_county | — | — | — | — | — | `connector: shovels` · county_q=Duval · **not pulled** |
| fl_pinellas_county | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_lee_county | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_polk_county | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_brevard_county | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_volusia_county | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_pasco_county | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_osceola_county | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_sarasota_county | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_broward_full_building | full_county | — | — | — | — | — | `connector: shovels` · **not pulled** |
| fl_cape_coral_shovels | city | — | — | — | — | — | city_q=Cape Coral historical backfill · **not pulled** |
| fl_manatee_county_shovels | full_county | — | — | — | — | — | county historical backfill · **not pulled** |

**Blocker:** `SHOVELS_API_KEY` length = **0** on this agent VM (secret configured on the environment after boot / not injected into this warm-fork). Re-run on a fresh agent with the secret present:

```bash
python3 scripts/export_shovels.py --check-key
python3 scripts/export_shovels.py --tier-b --backfill-active-only --since 2021-01-01
```

**Plan / quota notes (from Shovels docs):** Free API = **500 credits / rolling 30 days** (1 credit = 1 record returned). Full Onda 1 Tier B history will need a paid plan (likely **100k–1M+ credits** depending on county volumes). API returns HTTP **402** when exhausted; connector stops and records partial CSVs. Rate limit = HTTP **429** with backoff. Free API includes full historical date range (Online free UI is 12 months only).

## Endpoint reference

| Jurisdiction | Connector | URL |
|---|---|---|
| fl_broward_county | arcgis | https://bcgishub.broward.org/posse/rest/services/HCED/HCEDPossePermitsRef/FeatureServer/4 |
| fl_cape_coral_city | arcgis | https://capeims.capecoral.gov/arcgis/rest/services/AGOL/Building_Permits_Map/MapServer/1 |
| fl_hillsborough_county | arcgis | https://gis.tpcmaps.org/arcgis/rest/services/Websites/BuildingPermits/MapServer/1 |
| fl_manatee_active_residential | arcgis | https://www.mymanatee.org/gisbads/rest/services/Permit/ActiveBuildingPermits/MapServer/0 |
| fl_miami_city | arcgis | https://services1.arcgis.com/CvuPhqcTQpZPT9qY/arcgis/rest/services/Building_Permits_Since_2014/FeatureServer/0 |
| fl_miami_dade_county | arcgis | https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0 |
| fl_orlando_city | socrata | https://data.cityoforlando.net/resource/ryhf-m453.json |
| fl_* Tier B (14) | shovels | https://api.shovels.ai/v2/permits/search (geo via /counties\|/cities/search) |

## Coverage caveats

- **Miami-Dade Hub = unincorporated only.** City of Miami is a separate extract (`fl_miami_city`).
- **Cape Coral / Manatee ArcGIS layers are Active permits**, not full historical archives — Shovels backfill IDs above preferred once key is live. Manatee ArcGIS `Permit/permitlinks` PermitData (~554k) is a strong non-Shovels fallback (see portal discovery note).
- **Broward HCED Posse** is a small geocoded subset; full volume targeted via `fl_broward_full_building` Shovels pull.
- Orange County Shovels county geo may overlap Orlando Tier A — dedupe before gold.

## Preview CSVs

Each bronze folder has `sample_preview.csv` (≤100 rows). A combined committed preview lives at
`data/reference/sample_preview.csv` (Miami-Dade first 100).

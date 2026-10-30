# Permit extract manifest — Florida Onda 1 (Path B)

Generated: 2026-10-30 18:28 UTC · Path B: Tier A + Manatee PermitData (no paid Shovels)

Window: **issued ≥ 2021-01-01** (post-pandemic). Raw/full permits — no market classification filter at extract time.

## TOM / SAM (after classify)

- **TOM** = total permits ingested (raw universe in `silver.permits`).
- **SAM** = Tigre/Dura subset: plumbing (new/repipe/remodel) **including new residential construction** (implied rough-in) + pool/spa + irrigation. Excludes roof/windows/AC-only/fence noise.

**Overall:** TOM **1,089,121** · SAM **301,667** · SAM/TOM **27.7%**

| Jurisdiction | TOM | SAM | SAM/TOM % |
|---|---:|---:|---:|
| fl_miami_dade_county | 420,160 | 111,147 | 26.45 |
| fl_miami_city | 169,827 | 41,956 | 24.71 |
| fl_broward_county | 2,350 | 16 | 0.68 |
| fl_hillsborough_county | 38,632 | 26,367 | 68.25 |
| fl_orlando_city | 191,566 | 36,652 | 19.13 |
| fl_cape_coral_city | 14,385 | 3,504 | 24.36 |
| fl_manatee_active_residential | 4,355 | 0 | 0.0 |
| fl_manatee_county | 247,846 | 82,025 | 33.1 |
| **TOTAL** | **1,089,121** | **301,667** | **27.7** |

SAM category mix: res_new_plumbing=222,623, pool_spa=68,771, irrigation=7,556, res_remodel_plumbing=1,893, res_repipe=824

> Note: `fl_manatee_active_residential` overlaps `fl_manatee_county` (Prefer PermitData for history). Active layer has weak type text → SAM≈0; full Manatee drives SAM.

## Completed extracts (Tier A)

| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |
|---|---|---:|---|---|---|---:|---|
| fl_broward_county | unknown | 2,350 | 2021-01-06 | 2026-10-29 | `/workspace/data/bronze/fl_broward_county/fl_broward_county_permits_2021-01-01_20261030.csv` | 2.1 MB | Geocoded HCED Posse permits (Broward). Small universe (~7.4k total / ~2.3k post-2021) — appears skewed to engineering/ROW-style jobs (e.g. driveway), not full A |
| fl_cape_coral_city | city | 14,385 | 2021-01-04 | 2026-10-30 | `/workspace/data/bronze/fl_cape_coral_city/fl_cape_coral_city_permits_2021-01-01_20261030.csv` | 7.9 MB | Active Building Permits layer (polygons) — not a full historical archive. ~14.5k active; nearly all issued >= 2021. Lee County unincorporated still Tier B. Site |
| fl_hillsborough_county | full_county | 40,329 | 2021 | 2026 | `/workspace/data/bronze/fl_hillsborough_county/fl_hillsborough_county_permits_2021-01-01_20261030.csv` | 35.5 MB | Hillsborough Planning Commission layer labeled with jurisdictions including Hillsborough County, Tampa, Plant City, Temple Terrace — treat as full_county until  |
| fl_manatee_active_residential | unknown | 4,357 | 2021-01-05 | 2026-10-29 | `/workspace/data/bronze/fl_manatee_active_residential/fl_manatee_active_residential_permits_2021-01-01_20261030.csv` | 0.9 MB | Active residential permits only (MapServer layer 0). Prefer fl_manatee_county (PermitData table) for full post-2021 history. |
| fl_manatee_county | full_county | 247,953 | 2021-01-01 | 2026-10-29 | `/workspace/data/bronze/fl_manatee_county/fl_manatee_county_permits_2021-01-01_20261030.csv` | 121.7 MB | Permit/permitlinks MapServer table PermitData (~555k total; ~248k issued >= 2021). ISSUED is ISO text (YYYY-MM-DD). No native geometry or site ZIP — compose ADD |
| fl_miami_city | city | 169,827 | 2021-01-01 | 2026-10-29 | `/workspace/data/bronze/fl_miami_city/fl_miami_city_permits_2021-01-01_20261030.csv` | 91.8 MB | City of Miami Building Department permits since 2014 (owner CityMiamiFL). Complements Miami-Dade unincorporated Hub. Attributes include Miami21Zone. IssuedDate  |
| fl_miami_dade_county | unincorporated_only | 420,160 | 2021-01-01 | 2026-10-26 | `/workspace/data/bronze/fl_miami_dade_county/fl_miami_dade_county_permits_2021-01-01_20261030.csv` | 195.9 MB | Unincorporated county only — incorporated cities (Miami, Hialeah, etc.) emit separately. Hub table has no native geometry or site ZIP; never use ContractorZip.  |
| fl_orlando_city | city | 191,615 | 2021-01-01 | 2026-10-30 | `/workspace/data/bronze/fl_orlando_city/fl_orlando_city_permits_2021-01-01_20261030.csv` | 98.2 MB | Socrata Permit Applications. City of Orlando only — Orange County unincorporated (FastTrack portal) is Tier B. Post-2021 ≈192k rows (probed). |

## Endpoint reference

| Jurisdiction | Connector | URL |
|---|---|---|
| fl_broward_county | arcgis | https://bcgishub.broward.org/posse/rest/services/HCED/HCEDPossePermitsRef/FeatureServer/4 |
| fl_cape_coral_city | arcgis | https://capeims.capecoral.gov/arcgis/rest/services/AGOL/Building_Permits_Map/MapServer/1 |
| fl_hillsborough_county | arcgis | https://gis.tpcmaps.org/arcgis/rest/services/Websites/BuildingPermits/MapServer/1 |
| fl_manatee_active_residential | arcgis | https://www.mymanatee.org/gisbads/rest/services/Permit/ActiveBuildingPermits/MapServer/0 |
| fl_manatee_county | arcgis | https://www.mymanatee.org/gisbads/rest/services/Permit/permitlinks/MapServer/1 |
| fl_miami_city | arcgis | https://services1.arcgis.com/CvuPhqcTQpZPT9qY/arcgis/rest/services/Building_Permits_Since_2014/FeatureServer/0 |
| fl_miami_dade_county | arcgis | https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0 |
| fl_orlando_city | socrata | https://data.cityoforlando.net/resource/ryhf-m453.json |

## Coverage caveats

- **Miami-Dade Hub = unincorporated only.** City of Miami is a separate extract (`fl_miami_city`).
- **Manatee PermitData** (`fl_manatee_county`) is the Path B full-history ArcGIS table (~248k issued ≥ 2021); Active residential layer kept for reference only.
- **Cape Coral** Active Building Permits — not a full historical archive (Shovels deferred).
- **Broward HCED Posse** is a small geocoded subset; full BCS still Tier B (Shovels deferred — quota exhausted).
- Paid Shovels Tier B pull **skipped** (path B).

## Preview CSVs

Each bronze folder has `sample_preview.csv` (≤100 rows). Classification report: `data/reference/classification_report.md`.


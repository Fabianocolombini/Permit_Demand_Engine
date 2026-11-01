# Permit extract manifest — Florida Onda 1 (Path B + open Tier B)

Generated: 2026-11-01 02:00 UTC · Path B: no paid Shovels · maximize remaining Tier B open fills from PR #5 tip

Window: **issued ≥ 2021-01-01** (post-pandemic). Raw/full permits — no market classification filter at extract time.

## TOM / SAM (Tier A only — classify not re-run this turn)

- **TOM** = total permits ingested (raw universe in `silver.permits`).
- **SAM** = Tigre/Dura subset: plumbing (new/repipe/remodel) **including new residential construction** (implied rough-in) + pool/spa + irrigation. Excludes roof/windows/AC-only/fence noise.

**Tier A (unchanged from PR #4):** TOM **1,089,121** · SAM **301,667** · SAM/TOM **27.7%**

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

## New open Tier B bronze (this PR — maximize remaining gaps)

| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |
|---|---|---:|---|---|---|---:|---|
| fl_cape_coral_history | city | 278,636 | 2021-01-04 | 2026-11-01 | `/workspace/data/bronze/fl_cape_coral_history/fl_cape_coral_history_permits_2021-01-01_20261101.csv` | 67.5 MB | Official All Issued Permits Excel 2021–2025 + OpenData MapServer/1 merge; deduped by permit_number. Closes Cape Coral history gap. |
| fl_pasco_permit_job_values | unknown | 20,495 | ~2024-05 | ~2025-05 | `/workspace/data/bronze/fl_pasco_permit_job_values/fl_pasco_permit_job_values_permits_2021-01-01_20261101.csv` | 15.3 MB | Pasco Performance Management geocode (May24–May25 window). Opaque `user_col_*` fields. |
| fl_osceola_new_construction | unknown | 4,639 | 2021+ | 2026-10 | `/workspace/data/bronze/fl_osceola_new_construction/fl_osceola_new_construction_permits_2021-01-01_20261101.csv` | 2.2 MB | Osceola AGOL new-construction **P** permits. |
| fl_osceola_new_construction_a | unknown | 1,341 | 2024-12 | 2026-10 | `/workspace/data/bronze/fl_osceola_new_construction_a/fl_osceola_new_construction_a_permits_2021-01-01_20261101.csv` | 0.7 MB | Osceola AGOL new-construction **A** permits. |
| fl_boca_raton_city | city | 1,026 | 2021-01 | 2022-05 | `/workspace/data/bronze/fl_boca_raton_city/fl_boca_raton_city_permits_2021-01-01_20261101.csv` | 0.2 MB | Boca Raton SunGard — **stale through mid-2022**. Thin Palm Beach city fill. |
| **NEW THIS PR** | | **306,137** | | | | | Classify / TOM+SAM not re-run. |

## Prior open Tier B bronze (PR #5 — still on disk)

| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |
|---|---|---:|---|---|---|---:|---|
| fl_pinellas_county | full_county | 583,918 | 2021-01-01 | 2026-10-08 | `/workspace/data/bronze/fl_pinellas_county/fl_pinellas_county_permits_2021-01-01_20261101.csv` | 68.1 MB | PCPAO RP_PERMITS bulk ZIP |
| fl_fort_lauderdale_city | city | 204,760 | 2021-03-18 | 2026-03-16 | `/workspace/data/bronze/fl_fort_lauderdale_city/fl_fort_lauderdale_city_permits_2021-01-01_20261101.csv` | 65.0 MB | FTL FeatureServer (SUBMITDT) |
| fl_lakeland_city | city | 26,090 | 2021-01-04 | 2025-06-25 | `/workspace/data/bronze/fl_lakeland_city/fl_lakeland_city_permits_2021-01-01_20261101.csv` | 7.6 MB | Lakeland IMS |
| fl_palm_bay_city | city | 20,313 | 2021-01-04 | 2022-05-31 | `/workspace/data/bronze/fl_palm_bay_city/fl_palm_bay_city_permits_2021-01-01_20261101.csv` | 3.5 MB | Stale → mid-2022 |
| fl_lee_new_sf_auburn | unknown | 7,435 | 2021+ | 2022+ | `/workspace/data/bronze/fl_lee_new_sf_auburn/fl_lee_new_sf_auburn_permits_2021-01-01_20261101.csv` | 3.1 MB | Auburn new-SF only |
| fl_volusia_active_permits | unknown | 2,851 | 2021-01-22 | 2026-10-30 | `/workspace/data/bronze/fl_volusia_active_permits/fl_volusia_active_permits_permits_2021-01-01_20261101.csv` | 1.7 MB | AMANDA open/current only |
| fl_sarasota_new_sf_auburn | unknown | 491 | 2021+ | 2022+ | `/workspace/data/bronze/fl_sarasota_new_sf_auburn/fl_sarasota_new_sf_auburn_permits_2021-01-01_20261101.csv` | 0.2 MB | Auburn new-SF only |
| **PR #5 SUBTOTAL** | | **845,858** | | | | | |

**Cumulative open Tier B bronze (PR #5 + this PR):** **1,151,995** rows (no Shovels).

## Completed extracts (Tier A — prior)

| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |
|---|---|---:|---|---|---|---:|---|
| fl_broward_county | unknown | 2,350 | 2021-01-06 | 2026-10-29 | `/workspace/data/bronze/fl_broward_county/fl_broward_county_permits_2021-01-01_20261030.csv` | 2.1 MB | HCED Posse subset |
| fl_cape_coral_city | city | 14,385 | 2021-01-04 | 2026-10-30 | `/workspace/data/bronze/fl_cape_coral_city/fl_cape_coral_city_permits_2021-01-01_20261030.csv` | 7.9 MB | Active only — prefer history |
| fl_hillsborough_county | full_county | 40,329 | 2021 | 2026 | `/workspace/data/bronze/fl_hillsborough_county/fl_hillsborough_county_permits_2021-01-01_20261030.csv` | 35.5 MB | Planning Commission layer |
| fl_manatee_active_residential | unknown | 4,357 | 2021-01-05 | 2026-10-29 | `/workspace/data/bronze/fl_manatee_active_residential/fl_manatee_active_residential_permits_2021-01-01_20261030.csv` | 0.9 MB | Prefer PermitData |
| fl_manatee_county | full_county | 247,953 | 2021-01-01 | 2026-10-29 | `/workspace/data/bronze/fl_manatee_county/fl_manatee_county_permits_2021-01-01_20261030.csv` | 121.7 MB | PermitData table |
| fl_miami_city | city | 169,827 | 2021-01-01 | 2026-10-29 | `/workspace/data/bronze/fl_miami_city/fl_miami_city_permits_2021-01-01_20261030.csv` | 91.8 MB | City of Miami |
| fl_miami_dade_county | unincorporated_only | 420,160 | 2021-01-01 | 2026-10-26 | `/workspace/data/bronze/fl_miami_dade_county/fl_miami_dade_county_permits_2021-01-01_20261030.csv` | 195.9 MB | Unincorporated only |
| fl_orlando_city | city | 191,615 | 2021-01-01 | 2026-10-30 | `/workspace/data/bronze/fl_orlando_city/fl_orlando_city_permits_2021-01-01_20261030.csv` | 98.2 MB | City only — Orange uninc Tier B |

## Endpoint reference (new this PR)

| Jurisdiction | Connector | URL |
|---|---|---|
| fl_cape_coral_history | file (Excel) + arcgis | https://www.capecoral.gov/departments/development_services/building_permit_reports/index.php · OpenData MapServer/1 |
| fl_pasco_permit_job_values | arcgis | https://pascogis.pascocountyfl.net/giswebeserver/rest/services/Hosted/Performance_Mgt_ECON_gdb/FeatureServer/0 |
| fl_osceola_new_construction | arcgis | https://services6.arcgis.com/9zKHLCgIwu2HFA5O/arcgis/rest/services/New_Construction_P_Permits/FeatureServer/6 |
| fl_osceola_new_construction_a | arcgis | https://services6.arcgis.com/9zKHLCgIwu2HFA5O/arcgis/rest/services/New_Construction_A_Permits/FeatureServer/7 |
| fl_boca_raton_city | arcgis | https://bocagis.ci.boca-raton.fl.us/gisweb/rest/services/Basemap/SunGard/MapServer/0 |

Helper: `scripts/export_cape_coral_history.py`.

## Remaining blockers (honest)

| Gap | Status |
|---|---|
| **Palm Beach building (full)** | Still no county building FeatureServer. ePZB portal; ENG EPERMIT_DATA = ROW/utility. PAO Permit_Portal item points at unreachable internal host (`giswebdev104lb.pbcgov.org`). Boca city (~1k, stale→2022) is only open city fill found. |
| **Orange unincorporated** | OC FastTrack HTML only; Orlando Socrata already Tier A. Hub/FTP permit bulk not found from this VM. |
| **Duval / Jacksonville** | JAXEPICS / Click2Gov portal; `data.coj.net` DNS fail; Hub requires sign-in; no public FeatureServer. |
| **Lee unincorporated full** | Accela LEECO portal; DCD “Building Permits” layer 22 only ~3 rows ≥2021 (stale/corrupt dates). Auburn new-SF (~7.4k) + Cape Coral history remain the open fills. |
| **Polk full** | Accela polkco portal; only Lakeland city open (~26k). |
| **Brevard full** | Accela BASS portal; Palm Bay city open but **stale through 2022**. |
| **Volusia full** | Only AMANDA current/open (~2.8k). Open_Data_* folders have no permit record layers. |
| **Pasco full** | Accela CapHome only for bulk history. Performance job-values layer is **May24–May25 only** (~20k). PascoAccela_OP = basemap/zones. |
| **Osceola full** | Accela CapHome for full volume. AGOL new-construction P+A (~6k) is a thin supplement only. |
| **Sarasota full** | Accela Civic Application; Auburn new-SF ~491. PAO Detailed_Data Building.txt is CAMA building cards, not permits. |
| **Broward BCS full** | `bcgishub` BCS folder **Token Required**. FTL city (~205k) + HCED Posse (~2.3k) remain partial. |
| **Cape Coral history** | **Closed** via Excel+OpenData merge (~279k). Prefer over Active-only Tier A. |

CAPTCHA: none on open endpoints used this turn. Login/token: Broward BCS FeatureServer; Accela Construct API requires App ID; many Accela modules need account for bulk export.

## Preview CSVs

Each new bronze folder has `sample_preview.csv` (≤100 rows). Store copies: `docs/sample_preview_cape_coral_history.csv`, `docs/sample_preview_pasco_job_values.csv`, `docs/sample_preview_osceola_nc.csv`, `docs/sample_preview_osceola_nc_a.csv`, `docs/sample_preview_boca_raton.csv`.

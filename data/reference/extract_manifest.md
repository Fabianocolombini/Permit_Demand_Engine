# Permit extract manifest — Florida Onda 1 (Path B + open Tier B)

Generated: 2026-11-01 01:40 UTC · Path B: no paid Shovels · open ArcGIS/CSV fills for Tier B gaps

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

## New open Tier B bronze (this PR)

| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |
|---|---|---:|---|---|---|---:|---|
| fl_pinellas_county | full_county | 583,918 | 2021-01-01 | 2026-10-08 | `/workspace/data/bronze/fl_pinellas_county/fl_pinellas_county_permits_2021-01-01_20261101.csv` | 68.1 MB | PCPAO RP_PERMITS bulk ZIP (POST download). County + cities. STRAP only (no site street). |
| fl_fort_lauderdale_city | city | 204,760 | 2021-03-18 | 2026-03-16 | `/workspace/data/bronze/fl_fort_lauderdale_city/fl_fort_lauderdale_city_permits_2021-01-01_20261101.csv` | 65.0 MB | Open FeatureServer. APPROVEDT null — window on SUBMITDT. Broward city fill; BCS still locked. |
| fl_lakeland_city | city | 26,090 | 2021-01-04 | 2025-06-25 | `/workspace/data/bronze/fl_lakeland_city/fl_lakeland_city_permits_2021-01-01_20261101.csv` | 7.6 MB | Lakeland IMS TYPE=Permit. Polk county Accela still portal-only. |
| fl_palm_bay_city | city | 20,313 | 2021-01-04 | 2022-05-31 | `/workspace/data/bronze/fl_palm_bay_city/fl_palm_bay_city_permits_2021-01-01_20261101.csv` | 3.5 MB | Palm Bay FeatureServer — **layer appears stale (issueDate only through mid-2022)**. |
| fl_lee_new_sf_auburn | unknown | 7,435 | 2021+ | 2022+ | `/workspace/data/bronze/fl_lee_new_sf_auburn/fl_lee_new_sf_auburn_permits_2021-01-01_20261101.csv` | 3.1 MB | Third-party Auburn AGOL new-SF only — not official Lee feed. |
| fl_volusia_active_permits | unknown | 2,851 | 2021-01-22 | 2026-10-30 | `/workspace/data/bronze/fl_volusia_active_permits/fl_volusia_active_permits_permits_2021-01-01_20261101.csv` | 1.7 MB | AMANDA current/open processes only — not full history. |
| fl_sarasota_new_sf_auburn | unknown | 491 | 2021+ | 2022+ | `/workspace/data/bronze/fl_sarasota_new_sf_auburn/fl_sarasota_new_sf_auburn_permits_2021-01-01_20261101.csv` | 0.2 MB | Same Auburn layer filtered to Sarasota — thin supplement. |
| **NEW TOTAL** | | **845,858** | | | | | Classify / TOM+SAM not re-run for these yet. |

## Completed extracts (Tier A — prior)

| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |
|---|---|---:|---|---|---|---:|---|
| fl_broward_county | unknown | 2,350 | 2021-01-06 | 2026-10-29 | `/workspace/data/bronze/fl_broward_county/fl_broward_county_permits_2021-01-01_20261030.csv` | 2.1 MB | HCED Posse subset |
| fl_cape_coral_city | city | 14,385 | 2021-01-04 | 2026-10-30 | `/workspace/data/bronze/fl_cape_coral_city/fl_cape_coral_city_permits_2021-01-01_20261030.csv` | 7.9 MB | Active only — history still missing |
| fl_hillsborough_county | full_county | 40,329 | 2021 | 2026 | `/workspace/data/bronze/fl_hillsborough_county/fl_hillsborough_county_permits_2021-01-01_20261030.csv` | 35.5 MB | Planning Commission layer |
| fl_manatee_active_residential | unknown | 4,357 | 2021-01-05 | 2026-10-29 | `/workspace/data/bronze/fl_manatee_active_residential/fl_manatee_active_residential_permits_2021-01-01_20261030.csv` | 0.9 MB | Prefer PermitData |
| fl_manatee_county | full_county | 247,953 | 2021-01-01 | 2026-10-29 | `/workspace/data/bronze/fl_manatee_county/fl_manatee_county_permits_2021-01-01_20261030.csv` | 121.7 MB | PermitData table |
| fl_miami_city | city | 169,827 | 2021-01-01 | 2026-10-29 | `/workspace/data/bronze/fl_miami_city/fl_miami_city_permits_2021-01-01_20261030.csv` | 91.8 MB | City of Miami |
| fl_miami_dade_county | unincorporated_only | 420,160 | 2021-01-01 | 2026-10-26 | `/workspace/data/bronze/fl_miami_dade_county/fl_miami_dade_county_permits_2021-01-01_20261030.csv` | 195.9 MB | Unincorporated only |
| fl_orlando_city | city | 191,615 | 2021-01-01 | 2026-10-30 | `/workspace/data/bronze/fl_orlando_city/fl_orlando_city_permits_2021-01-01_20261030.csv` | 98.2 MB | City only — Orange uninc Tier B |

## Endpoint reference (new)

| Jurisdiction | Connector | URL |
|---|---|---|
| fl_pinellas_county | file (POST) | https://www.pcpao.gov/dal/databasefile/downloadDatabaseFile |
| fl_fort_lauderdale_city | arcgis | https://gis.fortlauderdale.gov/server/rest/services/BuildingPermits/FeatureServer/0 |
| fl_palm_bay_city | arcgis | https://gis.palmbayflorida.org/arcgis/rest/services/GrowthManagement/BuildingPermits/FeatureServer/0 |
| fl_lakeland_city | arcgis | https://arcgis.lakelandgov.net/maps/rest/services/IMS/IMS_Projects_Permits/FeatureServer/6 |
| fl_volusia_active_permits | arcgis | https://maps5.vcgov.org/arcgis/rest/services/CurrentProjects/FeatureServer/1 |
| fl_lee_new_sf_auburn | arcgis | https://services.arcgis.com/5UFHFK7ZmWoapZj1/arcgis/rest/services/NewPermits_Post2021_LeeManateeSarasotaCharlotte/FeatureServer/0 |
| fl_sarasota_new_sf_auburn | arcgis | (same Auburn layer, `layer = 'Sarasota County permits'`) |

## Remaining blockers (honest)

| Gap | Status |
|---|---|
| **Palm Beach** building | No open building FeatureServer. ePZB / discover.pbcgov.org portal; ENG EPERMIT_DATA is ROW/utility. |
| **Orange unincorporated** | OC FastTrack HTML only; Orlando Socrata already Tier A. Download link 404. |
| **Duval / Jacksonville** | JAXEPICS portal / Excel email; `data.coj.net` DNS fail; no public FeatureServer. |
| **Lee unincorporated full** | Accela LEECO portal; GIS permitting = zones only. Auburn new-SF (~7.4k) thin; Cape Coral Active still not history. |
| **Polk full** | Accela polkco portal; only Lakeland city open (~26k). |
| **Brevard full** | Accela BASS portal; Palm Bay city open but **stale through 2022**. |
| **Volusia full** | Only AMANDA current/open (~2.8k). |
| **Pasco / Osceola** | Accela CapHome only (ASP.NET; brittle / often login for bulk). |
| **Sarasota full** | Accela Civic Application; Auburn new-SF ~491 only. |
| **Broward BCS full** | `bcgishub` BCS folder **Token Required**. FTL city (~205k) is partial fill only. |
| **Cape Coral history** | Still Active + tiny FY SF layers only. |

CAPTCHA: none on the open endpoints used this turn. Login/token: Broward BCS FeatureServer; many Accela modules need account for bulk export.

## Preview CSVs

Each new bronze folder has `sample_preview.csv` (≤100 rows). Helper: `scripts/export_pcpao_pinellas.py`.

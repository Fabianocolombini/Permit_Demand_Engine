# Permit extract manifest — Florida Onda 1

Generated: 2026-10-30 17:09 UTC

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

## Coverage caveats

- **Miami-Dade Hub = unincorporated only.** City of Miami is a separate extract (`fl_miami_city`).
- **Cape Coral / Manatee layers are Active permits**, not full historical archives.
- **Broward HCED Posse** is a small geocoded subset (engineering-leaning), not full BCS building volume.
- Orange County unincorporated, Duval/Jacksonville, Palm Beach building, Pinellas, Lee unincorporated,
  Polk, Brevard, Volusia, Pasco, Osceola, Sarasota: **Tier B** (portal / no open record API found).

## Preview CSVs

Each bronze folder has `sample_preview.csv` (≤100 rows). A combined committed preview lives at
`data/reference/sample_preview.csv` (Miami-Dade first 100).


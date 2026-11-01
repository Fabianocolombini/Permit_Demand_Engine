# Schema report — Miami-Dade County building permits

**Etapa 1.1 only.** Probe of the official ArcGIS Open Data layer. Field mapping below is **hypothesis for human review** — do not treat as confirmed.

Probe date: 2026-10-30  
Probe method: `GET …?f=json` (layer metadata) + tiny `query` (`returnCountOnly`, `resultRecordCount=3`, outStatistics). No bulk download.

---

## Chosen service

| Item | Value |
|---|---|
| **Hub listing** | [Building Permits Issued By Miami-Dade County - 2 Previous Years to Present](https://opendata.miamidade.gov/datasets/MDC::building-permits-issued-by-miami-dade-county-2-previous-years-to-present) |
| **ArcGIS item** | `6db5f56e886446df88313ca279e59120` (owner `MDPublisher`, org `8Pc9XBTAsYuxx9Ny`) |
| **Exact service URL** | `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer` |
| **Layer index** | **0** |
| **Layer query URL** | `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer/0` |
| **Auth** | Public / anonymous — no token required on probe |

**Why this layer:** It is the county Open Data Hub Feature Service titled for issued building permits and published by Miami-Dade (`MDPublisher`). Title matches the V1 need (issued permits, multi-year window). Prefer this over third-party mirrors.

---

## Layer metadata (from `?f=json`)

| Property | Value |
|---|---|
| **name** | `miamidade_permit_data` |
| **type** | **Table** (not a spatial Feature Layer) |
| **geometryType** | `null` — **no native geometry** |
| **maxRecordCount** | `1000` |
| **supportsPagination** | `true` (`advancedQueryCapabilities.supportsPagination`) |
| **objectIdField** | `ObjectId` |
| **displayField** | *(empty)* |
| **extent** | **None** on the table layer (item `extent` also empty) |
| **timeInfo** | None |
| **field count** | **58** |

### total_features

| Query | Count |
|---|---|
| `where=1=1` | **487,686** |
| `PermitIssuedDate IS NOT NULL` | 487,686 (all rows have issued date) |
| `PermitIssuedDate >= '2024-10-30'` (~24 months before probe) | **139,387** |
| `PermitIssuedDate >= '2023-10-30'` (~36 months) | 210,726 |

**Issued-date span (outStatistics min/max on `PermitIssuedDate`):** `2020-01-01` → `2026-10-26`.

**Note vs Hub title:** Hub title says “2 Previous Years to Present,” but the FeatureServer currently exposes ~7 years of issued dates (from 2020). For V1, filter on `PermitIssuedDate` to the last 24 months rather than trusting the title as a server-side window.

**Date query tip:** `PermitIssuedDate` is `esriFieldTypeDateOnly`. Epoch-ms comparisons failed; string / `DATE 'YYYY-MM-DD'` worked (`PermitIssuedDate >= '2024-10-30'`).

---

## Geographic extent

**Not provided by this layer** (table, no `extent`, no geometry).

Implied coverage from attributes: Miami-Dade addresses (`City` often `MIAMI`, `State` = `FL`), plus `FolioNumber` (parcel). Lat/lon for maps/logistics will require **geocoding** (Census batch) or a join to a spatial layer (see alternate below).

---

## Full field list

| name | type | alias |
|---|---|---|
| PermitIssuedDate | esriFieldTypeDateOnly | PermitIssuedDate |
| ApplicationDate | esriFieldTypeDate | ApplicationDate |
| PermitNumber | esriFieldTypeString | PermitNumber |
| ProcessNumber | esriFieldTypeString | ProcessNumber |
| MasterPermitNumber | esriFieldTypeString | MasterPermitNumber |
| PermitType | esriFieldTypeString | PermitType |
| ResidentialCommercial | esriFieldTypeString | ResidentialCommercial |
| EstimatedValue | esriFieldTypeString | EstimatedValue |
| ApplicationTypeCode | esriFieldTypeInteger | ApplicationTypeCode |
| ApplicationTypeDescription | esriFieldTypeString | ApplicationTypeDescription |
| ProposedUseCode | esriFieldTypeInteger | ProposedUseCode |
| ProposedUseDescription | esriFieldTypeString | ProposedUseDescription |
| DetailDescriptionComments | esriFieldTypeString | DetailDescriptionComments |
| FolioNumber | esriFieldTypeString | FolioNumber |
| OwnerName | esriFieldTypeString | OwnerName |
| LegalDescription1 | esriFieldTypeString | LegalDescription1 |
| LegalDescription2 | esriFieldTypeString | LegalDescription2 |
| PropertyAddress | esriFieldTypeString | PropertyAddress |
| ArchitectName | esriFieldTypeString | ArchitectName |
| ContractorNumber | esriFieldTypeString | ContractorNumber |
| ContractorName | esriFieldTypeString | ContractorName |
| ContractorAddress | esriFieldTypeString | ContractorAddress |
| ContractorCity | esriFieldTypeString | ContractorCity |
| ContractorState | esriFieldTypeString | ContractorState |
| ContractorZip | esriFieldTypeString | ContractorZip |
| ContractorPhone | esriFieldTypeString | ContractorPhone |
| SquareFootage | esriFieldTypeString | SquareFootage |
| StructureUnits | esriFieldTypeInteger | StructureUnits |
| StructureFloors | esriFieldTypeInteger | StructureFloors |
| Category1 | esriFieldTypeString | Category1 |
| CategoryDescription1 | esriFieldTypeString | CategoryDescription1 |
| Category2 | esriFieldTypeString | Category2 |
| CategoryDescription2 | esriFieldTypeString | CategoryDescription2 |
| Category3 | esriFieldTypeString | Category3 |
| CategoryDescription3 | esriFieldTypeString | CategoryDescription3 |
| Category4 | esriFieldTypeString | Category4 |
| CategoryDescription4 | esriFieldTypeString | CategoryDescription4 |
| Category5 | esriFieldTypeString | Category5 |
| CategoryDescription5 | esriFieldTypeString | CategoryDescription5 |
| Category6 | esriFieldTypeString | Category6 |
| CategoryDescription6 | esriFieldTypeString | CategoryDescription6 |
| Category7 | esriFieldTypeString | Category7 |
| CategoryDescription7 | esriFieldTypeString | CategoryDescription7 |
| Category8 | esriFieldTypeString | Category8 |
| CategoryDescription8 | esriFieldTypeString | CategoryDescription8 |
| Category9 | esriFieldTypeString | Category9 |
| CategoryDescription9 | esriFieldTypeString | CategoryDescription9 |
| Category10 | esriFieldTypeString | Category10 |
| CategoryDescription10 | esriFieldTypeString | CategoryDescription10 |
| LastInspectionDate | esriFieldTypeDate | LastInspectionDate |
| LastApprovedInspDate | esriFieldTypeDate | LastApprovedInspDate |
| CoCcDate | esriFieldTypeString | CoCcDate |
| PermitTotalFee | esriFieldTypeString | PermitTotalFee |
| Filler | esriFieldTypeString | Filler |
| City | esriFieldTypeString | City |
| State | esriFieldTypeString | State |
| ObjectId | esriFieldTypeOID | ObjectId |
| GlobalID | esriFieldTypeGlobalID | GlobalID |

Observed non-empty rates (approx., `returnCountOnly` on full table): address ~484k/487k; estimated value non-zero ~440k; description ~480k; contractor name all rows; contractor number ~412k. `City`/`State` present on all probed rows.

**Distinct `PermitType` values observed:** `BLDG`, `CCUT`, `ELEC`, `FIRE`, `LPGX`, `MBLD`, `MECH`, `MELE`, `MLPG`, `MMEC`, `MMFP`, `MPLU`, `PLUM`, `ZIPS`.

Rough text-hit counts (description / app type / category / proposed use, case-insensitive): `PLUMB` ~25.7k; `POOL` ~34.9k; `IRRIG` ~302; `REPIPE` ~50; `WATER HEATER` ~772; `SPRINK` ~10.6k (includes fire sprinklers — rules must disambiguate).

---

## Candidate mapping notes — **HYPOTHESES for Fabiano review**

Not confirmed. Labels for normalize/mapper design only.

| Normalized target | Likely raw field(s) | Confidence / caveats |
|---|---|---|
| **permit_id** | `PermitNumber` (alt: `ProcessNumber`, or `GlobalID`) | High for `PermitNumber`; confirm uniqueness / reissues |
| **issued_date** | **`PermitIssuedDate`** | High — DateOnly `YYYY-MM-DD` |
| **applied_date** | `ApplicationDate` | High — epoch ms Date |
| **final_date / CO** | `CoCcDate`? | Low — stored as **string**, format unclear |
| **address_raw** | **`PropertyAddress`** | High |
| **city / state** | `City`, `State` | High; city often generic `MIAMI` |
| **zip** | **No property ZIP field** | Blocker for ZIP analytics unless geocode or folio join; `ContractorZip` is contractor HQ, **not** site ZIP |
| **lat / lon / geometry** | *(none on this layer)* | Must geocode or join spatial alternate |
| **declared_valuation** | **`EstimatedValue`** | Medium — **string** digits (e.g. `"498002"`); parse to float; may be cents? samples look like whole USD |
| **permit_type_raw** | `PermitType` and/or `ApplicationTypeDescription` | Medium — codes (`PLUM`, `BLDG`…) vs free-text app type |
| **work_class_raw** | `CategoryDescription1`…`10` and/or `ProposedUseDescription` | Medium — multi-category slots |
| **description_raw** | **`DetailDescriptionComments`** | High |
| **is_residential** | `ResidentialCommercial` (`R`/`C`) | High on samples |
| **contractor_name** | `ContractorName` | High (`OWNER` common) |
| **contractor_license** | `ContractorNumber` | High when present |
| **owner_name** | `OwnerName` | High |
| **square_feet / units** | `SquareFootage` (string), `StructureUnits` | Medium |
| **project_key inputs** | address + issued + maybe `MasterPermitNumber` / folio | Medium — master permit often `0000000000` |

**Classification signal (hypothesis):** Concatenate `PermitType` + `ApplicationTypeDescription` + `CategoryDescription1..n` + `ProposedUseDescription` + `DetailDescriptionComments` for regex rules. Filter or weight `PLUM`/`MPLU` permit types for plumbing demand; do not rely on category alone.

---

## Sample attribute keys (tiny query, 3 features)

Query: `where=PermitIssuedDate >= '2026-10-01'`, `outFields=*`, `resultRecordCount=3`. Response features had **`attributes` only** (no `geometry`).

**Keys present on each sample (58):**  
`ApplicationDate`, `ApplicationTypeCode`, `ApplicationTypeDescription`, `ArchitectName`, `Category1`…`Category10`, `CategoryDescription1`…`CategoryDescription10`, `City`, `CoCcDate`, `ContractorAddress`, `ContractorCity`, `ContractorName`, `ContractorNumber`, `ContractorPhone`, `ContractorState`, `ContractorZip`, `DetailDescriptionComments`, `EstimatedValue`, `Filler`, `FolioNumber`, `GlobalID`, `LastApprovedInspDate`, `LastInspectionDate`, `LegalDescription1`, `LegalDescription2`, `MasterPermitNumber`, `ObjectId`, `OwnerName`, `PermitIssuedDate`, `PermitNumber`, `PermitTotalFee`, `PermitType`, `ProcessNumber`, `PropertyAddress`, `ProposedUseCode`, `ProposedUseDescription`, `ResidentialCommercial`, `SquareFootage`, `State`, `StructureFloors`, `StructureUnits`

**Illustrative values (not a dump):**

1. `PermitNumber=2027000198`, issued `2026-10-01`, `PropertyAddress=3070 SW 37 AVE`, `EstimatedValue=145000000`, `PermitType=BLDG`, description `NEW APARTMENT BLDG`, contractor `CIVIC CONSTRUCTION MANAGEMENT LLC`
2. `PermitNumber=2027000197`, `PermitType=MECH`, description `VENTILATION IMPOVE`, value `498002`
3. `PermitNumber=2027000196`, residential, description `REPLACE JOISTS`, contractor `OWNER`, value `2200`

---

## Alternate candidate (not chosen as primary)

| Item | Value |
|---|---|
| Service | `https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer` |
| Layer | **1** — `County Building Permits @ BuildingPermit` |
| Type | Feature Layer, **`esriGeometryPoint`** |
| maxRecordCount | 1000 |
| supportsPagination | true |
| total_features | **262,015** |
| extent | xmin/ymin/xmax/ymax in State Plane (wkid 102658 / 2236); sample query with `outSR=4326` returned lon/lat points |
| Fields | 43 — shorter names (`ISSUDATE`, `ADDRESS`, `CONTRNAME`, `TYPE`, `DESC1`…) |
| Valuation | **No `EstimatedValue`-like field** observed |

Useful if V1 wants native coordinates without geocoding, but weaker for material model (no declared valuation) and appears to be a different/subset universe vs Hub table. Possible later **join** key: process/permit/folio — needs confirmation.

---

## Blockers / open questions for Fabiano

1. **No geometry on chosen Hub layer** — accept Census geocode path, or join MapServer points / parcel layer?
2. **No site ZIP** — geocode must return ZIP, or derive from folio; ZIP-level gold tables depend on this.
3. **Hub title vs data span** — use explicit 24-month `PermitIssuedDate` filter (recommended).
4. **`EstimatedValue` as string** — confirm units (USD whole dollars vs other) before material model.
5. **Primary key** — `PermitNumber` vs `ProcessNumber` vs `GlobalID` for DuckDB `permit_id`.
6. **Municipal vs unincorporated** — Hub description is county-issued; confirm whether municipal permits (City of Miami, etc.) are in-scope / included.
7. **MapServer vs Hub** — same universe or different? Do not dual-ingest without a dedup plan.
8. **No auth blocker** on probe.

---

## Stop line

Etapa **1.1 complete** with this report. **Do not** implement ArcGIS connector, ingest, normalize, classify, or app until mapping is reviewed.

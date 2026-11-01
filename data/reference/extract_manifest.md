# Permit extract manifest — Florida free-path advance (no paid Shovels)

Generated: 2026-11-01 02:50 UTC · Branched from PR #6 tip · Path B only

Window: **issued ≥ 2021-01-01** (post-pandemic). Raw/full permits — no market filter at extract time.

## TOM / SAM (Tier A + open Tier B bronze → silver)

Recomputed after combining prior Tier A with open Tier B fills (Pinellas, Cape history, FTL, Jax, etc.). Prefer `fl_cape_coral_history` over active-only Cape; prefer `fl_manatee_county` over active residential.

- **TOM** = total permits in `silver.permits`
- **SAM** = plumbing (new/repipe/remodel) **including new residential construction** + pool/spa + irrigation

**Overall:** TOM **2,726,677** · SAM **712,689** · SAM/TOM **26.14%**

| Jurisdiction | Tier | TOM | SAM | SAM/TOM % |
|---|---|---:|---:|---:|
| fl_duval_jacksonville | A | 712,300 | 273,456 | 38.39 |
| fl_pinellas_county | B | 565,965 | 51,308 | 9.07 |
| fl_miami_dade_county | A | 420,160 | 111,147 | 26.45 |
| fl_cape_coral_history | B | 278,675 | 63,776 | 22.89 |
| fl_manatee_county | A | 247,964 | 82,074 | 33.10 |
| fl_orlando_city | A | 191,663 | 36,674 | 19.13 |
| fl_miami_city | A | 169,928 | 41,990 | 24.71 |
| fl_hillsborough_county | A | 38,632 | 26,367 | 68.25 |
| fl_lakeland_city | B | 26,090 | 3,656 | 14.01 |
| fl_pasco_permit_job_values | B | 20,494 | 6,877 | 33.56 |
| fl_palm_bay_city | B | 20,228 | 1,283 | 6.34 |
| fl_fort_lauderdale_city | B | 11,568 | 1,543 | 13.34 |
| fl_lee_new_sf_auburn | B | 7,419 | 7,184 | 96.83 |
| fl_osceola_new_construction | B | 4,639 | 2,245 | 48.39 |
| fl_volusia_active_permits | B | 2,851 | 920 | 32.27 |
| fl_tampa_city_active | B | 2,410 | 1,785 | 74.07 |
| fl_broward_county | A | 2,350 | 16 | 0.68 |
| fl_osceola_new_construction_a | B | 1,341 | 224 | 16.70 |
| fl_boca_raton_city | B | 883 | 117 | 13.25 |
| fl_st_petersburg_* (5 layers) | B | 626 | 47 | — |
| fl_sarasota_new_sf_auburn | B | 491 | 0 | 0.00 |
| **TOTAL** | | **2,726,677** | **712,689** | **26.14** |

Notes: FTL bronze has ~205k SUBMITDT rows but **11,568 unique PERMITID** (event/status fan-out → silver dedupe). St Pete YYMMDD int dates normalized; silver keeps unique `APPLICATIONPARAM`.

## Material fittings (SAM)

From `config/assumptions.yaml` → `gold.material_estimates`:

| Scenario | Fittings $ |
|---|---:|
| **low** | **$1.99B** |
| **base** | **$3.30B** |
| **high** | **$4.82B** |

Declared project valuation: TOM **$897.35B** · SAM **$324.80B** (see `valuation_tom_sam.md`; ≥$1B outlier caveat unchanged).

## Census BPS + HUD (67 FL counties)

| Source | Path | Coverage |
|---|---|---|
| Census BPS annual county 2021–2025 | `data/reference/census_bps_fl.csv` | **335** rows · **67** counties × 5 years |
| HUD Residential Construction Permits by County | `data/reference/hud_permits_fl.csv` | **134** rows · **67** counties × years **2021–2022** (layer max) |
| Bronze vs BPS coverage | `data/reference/bps_bronze_coverage_fl.md` | Directional ratio (all-permit bronze ≠ BPS new residential units) |

## New / upgraded open fills this turn

| Jurisdiction | Rows (bronze) | Source |
|---|---:|---|
| fl_duval_jacksonville | 712,345 | BID GIS Esri proxy All Permits (Tier A) |
| fl_tampa_city_active | 2,452 | tampagov Planning/PermitsAll (active-only; prefer Hillsborough) |
| fl_st_petersburg_{sf,mf,other,demo,renovation} | 2,002 | egis.stpete PermitsExternal layers 0–4 |
| fl_pinellas_county (re-pull) | 583,918 | PCPAO RP_PERMITS ZIP |
| fl_cape_coral_history (re-pull) | 278,675 | Excel + OpenData |
| Prior open Tier B (FTL, Lakeland, Palm Bay, Pasco, Osceola, Boca, Auburn, Volusia) | re-exported | unchanged connectors |

## Accela CapHome (Lee, Polk, Brevard, Volusia, Pasco, Osceola, Sarasota)

Best-effort anonymous probes — **no bulk history**. Construct API requires App ID.

| County | Host | Sample rows | Blocker |
|---|---|---:|---|
| Lee | `aca-prod.accela.com/LEECO` | 10 | CapHome list capped (~100+); Download-results → HTML |
| Polk | `…/polkco` | 10 | Same cap |
| Brevard | `…/BREVARD` | 10 | Same cap |
| Pasco | `…/PASCO` | 10 | Same cap |
| Osceola | `…/OSCEOLA` | 10 | Same cap |
| Volusia | — | 0 | Not Accela; Connect Live + reCAPTCHA |
| Sarasota | `…/SARASOTACO` | 0 | Building CapHome redirects anonymous → Login |

Bronze samples only: `data/bronze/fl_*_accela/sample_preview.csv` (not in TOM/SAM).

## Remaining blockers (honest)

| Gap | Status |
|---|---|
| Palm Beach full building | No county FeatureServer; ePZB / internal PAO host |
| Orange unincorporated | OC FastTrack HTML only |
| Lee / Polk / Brevard / Pasco / Osceola full | Accela CapHome no bulk; Construct needs App ID |
| Volusia full | Connect Live + reCAPTCHA (not Accela) |
| Sarasota full | Accela SARASOTACO login wall |
| Broward BCS full | `bcgishub` BCS Token Required |
| Tampa full city history | Active viewer only; CivicData BLDS 404; Hillsborough Tier A covers county |
| St Pete full city | Thin PermitsExternal; prefer Pinellas PCPAO |

No paid Shovels this turn.

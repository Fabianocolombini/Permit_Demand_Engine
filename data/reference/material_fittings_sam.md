# Material fittings demand — SAM (low / base / high)

Generated: 2026-11-01 02:48 UTC from `gold.material_estimates` · assumptions in `config/assumptions.yaml`.

## Units

**USD fittings demand** estimated from declared project valuation (or fixed $/project for repipe), not declared construction value itself.

- `res_new_plumbing` / `res_remodel_plumbing`: valuation × plumbing_share × material_share × fittings_share
- `res_repipe`: fixed `$320 / $450 / $640` per project
- `irrigation` / `pool_spa`: valuation × fittings_share_of_project

**SAM rows modeled:** 712,689

| Scenario | Fittings $ |
|---|---:|
| **low** | **$1.99B** (`$1,992,559,979`) |
| **base** | **$3.30B** (`$3,301,932,288`) |
| **high** | **$4.82B** (`$4,815,687,480`) |

## By SAM category

| Category | Rows | Fittings low | Fittings base | Fittings high |
|---|---:|---:|---:|---:|
| pool_spa | 121,324 | $1.11B | $1.78B | $2.44B |
| res_new_plumbing | 533,608 | $425.1M | $819.8M | $1.40B |
| irrigation | 41,213 | $425.9M | $638.9M | $851.9M |
| res_remodel_plumbing | 4,561 | $26.9M | $60.6M | $112.8M |
| res_repipe | 11,983 | $3.8M | $5.4M | $7.7M |

## By jurisdiction

| Jurisdiction | SAM rows | Fittings base |
|---|---:|---:|
| fl_miami_dade_county | 111,147 | $2.50B |
| fl_miami_city | 41,990 | $230.0M |
| fl_duval_jacksonville | 273,456 | $205.6M |
| fl_manatee_county | 82,074 | $127.0M |
| fl_cape_coral_history | 63,776 | $79.2M |
| fl_hillsborough_county | 26,367 | $49.4M |
| fl_pinellas_county | 51,308 | $46.9M |
| fl_orlando_city | 36,674 | $36.6M |
| fl_osceola_new_construction | 2,245 | $15.4M |
| fl_pasco_permit_job_values | 6,877 | $8.5M |
| fl_lakeland_city | 3,656 | $3.3M |
| fl_palm_bay_city | 1,283 | $1.2M |
| fl_boca_raton_city | 117 | $200.9K |
| fl_osceola_new_construction_a | 224 | $32.5K |
| fl_st_petersburg_sf_new | 43 | $23.1K |
| fl_st_petersburg_mf_new | 2 | $20.6K |
| fl_tampa_city_active | 1,785 | $5.8K |
| fl_volusia_active_permits | 920 | $4.5K |
| fl_st_petersburg_other_new | 2 | $432 |
| fl_lee_new_sf_auburn | 7,184 | $0 |
| fl_fort_lauderdale_city | 1,543 | $0 |
| fl_broward_county | 16 | $0 |

## Caveats

- Multiplicative assumptions (± bands) produce ~2× low–high span; confidence is **low** until calibrated with sell-out.
- Rows with missing/≤0 valuation contribute $0 for share-of-valuation methods (repipe still counts fixed $).
- Extreme Miami-Dade valuations inflate share-based fittings — same outlier caveat as declared-valuation reports.

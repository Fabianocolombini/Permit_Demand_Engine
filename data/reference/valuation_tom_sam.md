# Declared project valuation — TOM / SAM

Generated: 2026-11-01 02:48 UTC from `/workspace/permits.duckdb` (`silver.permits`).

## Units

**USD declared project value** (`declared_valuation`). This is the **permit's stated construction value**, not fittings demand.

**Declared** = `declared_valuation IS NOT NULL AND declared_valuation > 0`.

## % of permits that declare valuation

| Universe | % declared | Declared rows | Missing (null/≤0) | Total rows |
|---|---:|---:|---:|---:|
| **TOM** | **92.65%** | 2,526,220 | 200,457 (null 125,572 · zero 74,885) | 2,726,677 |
| **SAM** | **95.11%** | 677,823 | 34,866 (null 31,176 · zero 3,690) | 712,689 |

### By jurisdiction

| Jurisdiction | TOM % declared | SAM % declared | TOM declared/total | SAM declared/total |
|---|---:|---:|---:|---:|
| fl_miami_dade_county | 90.85% | 95.94% | 381,730/420,160 | 106,635/111,147 |
| fl_duval_jacksonville | 93.43% | 95.57% | 665,500/712,300 | 261,335/273,456 |
| fl_hillsborough_county | 96.31% | 99.55% | 37,205/38,632 | 26,249/26,367 |
| fl_miami_city | 93.42% | 92.81% | 158,739/169,928 | 38,971/41,990 |
| fl_pinellas_county | 95.88% | 96.51% | 542,651/565,965 | 49,516/51,308 |
| fl_manatee_county | 99.71% | 99.81% | 247,234/247,964 | 81,917/82,074 |
| fl_orlando_city | 91.9% | 99.84% | 176,136/191,663 | 36,616/36,674 |
| fl_cape_coral_history | 89.16% | 98.38% | 248,454/278,675 | 62,742/63,776 |
| fl_pasco_permit_job_values | 99.78% | 99.99% | 20,448/20,494 | 6,876/6,877 |
| fl_lakeland_city | 97.09% | 86.16% | 25,330/26,090 | 3,150/3,656 |
| fl_osceola_new_construction | 99.98% | 100.0% | 4,638/4,639 | 2,245/2,245 |
| fl_palm_bay_city | 79.84% | 97.97% | 16,151/20,228 | 1,257/1,283 |
| fl_osceola_new_construction_a | 99.93% | 100.0% | 1,340/1,341 | 224/224 |
| fl_st_petersburg_renovation | 99.16% | n/a% | 473/477 | 0/0 |
| fl_st_petersburg_mf_new | 100.0% | 100.0% | 4/4 | 2/2 |
| fl_st_petersburg_other_new | 98.7% | 100.0% | 76/77 | 2/2 |
| fl_st_petersburg_sf_new | 100.0% | 100.0% | 43/43 | 43/43 |
| fl_boca_raton_city | 4.87% | 36.75% | 43/883 | 43/117 |
| fl_st_petersburg_demo | 100.0% | n/a% | 25/25 | 0/0 |
| fl_sarasota_new_sf_auburn | 0.0% | n/a% | 0/491 | 0/0 |
| fl_broward_county | 0.0% | 0.0% | 0/2,350 | 0/16 |
| fl_volusia_active_permits | 0.0% | 0.0% | 0/2,851 | 0/920 |
| fl_fort_lauderdale_city | 0.0% | 0.0% | 0/11,568 | 0/1,543 |
| fl_lee_new_sf_auburn | 0.0% | 0.0% | 0/7,419 | 0/7,184 |
| fl_tampa_city_active | 0.0% | 0.0% | 0/2,410 | 0/1,785 |
| **TOTAL** | **92.65%** | **95.11%** | **2,526,220/2,726,677** | **677,823/712,689** |

## Dollar sums (declared project value)

| Metric | $ valuation | Rows | % declared |
|---|---:|---:|---:|
| **TOM** | **$897.35B** (`$897,347,693,831`) | 2,726,677 | 92.65% |
| **SAM** | **$324.80B** (`$324,803,964,207`) | 712,689 | 95.11% |
| SAM / TOM | **36.2%** of $ · **26.14%** of rows | | |

### Data-quality note (outliers)

**89** TOM rows and **30** SAM rows have valuation ≥ $1B ($471,516,870,952 / $131,385,625,304 of the sums above).

If those ≥$1B rows are excluded: TOM **$425.83B** · SAM **$193.42B**.

## By jurisdiction — $ and coverage

| Jurisdiction | TOM $ | SAM $ | SAM/TOM $ % | TOM % declared | SAM % declared | TOM missing | SAM missing |
|---|---:|---:|---:|---:|---:|---:|---:|
| fl_miami_dade_county | $706.14B | $227.46B | 32.21 | 90.85% | 95.94% | 38,430 | 4,512 |
| fl_duval_jacksonville | $52.03B | $34.81B | 66.9 | 93.43% | 95.57% | 46,800 | 12,121 |
| fl_hillsborough_county | $28.46B | $17.20B | 60.45 | 96.31% | 99.55% | 1,427 | 118 |
| fl_miami_city | $27.52B | $18.49B | 67.19 | 93.42% | 92.81% | 11,189 | 3,019 |
| fl_pinellas_county | $26.83B | $868.0M | 3.24 | 95.88% | 96.51% | 23,314 | 1,792 |
| fl_manatee_county | $19.58B | $11.53B | 58.88 | 99.71% | 99.81% | 730 | 157 |
| fl_orlando_city | $15.73B | $8.11B | 51.58 | 91.9% | 99.84% | 15,527 | 58 |
| fl_cape_coral_history | $12.00B | $2.23B | 18.6 | 89.16% | 98.38% | 30,221 | 1,034 |
| fl_pasco_permit_job_values | $4.07B | $2.81B | 68.96 | 99.78% | 99.99% | 46 | 1 |
| fl_lakeland_city | $1.92B | $551.7M | 28.72 | 97.09% | 86.16% | 760 | 506 |
| fl_osceola_new_construction | $1.88B | $697.7M | 37.04 | 99.98% | 100.0% | 1 | 0 |
| fl_palm_bay_city | $1.09B | $24.3M | 2.23 | 79.84% | 97.97% | 4,077 | 26 |
| fl_osceola_new_construction_a | $45.5M | $2.5M | 5.55 | 99.93% | 100.0% | 1 | 0 |
| fl_st_petersburg_renovation | $22.8M | $0 | 0.0 | 99.16% | 0% | 4 | 0 |
| fl_st_petersburg_mf_new | $10.3M | $7.3M | 70.53 | 100.0% | 100.0% | 0 | 0 |
| fl_st_petersburg_other_new | $10.1M | $152,540 | 1.51 | 98.7% | 100.0% | 1 | 0 |
| fl_st_petersburg_sf_new | $8.2M | $8.2M | 100.0 | 100.0% | 100.0% | 0 | 0 |
| fl_boca_raton_city | $2.5M | $2.5M | 100.0 | 4.87% | 36.75% | 840 | 74 |
| fl_st_petersburg_demo | $63,424 | $0 | 0.0 | 100.0% | 0% | 0 | 0 |
| fl_sarasota_new_sf_auburn | $0 | $0 | 0.0 | 0.0% | 0% | 491 | 0 |
| fl_broward_county | $0 | $0 | 0.0 | 0.0% | 0.0% | 2,350 | 16 |
| fl_volusia_active_permits | $0 | $0 | 0.0 | 0.0% | 0.0% | 2,851 | 920 |
| fl_fort_lauderdale_city | $0 | $0 | 0.0 | 0.0% | 0.0% | 11,568 | 1,543 |
| fl_lee_new_sf_auburn | $0 | $0 | 0.0 | 0.0% | 0.0% | 7,419 | 7,184 |
| fl_tampa_city_active | $0 | $0 | 0.0 | 0.0% | 0.0% | 2,410 | 1,785 |
| **TOTAL** | **$897.35B** | **$324.80B** | **36.2** | **92.65%** | **95.11%** | **200,457** | **34,866** |

## By SAM category

| SAM category | $ valuation | Rows | % declared | Missing | % of SAM $ |
|---|---:|---:|---:|---:|---:|
| res_new_plumbing | $289.18B (`$289,180,061,732`) | 533,608 | 94.04% | 31,793 | 89.03 |
| pool_spa | $22.22B (`$22,215,447,258`) | 121,324 | 98.68% | 1,605 | 6.84 |
| res_remodel_plumbing | $8.01B (`$8,012,355,055`) | 4,561 | 96.1% | 178 | 2.47 |
| irrigation | $5.32B (`$5,324,210,651`) | 41,213 | 97.55% | 1,009 | 1.64 |
| res_repipe | $71.9M (`$71,889,512`) | 11,983 | 97.66% | 281 | 0.02 |

## Definitions

- **TOM** = all rows in `silver.permits`.
- **SAM** = categories `res_new_plumbing`, `res_repipe`, `res_remodel_plumbing`, `pool_spa`, `irrigation`.
- **% declared** = share with `declared_valuation` not null and > 0.
- Valuation is **not** fittings demand; see material fittings report.

# Census BPS + HUD coverage — Florida (67 counties)

Generated: 2026-11-01 02:48 UTC

- **Census BPS** annual county files: years **2021–2025** → `data/reference/census_bps_fl.csv`
- **HUD** Residential Construction Permits by County (ArcGIS): years **2021, 2022** → `data/reference/hud_permits_fl.csv`
- Counties in table: **67** · with any bronze rows: **15**

## Method notes

- BPS `units_total` / `valuation_usd` = new privately-owned residential units authorized (USD as filed in coYYYYa.txt).
- HUD `all_permits` = final residential permit counts (SOCDS; may lag BPS annual).
- Bronze rows are **all permit types** (plumbing, roof, etc.), not BPS-equivalent new residential units — ratio is a **directional coverage signal**, not a true capture rate.

## County coverage (sorted by BPS units desc)

| FIPS | County | BPS units ≥2021 | BPS $ ≥2021 | HUD permits ≥2021 | Bronze rows | Bronze/BPS units | Tiers |
|---|---|---:|---:|---:|---:|---:|---|
| 12071 | Lee | 69,529 | $15.88B | 27,015 | 301,684 | 4.34 | A;B |
| 12086 | Miami-Dade | 64,622 | $19.14B | 24,998 | 590,088 | 9.13 | A |
| 12057 | Hillsborough | 59,189 | $13.22B | 28,725 | 46,152 | 0.78 | A;B |
| 12105 | Polk | 56,415 | $13.53B | 25,282 | 26,090 | 0.46 | B |
| 12095 | Orange | 55,194 | $12.78B | 25,312 | 192,184 | 3.48 | A;B |
| 12031 | Duval | 43,912 | $7.47B | 21,589 | 824,912 | 18.79 | A |
| 12081 | Manatee | 43,169 | $9.59B | 16,576 | 252,408 | 5.85 | A;B |
| 12097 | Osceola | 41,820 | $8.71B | 17,386 | 8,001 | 0.19 | B |
| 12101 | Pasco | 38,973 | $9.41B | 16,663 | 20,495 | 0.53 | B |
| 12115 | Sarasota | 37,043 | $12.35B | 15,128 | 491 | 0.01 | B |
| 12109 | St. Johns | 33,364 | $7.88B | 16,609 | 0 | 0.00 | C |
| 12083 | Marion | 30,629 | $6.53B | 12,718 | 0 | 0.00 | C |
| 12111 | St. Lucie | 28,001 | $6.65B | 13,931 | 0 | 0.00 | C |
| 12099 | Palm Beach | 27,750 | $9.87B | 13,941 | 1,026 | 0.04 | B |
| 12069 | Lake | 26,555 | $7.32B | 9,907 | 0 | 0.00 | C |
| 12009 | Brevard | 26,196 | $8.97B | 10,432 | 20,313 | 0.78 | B |
| 12015 | Charlotte | 22,535 | $6.29B | 10,506 | 0 | 0.00 | C |
| 12021 | Collier | 22,161 | $9.48B | 12,283 | 0 | 0.00 | C |
| 12127 | Volusia | 21,486 | $6.26B | 10,494 | 2,859 | 0.13 | B |
| 12119 | Sumter | 19,866 | $4.85B | 9,162 | 0 | 0.00 | C |
| 12103 | Pinellas | 15,519 | $4.32B | 5,721 | 585,920 | 37.76 | B |
| 12035 | Flagler | 13,959 | $4.20B | 6,256 | 0 | 0.00 | C |
| 12011 | Broward | 13,787 | $3.07B | 6,395 | 207,113 | 15.02 | A;B |
| 12131 | Walton | 13,265 | $6.03B | 5,189 | 0 | 0.00 | C |
| 12117 | Seminole | 13,127 | $2.77B | 6,696 | 0 | 0.00 | C |
| 12005 | Bay | 11,765 | $3.69B | 4,898 | 0 | 0.00 | C |
| 12001 | Alachua | 11,648 | $2.20B | 5,006 | 0 | 0.00 | C |
| 12073 | Leon | 10,371 | $1.72B | 4,569 | 0 | 0.00 | C |
| 12017 | Citrus | 10,358 | $2.42B | 3,611 | 0 | 0.00 | C |
| 12053 | Hernando | 10,201 | $2.54B | 3,691 | 0 | 0.00 | C |
| 12019 | Clay | 9,946 | $2.42B | 4,101 | 0 | 0.00 | C |
| 12113 | Santa Rosa | 9,307 | $2.31B | 3,621 | 0 | 0.00 | C |
| 12091 | Okaloosa | 7,952 | $2.10B | 2,825 | 0 | 0.00 | C |
| 12033 | Escambia | 7,858 | $1.95B | 3,949 | 0 | 0.00 | C |
| 12089 | Nassau | 6,846 | $2.45B | 3,286 | 0 | 0.00 | C |
| 12061 | Indian River | 5,240 | $2.11B | 2,775 | 0 | 0.00 | C |
| 12085 | Martin | 4,711 | $2.06B | 2,276 | 0 | 0.00 | C |
| 12055 | Highlands | 3,767 | $835.6M | 1,307 | 0 | 0.00 | C |
| 12051 | Hendry | 2,951 | $471.8M | 1,389 | 0 | 0.00 | C |
| 12129 | Wakulla | 2,431 | $420.8M | 911 | 0 | 0.00 | C |
| 12087 | Monroe | 2,142 | $1.11B | 877 | 0 | 0.00 | C |
| 12045 | Gulf | 1,474 | $416.7M | 592 | 0 | 0.00 | C |
| 12075 | Levy | 1,162 | $228.2M | 449 | 0 | 0.00 | C |
| 12023 | Columbia | 1,011 | $242.1M | 469 | 0 | 0.00 | C |
| 12133 | Washington | 811 | $190.2M | 196 | 0 | 0.00 | C |
| 12027 | DeSoto | 762 | $149.2M | 379 | 0 | 0.00 | C |
| 12041 | Gilchrist | 732 | $181.4M | 425 | 0 | 0.00 | C |
| 12121 | Suwannee | 721 | $155.0M | 307 | 0 | 0.00 | C |
| 12107 | Putnam | 651 | $174.2M | 2,021 | 0 | 0.00 | C |
| 12003 | Baker | 616 | $131.2M | 322 | 0 | 0.00 | C |
| 12063 | Jackson | 615 | $132.1M | 229 | 0 | 0.00 | C |
| 12039 | Gadsden | 609 | $161.2M | 281 | 0 | 0.00 | C |
| 12037 | Franklin | 563 | $123.3M | 229 | 0 | 0.00 | C |
| 12043 | Glades | 451 | $82.8M | 228 | 0 | 0.00 | C |
| 12049 | Hardee | 446 | $113.9M | 146 | 0 | 0.00 | C |
| 12123 | Taylor | 405 | $64.3M | 241 | 0 | 0.00 | C |
| 12007 | Bradford | 398 | $91.5M | 173 | 0 | 0.00 | C |
| 12065 | Jefferson | 391 | $102.4M | 200 | 0 | 0.00 | C |
| 12029 | Dixie | 332 | $48.1M | 107 | 0 | 0.00 | C |
| 12125 | Union | 226 | $2.5M | 91 | 0 | 0.00 | C |
| 12079 | Madison | 204 | $51.3M | 104 | 0 | 0.00 | C |
| 12067 | Lafayette | 198 | $16.4M | 76 | 0 | 0.00 | C |
| 12093 | Okeechobee | 154 | $53.2M | 39 | 0 | 0.00 | C |
| 12047 | Hamilton | 129 | $26.7M | 52 | 0 | 0.00 | C |
| 12013 | Calhoun | 115 | $20.1M | 47 | 0 | 0.00 | C |
| 12077 | Liberty | 70 | $15.2M | 23 | 0 | 0.00 | C |
| 12059 | Holmes | 60 | $8.0M | 24 | 0 | 0.00 | C |

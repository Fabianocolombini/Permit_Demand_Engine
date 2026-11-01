#!/usr/bin/env python3
"""Build interactive dashboard metrics JSON (Power BI-style filters).

TOM / SAM / SOM with:
  - YTD multi-year (2023–2026) same-period YoY
  - monthly series + dotted projection through Dec
  - SAM+SOM by category (counts, $, 5% SOM, material vs labor)
  - county + Miami-Dade mesoregion drill
  - contractors: YTD + current/near-term month
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.rules import SAM_CATEGORIES  # noqa: E402
from src.db import connect  # noqa: E402
from src.registry import load_assumptions  # noqa: E402

SOM_SHARE = 0.05
YEAR_END_2026 = date(2026, 12, 31)
AS_OF = date(2026, 11, 1)

MIAMI_AREA_RE = re.compile(
    r"(MIAMI BEACH|CORAL GABLES|HIALEAH|HOMESTEAD|KENDALL|DORAL|CUTLER BAY|"
    r"NORTH MIAMI|AVENTURA|KEY BISCAYNE|MIAMI GARDENS|OPA[\s-]?LOCKA|SWEETWATER|"
    r"FLORIDA CITY|PINECREST|PALMETTO BAY|SUNNY ISLES|MIAMI LAKES|MEDLEY|"
    r"MIAMI SPRINGS|SOUTH MIAMI|WEST MIAMI|NORTH MIAMI BEACH)",
    re.I,
)

COUNTY_FIPS = {
    "Alachua": "12001",
    "Baker": "12003",
    "Bay": "12005",
    "Bradford": "12007",
    "Brevard": "12009",
    "Broward": "12011",
    "Calhoun": "12013",
    "Charlotte": "12015",
    "Citrus": "12017",
    "Clay": "12019",
    "Collier": "12021",
    "Columbia": "12023",
    "DeSoto": "12027",
    "Dixie": "12029",
    "Duval": "12031",
    "Escambia": "12033",
    "Flagler": "12035",
    "Franklin": "12037",
    "Gadsden": "12039",
    "Gilchrist": "12041",
    "Glades": "12043",
    "Gulf": "12045",
    "Hamilton": "12047",
    "Hardee": "12049",
    "Hendry": "12051",
    "Hernando": "12053",
    "Highlands": "12055",
    "Hillsborough": "12057",
    "Holmes": "12059",
    "Indian River": "12061",
    "Jackson": "12063",
    "Jefferson": "12065",
    "Lafayette": "12067",
    "Lake": "12069",
    "Lee": "12071",
    "Leon": "12073",
    "Levy": "12075",
    "Liberty": "12077",
    "Madison": "12079",
    "Manatee": "12081",
    "Marion": "12083",
    "Martin": "12085",
    "Miami-Dade": "12086",
    "Monroe": "12087",
    "Nassau": "12089",
    "Okaloosa": "12091",
    "Okeechobee": "12093",
    "Orange": "12095",
    "Osceola": "12097",
    "Palm Beach": "12099",
    "Pasco": "12101",
    "Pinellas": "12103",
    "Polk": "12105",
    "Putnam": "12107",
    "St. Johns": "12109",
    "St. Lucie": "12111",
    "Santa Rosa": "12113",
    "Sarasota": "12115",
    "Seminole": "12117",
    "Sumter": "12119",
    "Suwannee": "12121",
    "Taylor": "12123",
    "Union": "12125",
    "Volusia": "12127",
    "Wakulla": "12129",
    "Walton": "12131",
    "Washington": "12133",
}


def _fmt(n: float | None) -> str | None:
    if n is None or (isinstance(n, float) and (math.isnan(n) or math.isinf(n))):
        return None
    a = abs(n)
    if a >= 1e9:
        return f"${n/1e9:.2f}B"
    if a >= 1e6:
        return f"${n/1e6:.1f}M"
    if a >= 1e3:
        return f"${n/1e3:.1f}K"
    return f"${n:,.0f}"


def _pct(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return round(100.0 * a / b, 2)


def _yoy(curr: float, prev: float) -> float | None:
    if prev == 0:
        return None
    return round(100.0 * (curr - prev) / prev, 2)


def _growth_factor(by_ym: dict, y: int, m: int, value_key: str) -> float:
    growths = []
    cursor_y, cursor_m = y, m - 1
    checked = 0
    while len(growths) < 3 and checked < 18:
        checked += 1
        if cursor_m <= 0:
            cursor_m += 12
            cursor_y -= 1
        cur = by_ym.get((cursor_y, cursor_m))
        prv = by_ym.get((cursor_y - 1, cursor_m))
        if cur and prv and prv[value_key] > 0:
            growths.append(cur[value_key] / prv[value_key])
        cursor_m -= 1
    return sum(growths) / len(growths) if growths else 1.0


def _project_monthly(
    months: list[dict], value_key: str, as_of: date
) -> tuple[list[dict], dict]:
    """Observed months + projected Nov–Dec (or sparse current) as dotted series."""
    by_ym = {(r["year"], r["month"]): r for r in months}
    y, m = as_of.year, as_of.month
    cur = by_ym.get((y, m))
    prior_same = by_ym.get((y - 1, m))
    sparse = False
    if cur and prior_same and prior_same[value_key] > 0:
        sparse = cur[value_key] < 0.25 * prior_same[value_key]
    elif cur is None:
        sparse = True
    last_complete = m - 1 if sparse else m
    g = _growth_factor(by_ym, y, m, value_key)
    series = []
    for r in months:
        if r["year"] < y or (r["year"] == y and r["month"] <= last_complete):
            series.append(
                {
                    "year": r["year"],
                    "month": r["month"],
                    "value": r[value_key],
                    "kind": "observed",
                }
            )
    remaining = []
    start = m if sparse else m + 1
    for rm in range(start, 13):
        prior = by_ym.get((y - 1, rm))
        pred = prior[value_key] * g if prior else 0.0
        remaining.append({"year": y, "month": rm, "value": pred, "kind": "projected"})
        series.append({"year": y, "month": rm, "value": pred, "kind": "projected"})
    ytd = sum(r["value"] for r in series if r["year"] == y and r["kind"] == "observed")
    ytg = sum(r["value"] for r in remaining)
    return series, {
        "ytd": ytd,
        "ytg": ytg,
        "full_year": ytd + ytg,
        "ytd_through_month": last_complete,
        "growth_factor": g,
        "sparse_current_month": sparse,
    }


def _miami_area(address: str | None, city: str | None, jid: str) -> str:
    if jid == "fl_miami_city":
        return "City of Miami"
    blob = " ".join(filter(None, [address or "", city or ""]))
    m = MIAMI_AREA_RE.search(blob.upper())
    if m:
        return m.group(1).title().replace("Opa-Locka", "Opa-Locka")
    if city and city.strip().upper() not in ("", "MIAMI", "FL"):
        return city.strip().title()
    return "Unincorporated / other Miami-Dade"


def _material_labor(cat: str, valuation: float, assumptions: dict) -> tuple[float, float]:
    """Return (material_usd, labor_usd) for a SAM category on project valuation."""
    cfg = assumptions.get("material_content", {})
    if cat in ("res_new_plumbing", "res_remodel_plumbing"):
        c = cfg.get(cat, cfg.get("res_new_plumbing", {}))
        pl = float(c.get("plumbing_share_of_project_value", {}).get("base", 0.045))
        ms = float(c.get("material_share_of_plumbing", {}).get("base", 0.35))
        plumbing = valuation * pl
        material = plumbing * ms
        labor = plumbing * (1 - ms)
        return material, labor
    if cat == "res_repipe":
        # fixed fittings ≈ material; labor assumed ~2× material (directional)
        base = float(cfg.get("res_repipe", {}).get("fittings_value_usd", {}).get("base", 450))
        return base, base * 2.0
    if cat == "pool_spa":
        fit = float(cfg.get("pool_spa", {}).get("fittings_share_of_project", {}).get("base", 0.08))
        return valuation * fit, valuation * (1 - fit)
    if cat == "irrigation":
        fit = float(
            cfg.get("irrigation", {}).get("fittings_share_of_project", {}).get("base", 0.12)
        )
        return valuation * fit, valuation * (1 - fit)
    return 0.0, 0.0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=ROOT / "permits.duckdb")
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "dashboard" / "public" / "data" / "metrics.json",
    )
    p.add_argument("--as-of", default=AS_OF.isoformat())
    args = p.parse_args()
    as_of = date.fromisoformat(args.as_of)
    assumptions = load_assumptions()
    mat_cfg = assumptions.get("material_content", {})

    con = connect(args.db)
    cats = sorted(SAM_CATEGORIES)
    ph = ",".join("?" * len(cats))

    val_expr = (
        "CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 "
        "THEN declared_valuation ELSE NULL END"
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE peer_medians AS
        SELECT category, county, median({val_expr}) AS median_val
        FROM silver.permits
        WHERE issued_date >= DATE '2021-01-01'
        GROUP BY 1, 2
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE county_medians AS
        SELECT county, median({val_expr}) AS median_val
        FROM silver.permits
        WHERE issued_date >= DATE '2021-01-01' AND {val_expr} IS NOT NULL
        GROUP BY 1
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE cat_medians AS
        SELECT category, median({val_expr}) AS median_val
        FROM silver.permits
        WHERE issued_date >= DATE '2021-01-01' AND {val_expr} IS NOT NULL
        GROUP BY 1
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE permits_v AS
        SELECT
          p.*,
          CASE
            WHEN {val_expr} IS NOT NULL THEN {val_expr}
            WHEN pm.median_val IS NOT NULL THEN pm.median_val
            WHEN cm.median_val IS NOT NULL THEN cm.median_val
            WHEN cat.median_val IS NOT NULL THEN cat.median_val
            ELSE 0
          END AS valuation_filled,
          CASE WHEN category IN ({ph}) THEN TRUE ELSE FALSE END AS is_sam,
          EXTRACT(year FROM issued_date)::INT AS yr,
          EXTRACT(month FROM issued_date)::INT AS mo
        FROM silver.permits p
        LEFT JOIN peer_medians pm USING (category, county)
        LEFT JOIN county_medians cm USING (county)
        LEFT JOIN cat_medians cat USING (category)
        WHERE p.issued_date >= DATE '2021-01-01'
          AND p.issued_date <= DATE '{as_of.isoformat()}'
        """,
        cats,
    )

    # --- YTD through month (sparse Nov excluded) ---
    ytd_through = as_of.month
    cur_n = con.execute(
        f"SELECT COUNT(*) FROM permits_v WHERE yr={as_of.year} AND mo={as_of.month}"
    ).fetchone()[0]
    prior_n = con.execute(
        f"SELECT COUNT(*) FROM permits_v WHERE yr={as_of.year-1} AND mo={as_of.month}"
    ).fetchone()[0]
    if prior_n and cur_n < 0.25 * prior_n:
        ytd_through = as_of.month - 1

    def monthly(where: str = "1=1") -> list[dict]:
        rows = con.execute(
            f"""
            SELECT yr, mo, COUNT(*), SUM(valuation_filled)
            FROM permits_v WHERE {where}
            GROUP BY 1, 2 ORDER BY 1, 2
            """
        ).fetchall()
        return [
            {
                "year": int(r[0]),
                "month": int(r[1]),
                "count": int(r[2]),
                "valuation": float(r[3] or 0),
            }
            for r in rows
        ]

    tom_monthly = monthly()
    sam_monthly = monthly("is_sam")

    tom_count_series, tom_count_proj = _project_monthly(tom_monthly, "count", as_of)
    tom_val_series, tom_val_proj = _project_monthly(tom_monthly, "valuation", as_of)
    sam_count_series, sam_count_proj = _project_monthly(sam_monthly, "count", as_of)
    sam_val_series, sam_val_proj = _project_monthly(sam_monthly, "valuation", as_of)

    # YTD by year for 2021–as_of.year (same months 1..ytd_through)
    def ytd_table(where: str = "1=1") -> list[dict]:
        out = []
        for y in range(2021, as_of.year + 1):
            r = con.execute(
                f"""
                SELECT COUNT(*), SUM(valuation_filled)
                FROM permits_v
                WHERE {where} AND yr = ? AND mo <= ?
                """,
                [y, ytd_through],
            ).fetchone()
            out.append(
                {
                    "year": y,
                    "through_month": ytd_through,
                    "count": int(r[0]),
                    "valuation": float(r[1] or 0),
                }
            )
        # attach YoY vs prior year same YTD
        for i, row in enumerate(out):
            if i == 0:
                row["count_yoy_pct"] = None
                row["valuation_yoy_pct"] = None
            else:
                row["count_yoy_pct"] = _yoy(row["count"], out[i - 1]["count"])
                row["valuation_yoy_pct"] = _yoy(row["valuation"], out[i - 1]["valuation"])
        return out

    tom_ytd = ytd_table()
    sam_ytd = ytd_table("is_sam")

    # Full annual
    def annual(where: str = "1=1") -> list[dict]:
        rows = con.execute(
            f"""
            SELECT yr, COUNT(*), SUM(valuation_filled)
            FROM permits_v WHERE {where}
            GROUP BY 1 ORDER BY 1
            """
        ).fetchall()
        out = [
            {"year": int(r[0]), "count": int(r[1]), "valuation": float(r[2] or 0)}
            for r in rows
        ]
        for i, row in enumerate(out):
            if i == 0:
                row["count_yoy_pct"] = None
                row["valuation_yoy_pct"] = None
            else:
                row["count_yoy_pct"] = _yoy(row["count"], out[i - 1]["count"])
                row["valuation_yoy_pct"] = _yoy(row["valuation"], out[i - 1]["valuation"])
        return out

    # Segment / category annual + YTD
    seg_annual = [
        {
            "segment": r[0],
            "year": int(r[1]),
            "count": int(r[2]),
            "valuation": float(r[3] or 0),
        }
        for r in con.execute(
            """
            SELECT
              CASE
                WHEN category = 'res_new_plumbing' THEN 'new_residential_plumbing'
                WHEN category IN ('res_repipe','res_remodel_plumbing') THEN 'plumbing_repipe_remodel'
                WHEN category = 'pool_spa' THEN 'pool_spa'
                WHEN category = 'irrigation' THEN 'irrigation'
                ELSE 'other'
              END AS segment,
              yr, COUNT(*), SUM(valuation_filled)
            FROM permits_v
            GROUP BY 1, 2 ORDER BY 1, 2
            """
        ).fetchall()
    ]

    # SAM by category by year with material/labor + SOM
    cat_year_rows = con.execute(
        f"""
        SELECT category, yr, COUNT(*), SUM(valuation_filled)
        FROM permits_v WHERE is_sam
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    ).fetchall()
    sam_by_cat_year = []
    for cat, yr, n, v in cat_year_rows:
        v = float(v or 0)
        # for repipe, material is per-project fixed × count
        if cat == "res_repipe":
            mat = float(
                mat_cfg.get("res_repipe", {}).get("fittings_value_usd", {}).get("base", 450)
            ) * int(n)
            lab = mat * 2.0
        else:
            mat, lab = _material_labor(cat, v, assumptions)
        sam_by_cat_year.append(
            {
                "category": cat,
                "year": int(yr),
                "count": int(n),
                "valuation": v,
                "material_usd": mat,
                "labor_usd": lab,
                "som_usd": v * SOM_SHARE,
                "som_material_usd": mat * SOM_SHARE,
                "som_labor_usd": lab * SOM_SHARE,
            }
        )

    # YTD by category (current as_of year through ytd_through)
    cat_ytd = []
    for cat, n, v in con.execute(
        f"""
        SELECT category, COUNT(*), SUM(valuation_filled)
        FROM permits_v
        WHERE is_sam AND yr = ? AND mo <= ?
        GROUP BY 1
        """,
        [as_of.year, ytd_through],
    ).fetchall():
        v = float(v or 0)
        if cat == "res_repipe":
            mat = float(
                mat_cfg.get("res_repipe", {}).get("fittings_value_usd", {}).get("base", 450)
            ) * int(n)
            lab = mat * 2.0
        else:
            mat, lab = _material_labor(cat, v, assumptions)
        # prior year same YTD
        pn, pv = con.execute(
            f"""
            SELECT COUNT(*), SUM(valuation_filled)
            FROM permits_v
            WHERE is_sam AND category = ? AND yr = ? AND mo <= ?
            """,
            [cat, as_of.year - 1, ytd_through],
        ).fetchone()
        cat_ytd.append(
            {
                "category": cat,
                "year": as_of.year,
                "through_month": ytd_through,
                "count": int(n),
                "valuation": v,
                "material_usd": mat,
                "labor_usd": lab,
                "som_usd": v * SOM_SHARE,
                "count_yoy_pct": _yoy(int(n), int(pn or 0)),
                "valuation_yoy_pct": _yoy(v, float(pv or 0)),
            }
        )

    # Overall SAM/TOM
    tot = con.execute(
        """
        SELECT COUNT(*), COUNT(*) FILTER (WHERE is_sam),
               SUM(valuation_filled), SUM(valuation_filled) FILTER (WHERE is_sam)
        FROM permits_v
        """
    ).fetchone()
    tom_n, sam_n, tom_v, sam_v = int(tot[0]), int(tot[1]), float(tot[2] or 0), float(tot[3] or 0)

    # gold fittings if present
    fittings_base = None
    if (
        con.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema='gold' AND table_name='material_estimates'
            """
        ).fetchone()[0]
        > 0
    ):
        fittings_base = float(
            con.execute("SELECT SUM(fittings_base) FROM gold.material_estimates").fetchone()[0]
            or 0
        )

    # Counties for map
    counties = []
    for r in con.execute(
        """
        SELECT COALESCE(county,'Unknown'),
               COUNT(*), COUNT(*) FILTER (WHERE is_sam),
               SUM(valuation_filled), SUM(valuation_filled) FILTER (WHERE is_sam)
        FROM permits_v
        GROUP BY 1 ORDER BY 4 DESC
        """
    ).fetchall():
        name = r[0]
        counties.append(
            {
                "county": name,
                "fips": COUNTY_FIPS.get(name),
                "tom_count": int(r[1]),
                "sam_count": int(r[2]),
                "tom_valuation": float(r[3] or 0),
                "sam_valuation": float(r[4] or 0),
                "som_usd": float(r[4] or 0) * SOM_SHARE,
            }
        )

    # County monthly for near-term (SAM)
    county_monthly = [
        {
            "county": r[0],
            "year": int(r[1]),
            "month": int(r[2]),
            "count": int(r[3]),
            "valuation": float(r[4] or 0),
        }
        for r in con.execute(
            """
            SELECT COALESCE(county,'Unknown'), yr, mo, COUNT(*), SUM(valuation_filled)
            FROM permits_v WHERE is_sam
            GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
            """
        ).fetchall()
    ]

    # Miami-Dade mesoregions
    miami_rows = con.execute(
        """
        SELECT jurisdiction_id, address_raw, city, is_sam, valuation_filled, yr, mo,
               contractor_name, category
        FROM permits_v
        WHERE county = 'Miami-Dade'
        """
    ).fetchall()
    meso: dict[str, dict[str, float | int]] = {}
    for jid, addr, city, is_sam, val, yr, mo, _cname, _cat in miami_rows:
        area = _miami_area(addr, city, jid)
        bucket = meso.setdefault(
            area,
            {
                "area": area,
                "tom_count": 0,
                "sam_count": 0,
                "tom_valuation": 0.0,
                "sam_valuation": 0.0,
            },
        )
        bucket["tom_count"] = int(bucket["tom_count"]) + 1
        bucket["tom_valuation"] = float(bucket["tom_valuation"]) + float(val or 0)
        if is_sam:
            bucket["sam_count"] = int(bucket["sam_count"]) + 1
            bucket["sam_valuation"] = float(bucket["sam_valuation"]) + float(val or 0)
    miami_meso = sorted(
        (
            {
                **b,
                "som_usd": float(b["sam_valuation"]) * SOM_SHARE,
                "note": (
                    "Most Miami-Dade Hub rows lack city/ZIP; "
                    "'Unincorporated / other' dominates unless address matches a municipality."
                ),
            }
            for b in meso.values()
        ),
        key=lambda x: -float(x["sam_valuation"]),
    )

    # Jurisdiction split for Miami
    miami_jur = [
        {
            "jurisdiction_id": r[0],
            "tom_count": int(r[1]),
            "sam_count": int(r[2]),
            "tom_valuation": float(r[3] or 0),
            "sam_valuation": float(r[4] or 0),
            "som_usd": float(r[4] or 0) * SOM_SHARE,
        }
        for r in con.execute(
            """
            SELECT jurisdiction_id, COUNT(*), COUNT(*) FILTER (WHERE is_sam),
                   SUM(valuation_filled), SUM(valuation_filled) FILTER (WHERE is_sam)
            FROM permits_v WHERE county='Miami-Dade'
            GROUP BY 1 ORDER BY 2 DESC
            """
        ).fetchall()
    ]

    # Contractors: YTD + last complete month (near-term demand)
    near_month = ytd_through  # e.g. October 2026
    near_year = as_of.year

    def top_contractors(extra_where: str, params: list[Any], limit: int = 30) -> list[dict]:
        rows = con.execute(
            f"""
            SELECT UPPER(TRIM(contractor_name)) AS cname,
                   COUNT(*) AS n,
                   SUM(valuation_filled) AS v,
                   STRING_AGG(DISTINCT county, ', ') AS counties,
                   STRING_AGG(DISTINCT category, ', ') AS cats
            FROM permits_v
            WHERE is_sam
              AND contractor_name IS NOT NULL
              AND TRIM(contractor_name) <> ''
              AND UPPER(TRIM(contractor_name)) NOT IN
                ('OWNER','OWNER BUILDER','OWNER/BUILDER','N/A','NA','NONE','UNKNOWN')
              AND COALESCE(is_owner_builder, FALSE) = FALSE
              AND {extra_where}
            GROUP BY 1
            ORDER BY n DESC
            LIMIT {limit}
            """,
            params,
        ).fetchall()
        # also rank by valuation version
        return [
            {
                "contractor_name": r[0],
                "permits": int(r[1]),
                "valuation": float(r[2] or 0),
                "counties": r[3],
                "categories": r[4],
            }
            for r in rows
        ]

    contractors_ytd = top_contractors(
        "yr = ? AND mo <= ?", [as_of.year, ytd_through], 40
    )
    contractors_ytd_by_val = con.execute(
        f"""
        SELECT UPPER(TRIM(contractor_name)), COUNT(*), SUM(valuation_filled),
               STRING_AGG(DISTINCT county, ', '), STRING_AGG(DISTINCT category, ', ')
        FROM permits_v
        WHERE is_sam AND contractor_name IS NOT NULL AND TRIM(contractor_name) <> ''
          AND UPPER(TRIM(contractor_name)) NOT IN
            ('OWNER','OWNER BUILDER','OWNER/BUILDER','N/A','NA','NONE','UNKNOWN')
          AND COALESCE(is_owner_builder, FALSE) = FALSE
          AND yr = ? AND mo <= ?
        GROUP BY 1 ORDER BY 3 DESC LIMIT 40
        """,
        [as_of.year, ytd_through],
    ).fetchall()
    contractors_near = top_contractors("yr = ? AND mo = ?", [near_year, near_month], 40)
    contractors_near_by_val = [
        {
            "contractor_name": r[0],
            "permits": int(r[1]),
            "valuation": float(r[2] or 0),
            "counties": r[3],
            "categories": r[4],
        }
        for r in con.execute(
            f"""
            SELECT UPPER(TRIM(contractor_name)), COUNT(*), SUM(valuation_filled),
                   STRING_AGG(DISTINCT county, ', '), STRING_AGG(DISTINCT category, ', ')
            FROM permits_v
            WHERE is_sam AND contractor_name IS NOT NULL AND TRIM(contractor_name) <> ''
              AND UPPER(TRIM(contractor_name)) NOT IN
                ('OWNER','OWNER BUILDER','OWNER/BUILDER','N/A','NA','NONE','UNKNOWN')
              AND COALESCE(is_owner_builder, FALSE) = FALSE
              AND yr = ? AND mo = ?
            GROUP BY 1 ORDER BY 3 DESC LIMIT 40
            """,
            [near_year, near_month],
        ).fetchall()
    ]

    cov = con.execute(
        """
        SELECT COUNT(*), 
               COUNT(*) FILTER (WHERE contractor_name IS NOT NULL AND TRIM(contractor_name)<>''),
               COUNT(*) FILTER (WHERE is_sam),
               COUNT(*) FILTER (WHERE is_sam AND contractor_name IS NOT NULL AND TRIM(contractor_name)<>'')
        FROM permits_v
        """
    ).fetchone()

    # Material/labor annual totals for SAM
    mat_lab_year: dict[int, dict[str, float]] = {}
    for row in sam_by_cat_year:
        y = row["year"]
        b = mat_lab_year.setdefault(y, {"material_usd": 0.0, "labor_usd": 0.0, "valuation": 0.0})
        b["material_usd"] += row["material_usd"]
        b["labor_usd"] += row["labor_usd"]
        b["valuation"] += row["valuation"]
    material_labor_annual = [
        {
            "year": y,
            **vals,
            "som_usd": vals["valuation"] * SOM_SHARE,
            "som_material_usd": vals["material_usd"] * SOM_SHARE,
            "som_labor_usd": vals["labor_usd"] * SOM_SHARE,
        }
        for y, vals in sorted(mat_lab_year.items())
    ]

    # Enrich Miami meso with material / SOM material (all-time in DB window)
    for b in miami_meso:
        # approximate material from SAM valuation using blended plumbing share assumptions
        # directional: use category mix for Miami if available — else 35% of plumbing portion of SAM $
        sam_v_area = float(b["sam_valuation"])
        # rough: treat as new_residential-heavy Miami mix → plumbing share × material share
        mat, lab = _material_labor("res_new_plumbing", sam_v_area, assumptions)
        b["material_usd"] = mat
        b["labor_usd"] = lab
        b["som_usd"] = sam_v_area * SOM_SHARE
        b["som_material_usd"] = mat * SOM_SHARE

    for j in miami_jur:
        mat, lab = _material_labor("res_new_plumbing", float(j["sam_valuation"]), assumptions)
        j["material_usd"] = mat
        j["labor_usd"] = lab
        j["som_material_usd"] = mat * SOM_SHARE

    # County material SOM (all history in window) for map metric
    for c in counties:
        mat, _lab = _material_labor("res_new_plumbing", float(c["sam_valuation"]), assumptions)
        # better: weight by actual category mix per county
        c["material_usd"] = 0.0
        c["som_material_usd"] = 0.0
    # overwrite with true category mix
    county_mat: dict[str, float] = {}
    for cat, county, n, v in con.execute(
        """
        SELECT category, COALESCE(county,'Unknown'), COUNT(*), SUM(valuation_filled)
        FROM permits_v WHERE is_sam GROUP BY 1, 2
        """
    ).fetchall():
        if cat == "res_repipe":
            mat = float(
                mat_cfg.get("res_repipe", {}).get("fittings_value_usd", {}).get("base", 450)
            ) * int(n)
        else:
            mat, _ = _material_labor(cat, float(v or 0), assumptions)
        county_mat[county] = county_mat.get(county, 0.0) + mat
    for c in counties:
        c["material_usd"] = county_mat.get(c["county"], 0.0)
        c["som_material_usd"] = float(c["material_usd"]) * SOM_SHARE

    # --- Pipeline short-term: last 30 / 60 days ---
    def pipeline_window(days: int) -> dict:
        from datetime import timedelta

        start = as_of - timedelta(days=days)
        # inclusive of as_of; exclusive of start day boundary via >
        rows = con.execute(
            """
            SELECT category, COALESCE(county,'Unknown'), COUNT(*), SUM(valuation_filled),
                   UPPER(TRIM(COALESCE(contractor_name,'')))
            FROM permits_v
            WHERE is_sam AND issued_date > ? AND issued_date <= ?
            GROUP BY 1, 2, 5
            """,
            [start, as_of],
        ).fetchall()
        by_county: dict[str, dict[str, float | int]] = {}
        by_cat: dict[str, dict[str, float | int]] = {}
        by_contractor: dict[str, dict[str, Any]] = {}
        for cat, county, n, v, cname in rows:
            v = float(v or 0)
            n = int(n)
            if cat == "res_repipe":
                mat = float(
                    mat_cfg.get("res_repipe", {}).get("fittings_value_usd", {}).get("base", 450)
                ) * n
                lab = mat * 2.0
            else:
                mat, lab = _material_labor(cat, v, assumptions)
            bc = by_county.setdefault(
                county,
                {
                    "county": county,
                    "fips": COUNTY_FIPS.get(county),
                    "sam_count": 0,
                    "sam_valuation": 0.0,
                    "material_usd": 0.0,
                    "labor_usd": 0.0,
                },
            )
            bc["sam_count"] = int(bc["sam_count"]) + n
            bc["sam_valuation"] = float(bc["sam_valuation"]) + v
            bc["material_usd"] = float(bc["material_usd"]) + mat
            bc["labor_usd"] = float(bc["labor_usd"]) + lab
            bcat = by_cat.setdefault(
                cat,
                {
                    "category": cat,
                    "sam_count": 0,
                    "sam_valuation": 0.0,
                    "material_usd": 0.0,
                    "labor_usd": 0.0,
                },
            )
            bcat["sam_count"] = int(bcat["sam_count"]) + n
            bcat["sam_valuation"] = float(bcat["sam_valuation"]) + v
            bcat["material_usd"] = float(bcat["material_usd"]) + mat
            bcat["labor_usd"] = float(bcat["labor_usd"]) + lab
            if cname and cname not in (
                "",
                "OWNER",
                "OWNER BUILDER",
                "OWNER/BUILDER",
                "N/A",
                "NA",
                "NONE",
                "UNKNOWN",
            ):
                bt = by_contractor.setdefault(
                    cname,
                    {
                        "contractor_name": cname,
                        "permits": 0,
                        "valuation": 0.0,
                        "material_usd": 0.0,
                        "counties": set(),
                        "categories": set(),
                    },
                )
                bt["permits"] = int(bt["permits"]) + n
                bt["valuation"] = float(bt["valuation"]) + v
                bt["material_usd"] = float(bt["material_usd"]) + mat
                bt["counties"].add(county)
                bt["categories"].add(cat)

        counties_out = sorted(
            (
                {
                    **b,
                    "som_usd": float(b["sam_valuation"]) * SOM_SHARE,
                    "som_material_usd": float(b["material_usd"]) * SOM_SHARE,
                }
                for b in by_county.values()
            ),
            key=lambda x: -float(x["som_material_usd"]),
        )
        cats_out = sorted(
            (
                {
                    **b,
                    "som_usd": float(b["sam_valuation"]) * SOM_SHARE,
                    "som_material_usd": float(b["material_usd"]) * SOM_SHARE,
                }
                for b in by_cat.values()
            ),
            key=lambda x: -float(x["som_material_usd"]),
        )
        contractors_out = sorted(
            (
                {
                    "contractor_name": b["contractor_name"],
                    "permits": int(b["permits"]),
                    "valuation": float(b["valuation"]),
                    "material_usd": float(b["material_usd"]),
                    "som_material_usd": float(b["material_usd"]) * SOM_SHARE,
                    "counties": ", ".join(sorted(b["counties"])),
                    "categories": ", ".join(sorted(b["categories"])),
                }
                for b in by_contractor.values()
            ),
            key=lambda x: -x["som_material_usd"],
        )[:40]
        tot_sam = sum(float(c["sam_valuation"]) for c in counties_out)
        tot_mat = sum(float(c["material_usd"]) for c in counties_out)
        tot_n = sum(int(c["sam_count"]) for c in counties_out)
        return {
            "days": days,
            "start": start.isoformat(),
            "end": as_of.isoformat(),
            "sam_count": tot_n,
            "sam_valuation": tot_sam,
            "material_usd": tot_mat,
            "som_usd": tot_sam * SOM_SHARE,
            "som_material_usd": tot_mat * SOM_SHARE,
            "by_county": counties_out,
            "by_category": cats_out,
            "by_contractor": contractors_out,
        }

    pipeline = {
        "d30": pipeline_window(30),
        "d60": pipeline_window(60),
        "note": (
            "Permits issued in the last N days — pragmatic commercial chase list. "
            "SOM material = 5% of estimated material content in the window."
        ),
    }

    # Per-year SAM share of TOM (for year filter chips)
    share_by_year = []
    for y in range(2021, as_of.year + 1):
        r = con.execute(
            """
            SELECT COUNT(*), COUNT(*) FILTER (WHERE is_sam),
                   SUM(valuation_filled), SUM(valuation_filled) FILTER (WHERE is_sam)
            FROM permits_v WHERE yr = ?
            """,
            [y],
        ).fetchone()
        tn, sn, tv, sv = int(r[0]), int(r[1]), float(r[2] or 0), float(r[3] or 0)
        share_by_year.append(
            {
                "year": y,
                "tom_count": tn,
                "sam_count": sn,
                "tom_valuation": tv,
                "sam_valuation": sv,
                "sam_share_count_pct": _pct(sn, tn),
                "sam_share_valuation_pct": _pct(sv, tv),
                "som_usd": sv * SOM_SHARE,
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of.isoformat(),
        "ytd_through_month": ytd_through,
        "near_term_month": {"year": near_year, "month": near_month},
        "definitions": {
            "TOM": "All permits issued ≥ 2021-01-01",
            "SAM": "plumbing (new/repipe/remodel incl. new residential) + pool/spa + irrigation",
            "SOM": "5% of SAM addressable project $",
            "YTD": f"Jan–{ytd_through} same months across years (sparse as-of month excluded)",
            "material_labor": (
                "Plumbing: project$ × plumbing_share(4.5%) split 35% material / 65% labor; "
                "pool/irrigation: fittings_share of project = material, remainder labor/other; "
                "repipe: fixed fittings$ material + 2× labor proxy"
            ),
            "miami_mesoregions": (
                "City of Miami jurisdiction vs county Hub; Hub mesoregions from address "
                "municipality regex when present — most Hub rows lack city/ZIP"
            ),
        },
        "assumptions": {
            "som_share": SOM_SHARE,
            "plumbing_share_of_project": 0.045,
            "material_share_of_plumbing": 0.35,
            "fittings_share_of_material": 0.18,
            "pool_fittings_share": 0.08,
            "irrigation_fittings_share": 0.12,
        },
        "universe": {
            "tom": tom_n,
            "sam": sam_n,
            "sam_share_count_pct": _pct(sam_n, tom_n),
            "tom_valuation": tom_v,
            "sam_valuation": sam_v,
            "sam_share_valuation_pct": _pct(sam_v, tom_v),
            "som_usd": sam_v * SOM_SHARE,
            "fittings_sam_usd": fittings_base,
            "fittings_som_usd": (fittings_base or 0) * SOM_SHARE,
            "counties": len(counties),
            "jurisdictions": int(
                con.execute("SELECT COUNT(DISTINCT jurisdiction_id) FROM permits_v").fetchone()[0]
            ),
        },
        "tom": {
            "annual": annual(),
            "ytd_comparison": tom_ytd,
            "monthly": tom_monthly,
            "monthly_count_with_projection": tom_count_series,
            "monthly_valuation_with_projection": tom_val_series,
            "projection_count": tom_count_proj,
            "projection_valuation": tom_val_proj,
        },
        "sam_som": {
            "share": {
                "sam_count": sam_n,
                "tom_count": tom_n,
                "sam_share_count_pct": _pct(sam_n, tom_n),
                "sam_valuation": sam_v,
                "tom_valuation": tom_v,
                "sam_share_valuation_pct": _pct(sam_v, tom_v),
                "som_usd": sam_v * SOM_SHARE,
            },
            "annual": annual("is_sam"),
            "ytd_comparison": sam_ytd,
            "monthly": sam_monthly,
            "monthly_count_with_projection": sam_count_series,
            "monthly_valuation_with_projection": sam_val_series,
            "projection_count": sam_count_proj,
            "projection_valuation": sam_val_proj,
            "by_category_year": sam_by_cat_year,
            "by_category_ytd": cat_ytd,
            "material_labor_annual": material_labor_annual,
            "segment_annual": seg_annual,
            "share_by_year": share_by_year,
        },
        "pipeline": pipeline,
        "regions": {
            "counties": counties,
            "county_monthly_sam": county_monthly,
            "miami_dade": {
                "jurisdictions": miami_jur,
                "mesoregions": miami_meso,
                "coverage_note": (
                    "ZIP/lat mostly missing on Miami feeds. Drill = City of Miami layer vs "
                    "county Hub + municipality tokens parsed from address when available. "
                    "SOM material on meso uses directional plumbing material share on SAM $."
                ),
            },
        },
        "contractors": {
            "coverage": {
                "tom": int(cov[0]),
                "tom_with_name": int(cov[1]),
                "tom_coverage_pct": _pct(cov[1], cov[0]),
                "sam": int(cov[2]),
                "sam_with_name": int(cov[3]),
                "sam_coverage_pct": _pct(cov[3], cov[2]),
            },
            "ytd_by_permits": contractors_ytd,
            "ytd_by_valuation": [
                {
                    "contractor_name": r[0],
                    "permits": int(r[1]),
                    "valuation": float(r[2] or 0),
                    "counties": r[3],
                    "categories": r[4],
                }
                for r in contractors_ytd_by_val
            ],
            "near_term_by_permits": contractors_near,
            "near_term_by_valuation": contractors_near_by_val,
            "near_term_label": f"{near_year}-{near_month:02d} (last complete month)",
            "notes": (
                "Near-term = last complete month of permit issuance — best proxy for "
                "purchase window now. Owner-builder / blank excluded."
            ),
        },
        "formatted_headlines": {
            "tom_count": f"{tom_n:,}",
            "sam_count": f"{sam_n:,}",
            "sam_share": f"{_pct(sam_n, tom_n)}%",
            "sam_share_val": f"{_pct(sam_v, tom_v)}%",
            "tom_valuation": _fmt(tom_v),
            "sam_valuation": _fmt(sam_v),
            "som": _fmt(sam_v * SOM_SHARE),
            "fittings_som": _fmt((fittings_base or 0) * SOM_SHARE),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {args.out} ({args.out.stat().st_size:,} bytes)")
    print(
        f"TOM={tom_n:,} SAM={sam_n:,} SOM={_fmt(sam_v * SOM_SHARE)} "
        f"YTD through m{ytd_through} near={near_year}-{near_month:02d}"
    )


if __name__ == "__main__":
    main()

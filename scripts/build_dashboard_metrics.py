#!/usr/bin/env python3
"""Build TOM/SAM/SOM dashboard metrics JSON from silver.permits (+ gold if present).

Answers executive questions 1–6 with locked definitions:
  TOM = all permits issued ≥ 2021
  SAM = plumbing + pool/spa + irrigation + new residential construction
  SOM = 5% of SAM addressable $ (valuation with peer median fill)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.rules import SAM_CATEGORIES  # noqa: E402
from src.db import connect  # noqa: E402
from src.model.material import estimate_fittings_value  # noqa: E402
from src.registry import load_assumptions  # noqa: E402

SOM_SHARE = 0.05
OUTLIER_CAP = 1_000_000_000.0  # ≥$1B flagged; still included unless --cap-outliers
YEAR_END_2026 = date(2026, 12, 31)
AS_OF = date(2026, 11, 1)


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
    """Trailing 3 complete months' average YoY growth (skip sparse current month)."""
    growths = []
    # Prefer months strictly before `m` in year y, then walk back
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


def _linear_project(months: list[dict], value_key: str, as_of: date, year_end: date) -> dict:
    """Project remaining months of year from recent YoY / monthly trend.

    If the as-of month is sparse (<25% of prior-year same month), treat it as
    incomplete: YTD excludes it and the month is re-projected in full.
    """
    by_ym = {(r["year"], r["month"]): r for r in months}
    y, m = as_of.year, as_of.month
    cur = by_ym.get((y, m))
    prior_same = by_ym.get((y - 1, m))
    sparse = False
    if cur and prior_same and prior_same[value_key] > 0:
        sparse = cur[value_key] < 0.25 * prior_same[value_key]
    elif cur is None:
        sparse = True

    last_complete_month = m - 1 if sparse else m
    if last_complete_month <= 0:
        last_complete_month = 0
    ytd = sum(
        r[value_key]
        for r in months
        if r["year"] == y and r["month"] <= last_complete_month
    )
    g = _growth_factor(by_ym, y, m if not sparse else m, value_key)
    start_rm = m if sparse else m + 1
    remaining = []
    for rm in range(start_rm, 13):
        prior = by_ym.get((y - 1, rm))
        if prior:
            pred = prior[value_key] * g
        else:
            recent = []
            for back in range(1, 4):
                mm = last_complete_month - back + 1
                yy = y
                while mm <= 0:
                    mm += 12
                    yy -= 1
                if (yy, mm) in by_ym:
                    recent.append(by_ym[(yy, mm)][value_key])
            pred = (sum(recent) / len(recent)) if recent else 0.0
        remaining.append({"year": y, "month": rm, "projected": pred, "growth_factor": g})
    ytg = sum(r["projected"] for r in remaining)
    return {
        "as_of": as_of.isoformat(),
        "year_end": year_end.isoformat(),
        "ytd": ytd,
        "ytd_through_month": last_complete_month,
        "current_month_sparse": sparse,
        "ytg_expected": ytg,
        "full_year_expected": ytd + ytg,
        "remaining_months": remaining,
        "method": (
            "prior-year same month × trailing-3m YoY growth; "
            "sparse as-of month excluded from YTD and fully re-projected"
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=ROOT / "permits.duckdb")
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "dashboard" / "public" / "data" / "metrics.json",
    )
    p.add_argument("--cap-outliers", action="store_true", help="Exclude valuation ≥ $1B")
    p.add_argument("--as-of", default=AS_OF.isoformat())
    args = p.parse_args()
    as_of = date.fromisoformat(args.as_of)

    assumptions = load_assumptions()
    mat_cfg = assumptions.get("material_content", {})
    # Headline material/labor split for construction $ (plumbing material share base)
    plumbing_mat_share = float(
        mat_cfg.get("res_new_plumbing", {})
        .get("material_share_of_plumbing", {})
        .get("base", 0.35)
    )
    pool_fit_share = float(
        mat_cfg.get("pool_spa", {}).get("fittings_share_of_project", {}).get("base", 0.08)
    )
    irrig_fit_share = float(
        mat_cfg.get("irrigation", {}).get("fittings_share_of_project", {}).get("base", 0.12)
    )

    con = connect(args.db)
    cats = sorted(SAM_CATEGORIES)
    ph = ",".join("?" * len(cats))

    # Cap outliers for analytics valuation if requested
    val_expr = (
        f"CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 "
        f"AND declared_valuation < {OUTLIER_CAP} THEN declared_valuation ELSE NULL END"
        if args.cap_outliers
        else "CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 "
        "THEN declared_valuation ELSE NULL END"
    )

    # --- Peer median valuation by (category, county) for imputation ---
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE peer_medians AS
        SELECT category, county,
               median({val_expr}) AS median_val,
               COUNT(*) FILTER (WHERE {val_expr} IS NOT NULL) AS n_decl
        FROM silver.permits
        WHERE issued_date >= DATE '2021-01-01'
        GROUP BY 1, 2
        """
    )
    # County-only fallback
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE county_medians AS
        SELECT county,
               median({val_expr}) AS median_val
        FROM silver.permits
        WHERE issued_date >= DATE '2021-01-01'
          AND {val_expr} IS NOT NULL
        GROUP BY 1
        """
    )
    # Category-only fallback
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE cat_medians AS
        SELECT category,
               median({val_expr}) AS median_val
        FROM silver.permits
        WHERE issued_date >= DATE '2021-01-01'
          AND {val_expr} IS NOT NULL
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
          CASE
            WHEN {val_expr} IS NOT NULL THEN 'declared'
            WHEN pm.median_val IS NOT NULL THEN 'peer_category_county_median'
            WHEN cm.median_val IS NOT NULL THEN 'peer_county_median'
            WHEN cat.median_val IS NOT NULL THEN 'peer_category_median'
            ELSE 'zero'
          END AS valuation_method,
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

    meta = con.execute(
        """
        SELECT COUNT(*) AS tom,
               COUNT(*) FILTER (WHERE is_sam) AS sam,
               MIN(issued_date) AS min_d,
               MAX(issued_date) AS max_d,
               COUNT(DISTINCT county) AS counties,
               COUNT(DISTINCT jurisdiction_id) AS jurisdictions
        FROM permits_v
        """
    ).fetchone()

    # --- Q1 TOM YoY + 2026 YTG ---
    tom_monthly = [
        {"year": int(r[0]), "month": int(r[1]), "count": int(r[2]), "valuation": float(r[3] or 0)}
        for r in con.execute(
            """
            SELECT yr, mo, COUNT(*), SUM(valuation_filled)
            FROM permits_v
            GROUP BY 1, 2
            ORDER BY 1, 2
            """
        ).fetchall()
    ]
    tom_annual = [
        {"year": int(r[0]), "count": int(r[1]), "valuation": float(r[2] or 0)}
        for r in con.execute(
            """
            SELECT yr, COUNT(*), SUM(valuation_filled)
            FROM permits_v
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
    ]
    by_year = {r["year"]: r for r in tom_annual}
    # For the incomplete as-of year, YoY uses YTD vs same months prior year
    max_complete_month = max(
        (r["month"] for r in tom_monthly if r["year"] == as_of.year),
        default=0,
    )
    # If current month sparse (<25% of prior), exclude it from YTD YoY
    cur_m_row = next(
        (r for r in tom_monthly if r["year"] == as_of.year and r["month"] == as_of.month),
        None,
    )
    prior_m_row = next(
        (
            r
            for r in tom_monthly
            if r["year"] == as_of.year - 1 and r["month"] == as_of.month
        ),
        None,
    )
    ytd_through = as_of.month
    if (
        cur_m_row
        and prior_m_row
        and prior_m_row["count"] > 0
        and cur_m_row["count"] < 0.25 * prior_m_row["count"]
    ):
        ytd_through = as_of.month - 1
    tom_yoy = []
    for y in sorted(by_year):
        if y == as_of.year and ytd_through > 0:
            ytd_count = sum(
                r["count"]
                for r in tom_monthly
                if r["year"] == y and r["month"] <= ytd_through
            )
            ytd_val = sum(
                r["valuation"]
                for r in tom_monthly
                if r["year"] == y and r["month"] <= ytd_through
            )
            prior_count = sum(
                r["count"]
                for r in tom_monthly
                if r["year"] == y - 1 and r["month"] <= ytd_through
            )
            prior_val = sum(
                r["valuation"]
                for r in tom_monthly
                if r["year"] == y - 1 and r["month"] <= ytd_through
            )
            tom_yoy.append(
                {
                    "year": y,
                    "count": by_year[y]["count"],
                    "valuation": by_year[y]["valuation"],
                    "ytd_through_month": ytd_through,
                    "ytd_count": ytd_count,
                    "ytd_valuation": ytd_val,
                    "count_yoy_pct": _yoy(ytd_count, prior_count),
                    "valuation_yoy_pct": _yoy(ytd_val, prior_val),
                    "yoy_basis": f"YTD Jan–{ytd_through} vs prior-year same months",
                }
            )
        elif y - 1 in by_year:
            tom_yoy.append(
                {
                    "year": y,
                    "count": by_year[y]["count"],
                    "valuation": by_year[y]["valuation"],
                    "count_yoy_pct": _yoy(by_year[y]["count"], by_year[y - 1]["count"]),
                    "valuation_yoy_pct": _yoy(
                        by_year[y]["valuation"], by_year[y - 1]["valuation"]
                    ),
                    "yoy_basis": "full_year",
                }
            )
        else:
            tom_yoy.append(
                {
                    "year": y,
                    "count": by_year[y]["count"],
                    "valuation": by_year[y]["valuation"],
                    "count_yoy_pct": None,
                    "valuation_yoy_pct": None,
                    "yoy_basis": None,
                }
            )

    tom_proj_count = _linear_project(tom_monthly, "count", as_of, YEAR_END_2026)
    tom_proj_val = _linear_project(tom_monthly, "valuation", as_of, YEAR_END_2026)

    # --- Q2 Segment trends ---
    segment_map_sql = """
      CASE
        WHEN category IN ('res_new_plumbing','res_repipe','res_remodel_plumbing') THEN 'plumbing'
        WHEN category = 'pool_spa' THEN 'pool_spa'
        WHEN category = 'irrigation' THEN 'irrigation'
        WHEN category = 'res_new_plumbing' THEN 'new_residential'
        ELSE 'other'
      END
    """
    # More precise: split plumbing subtypes + other
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
            GROUP BY 1, 2
            ORDER BY 1, 2
            """
        ).fetchall()
    ]
    seg_monthly = [
        {
            "segment": r[0],
            "year": int(r[1]),
            "month": int(r[2]),
            "count": int(r[3]),
            "valuation": float(r[4] or 0),
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
              yr, mo, COUNT(*), SUM(valuation_filled)
            FROM permits_v
            GROUP BY 1, 2, 3
            ORDER BY 1, 2, 3
            """
        ).fetchall()
    ]

    # --- Q3 SAM share, county trend, YE projection ---
    sam_share = {
        "tom_count": int(meta[0]),
        "sam_count": int(meta[1]),
        "sam_share_of_tom_count_pct": _pct(meta[1], meta[0]),
    }
    sam_usd = con.execute(
        """
        SELECT
          SUM(valuation_filled) FILTER (WHERE is_sam) AS sam_v,
          SUM(valuation_filled) AS tom_v
        FROM permits_v
        """
    ).fetchone()
    sam_share["sam_valuation"] = float(sam_usd[0] or 0)
    sam_share["tom_valuation"] = float(sam_usd[1] or 0)
    sam_share["sam_share_of_tom_valuation_pct"] = _pct(
        float(sam_usd[0] or 0), float(sam_usd[1] or 0)
    )

    sam_by_cat = [
        {
            "category": r[0],
            "count": int(r[1]),
            "valuation": float(r[2] or 0),
            "pct_of_sam_count": float(r[3] or 0),
            "pct_of_sam_valuation": float(r[4] or 0),
        }
        for r in con.execute(
            f"""
            WITH s AS (
              SELECT category, COUNT(*) AS c, SUM(valuation_filled) AS v
              FROM permits_v WHERE is_sam GROUP BY 1
            ), t AS (SELECT SUM(c) AS tc, SUM(v) AS tv FROM s)
            SELECT category, c, v,
                   100.0 * c / NULLIF(t.tc,0),
                   100.0 * v / NULLIF(t.tv,0)
            FROM s, t
            ORDER BY v DESC
            """
        ).fetchall()
    ]

    sam_county_monthly = [
        {
            "county": r[0] or "Unknown",
            "year": int(r[1]),
            "month": int(r[2]),
            "count": int(r[3]),
            "valuation": float(r[4] or 0),
        }
        for r in con.execute(
            """
            SELECT COALESCE(county, 'Unknown'), yr, mo, COUNT(*), SUM(valuation_filled)
            FROM permits_v
            WHERE is_sam
            GROUP BY 1, 2, 3
            ORDER BY 1, 2, 3
            """
        ).fetchall()
    ]
    sam_county_annual = [
        {
            "county": r[0] or "Unknown",
            "year": int(r[1]),
            "count": int(r[2]),
            "valuation": float(r[3] or 0),
        }
        for r in con.execute(
            """
            SELECT COALESCE(county, 'Unknown'), yr, COUNT(*), SUM(valuation_filled)
            FROM permits_v
            WHERE is_sam
            GROUP BY 1, 2
            ORDER BY 4 DESC
            """
        ).fetchall()
    ]
    # Top counties for dashboard
    top_counties = [
        {
            "county": r[0] or "Unknown",
            "count": int(r[1]),
            "valuation": float(r[2] or 0),
        }
        for r in con.execute(
            """
            SELECT COALESCE(county, 'Unknown'), COUNT(*), SUM(valuation_filled)
            FROM permits_v WHERE is_sam
            GROUP BY 1 ORDER BY 3 DESC LIMIT 15
            """
        ).fetchall()
    ]

    sam_monthly = [
        {"year": int(r[0]), "month": int(r[1]), "count": int(r[2]), "valuation": float(r[3] or 0)}
        for r in con.execute(
            """
            SELECT yr, mo, COUNT(*), SUM(valuation_filled)
            FROM permits_v WHERE is_sam
            GROUP BY 1, 2 ORDER BY 1, 2
            """
        ).fetchall()
    ]
    sam_proj_count = _linear_project(sam_monthly, "count", as_of, YEAR_END_2026)
    sam_proj_val = _linear_project(sam_monthly, "valuation", as_of, YEAR_END_2026)

    # --- Q4 SOM 5% + material/labor + imputation stats ---
    imput = con.execute(
        """
        SELECT valuation_method, COUNT(*), SUM(valuation_filled)
        FROM permits_v WHERE is_sam
        GROUP BY 1 ORDER BY 2 DESC
        """
    ).fetchall()
    imputation = [
        {"method": r[0], "count": int(r[1]), "valuation": float(r[2] or 0)} for r in imput
    ]

    sam_addressable = float(sam_usd[0] or 0)
    som_total = sam_addressable * SOM_SHARE

    # Material vs labor on SAM addressable construction $ using category weights
    # Plumbing cats: material_share_of_plumbing on the plumbing portion of project;
    # for exec split we apply material_share directly to SAM valuation for plumbing,
    # and fittings_share_of_project for pool/irrigation as the "material" share.
    mat_rows = con.execute(
        f"""
        SELECT category, SUM(valuation_filled)
        FROM permits_v WHERE is_sam
        GROUP BY 1
        """
    ).fetchall()
    material_usd = 0.0
    for cat, v in mat_rows:
        v = float(v or 0)
        if cat in ("res_new_plumbing", "res_repipe", "res_remodel_plumbing"):
            # For new construction valuation is whole project; apply plumbing×material chain base
            cfg = mat_cfg.get(cat, mat_cfg.get("res_new_plumbing", {}))
            if cfg.get("method") == "fixed_per_project":
                # Use fittings base × count approx — recompute from gold if available
                material_usd += 0.0  # filled below via fittings if present
            else:
                pl = float(cfg.get("plumbing_share_of_project_value", {}).get("base", 0.045))
                ms = float(cfg.get("material_share_of_plumbing", {}).get("base", plumbing_mat_share))
                material_usd += v * pl * ms
        elif cat == "pool_spa":
            material_usd += v * pool_fit_share
        elif cat == "irrigation":
            material_usd += v * irrig_fit_share

    # Prefer gold fittings if table exists
    has_gold = (
        con.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema='gold' AND table_name='material_estimates'
            """
        ).fetchone()[0]
        > 0
    )
    fittings_base = None
    if has_gold:
        fittings_base = float(
            con.execute("SELECT SUM(fittings_base) FROM gold.material_estimates").fetchone()[0]
            or 0
        )
        # Align material with fittings demand for SOM narrative
        material_usd = fittings_base

    labor_usd = max(0.0, sam_addressable - material_usd)
    # SOM splits proportional
    if sam_addressable > 0:
        mat_share = material_usd / sam_addressable
        lab_share = labor_usd / sam_addressable
    else:
        mat_share = plumbing_mat_share
        lab_share = 1 - mat_share

    fittings_sam = float(fittings_base) if fittings_base is not None else material_usd
    fittings_som = fittings_sam * SOM_SHARE
    som = {
        "share_pct": SOM_SHARE * 100,
        "sam_addressable_usd": sam_addressable,
        "som_usd": som_total,
        "material_usd": som_total * mat_share,
        "labor_usd": som_total * lab_share,
        "fittings_sam_usd": fittings_sam,
        "fittings_som_usd": fittings_som,
        "material_share_of_sam_pct": round(mat_share * 100, 2),
        "labor_share_of_sam_pct": round(lab_share * 100, 2),
        "assumptions_stated": {
            "plumbing_material_share_of_plumbing_base": plumbing_mat_share,
            "plumbing_share_of_new_construction_base": float(
                mat_cfg.get("res_new_plumbing", {})
                .get("plumbing_share_of_project_value", {})
                .get("base", 0.045)
            ),
            "fittings_share_of_material_base": float(
                mat_cfg.get("res_new_plumbing", {})
                .get("fittings_share_of_material", {})
                .get("base", 0.18)
            ),
            "pool_fittings_share_of_project_base": pool_fit_share,
            "irrigation_fittings_share_of_project_base": irrig_fit_share,
            "material_basis": "gold.fittings_base" if has_gold else "assumptions_chain_on_valuation",
        },
        "imputation": imputation,
        "imputation_method": (
            "Missing/≤0 declared_valuation filled with median of peer "
            "(category×county → county → category)."
        ),
        "formatted": {
            "sam_addressable": _fmt(sam_addressable),
            "som": _fmt(som_total),
            "material": _fmt(som_total * mat_share),
            "labor": _fmt(som_total * lab_share),
            "fittings_sam": _fmt(fittings_sam),
            "fittings_som": _fmt(fittings_som),
        },
    }

    # --- Q5 Near-term opportunity by county ---
    # Current month + next 1–3 months projected from seasonality
    cur_m = as_of.month
    cur_y = as_of.year
    near_term = []
    for county_row in top_counties[:12]:
        county = county_row["county"]
        series = [r for r in sam_county_monthly if r["county"] == county]
        by_ym = {(r["year"], r["month"]): r for r in series}
        current = by_ym.get((cur_y, cur_m), {"count": 0, "valuation": 0.0})
        horizon = []
        for ahead in range(0, 4):
            mm = cur_m + ahead
            yy = cur_y
            while mm > 12:
                mm -= 12
                yy += 1
            if ahead == 0 and (cur_y, cur_m) in by_ym:
                horizon.append(
                    {
                        "year": yy,
                        "month": mm,
                        "label": "current" if ahead == 0 else f"+{ahead}m",
                        "count": by_ym[(cur_y, cur_m)]["count"],
                        "valuation": by_ym[(cur_y, cur_m)]["valuation"],
                        "kind": "observed",
                    }
                )
            else:
                prior = by_ym.get((yy - 1, mm))
                # growth from last available same-offset
                g = 1.0
                last = by_ym.get((cur_y, cur_m)) or by_ym.get((cur_y, cur_m - 1))
                last_prior = None
                if last:
                    last_prior = by_ym.get((last["year"] - 1, last["month"]))
                if last and last_prior and last_prior["valuation"] > 0:
                    g = last["valuation"] / last_prior["valuation"]
                pred_v = (prior["valuation"] * g) if prior else (current.get("valuation", 0) or 0)
                pred_c = (prior["count"] * g) if prior else (current.get("count", 0) or 0)
                horizon.append(
                    {
                        "year": yy,
                        "month": mm,
                        "label": "current" if ahead == 0 else f"+{ahead}m",
                        "count": round(pred_c),
                        "valuation": pred_v,
                        "kind": "projected" if ahead or (cur_y, cur_m) not in by_ym else "observed",
                    }
                )
        near_term.append(
            {
                "county": county,
                "horizon": horizon,
                "pipeline_0_3m_valuation": sum(h["valuation"] for h in horizon),
            }
        )
    near_term.sort(key=lambda x: -x["pipeline_0_3m_valuation"])

    # --- Q6 Contractor activation ranking ---
    contractor_cov = con.execute(
        """
        SELECT
          COUNT(*) AS tom,
          COUNT(*) FILTER (WHERE contractor_name IS NOT NULL AND TRIM(contractor_name) <> '') AS with_name,
          COUNT(*) FILTER (WHERE is_sam AND contractor_name IS NOT NULL AND TRIM(contractor_name) <> '') AS sam_with_name,
          COUNT(*) FILTER (WHERE is_sam) AS sam
        FROM permits_v
        """
    ).fetchone()
    top_contractors = [
        {
            "contractor_name": r[0],
            "permits": int(r[1]),
            "valuation": float(r[2] or 0),
            "counties": r[3],
            "top_categories": r[4],
        }
        for r in con.execute(
            """
            SELECT
              UPPER(TRIM(contractor_name)) AS cname,
              COUNT(*) AS n,
              SUM(valuation_filled) AS v,
              STRING_AGG(DISTINCT county, ', ') AS counties,
              STRING_AGG(DISTINCT category, ', ') AS cats
            FROM permits_v
            WHERE is_sam
              AND contractor_name IS NOT NULL
              AND TRIM(contractor_name) <> ''
              AND UPPER(TRIM(contractor_name)) NOT IN ('OWNER', 'OWNER BUILDER', 'OWNER/BUILDER', 'N/A', 'NA', 'NONE', 'UNKNOWN')
              AND COALESCE(is_owner_builder, FALSE) = FALSE
            GROUP BY 1
            ORDER BY v DESC
            LIMIT 40
            """
        ).fetchall()
    ]
    # Coverage gaps by jurisdiction
    contractor_gaps = [
        {
            "jurisdiction_id": r[0],
            "sam": int(r[1]),
            "with_contractor": int(r[2]),
            "coverage_pct": float(r[3] or 0),
        }
        for r in con.execute(
            """
            SELECT jurisdiction_id,
                   COUNT(*) FILTER (WHERE is_sam),
                   COUNT(*) FILTER (WHERE is_sam AND contractor_name IS NOT NULL AND TRIM(contractor_name) <> ''),
                   100.0 * COUNT(*) FILTER (WHERE is_sam AND contractor_name IS NOT NULL AND TRIM(contractor_name) <> '')
                     / NULLIF(COUNT(*) FILTER (WHERE is_sam), 0)
            FROM permits_v
            GROUP BY 1
            ORDER BY 2 DESC
            """
        ).fetchall()
    ]

    # Jurisdiction coverage for notes
    by_jur = [
        {
            "jurisdiction_id": r[0],
            "tom": int(r[1]),
            "sam": int(r[2]),
            "valuation_sam": float(r[3] or 0),
        }
        for r in con.execute(
            """
            SELECT jurisdiction_id, COUNT(*),
                   COUNT(*) FILTER (WHERE is_sam),
                   SUM(valuation_filled) FILTER (WHERE is_sam)
            FROM permits_v
            GROUP BY 1 ORDER BY 2 DESC
            """
        ).fetchall()
    ]

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of.isoformat(),
        "definitions": {
            "TOM": "All permits issued ≥ 2021-01-01 in silver.permits",
            "SAM": "plumbing (new/repipe/remodel incl. new residential) + pool/spa + irrigation",
            "SOM": "5% market share of SAM addressable $ (valuation with peer median fill)",
            "valuation": "USD declared project value; missing filled with peer median",
            "outlier_cap_applied": bool(args.cap_outliers),
        },
        "universe": {
            "tom": int(meta[0]),
            "sam": int(meta[1]),
            "sam_share_pct": _pct(meta[1], meta[0]),
            "min_issued": str(meta[2]),
            "max_issued": str(meta[3]),
            "counties": int(meta[4]),
            "jurisdictions": int(meta[5]),
        },
        "q1_tom_yoy": {
            "annual": tom_yoy,
            "monthly": tom_monthly,
            "projection_2026_count": tom_proj_count,
            "projection_2026_valuation": tom_proj_val,
            "headline": {
                "latest_full_year": max((y for y in by_year if y < as_of.year), default=None),
                "yoy_count_pct": next(
                    (x["count_yoy_pct"] for x in reversed(tom_yoy) if x["count_yoy_pct"] is not None),
                    None,
                ),
                "yoy_valuation_pct": next(
                    (
                        x["valuation_yoy_pct"]
                        for x in reversed(tom_yoy)
                        if x["valuation_yoy_pct"] is not None
                    ),
                    None,
                ),
                "y2026_ytd_count": tom_proj_count["ytd"],
                "y2026_ytg_count": tom_proj_count["ytg_expected"],
                "y2026_full_year_count": tom_proj_count["full_year_expected"],
                "y2026_ytd_valuation": tom_proj_val["ytd"],
                "y2026_ytg_valuation": tom_proj_val["ytg_expected"],
                "y2026_full_year_valuation": tom_proj_val["full_year_expected"],
            },
        },
        "q2_segment_trends": {
            "annual": seg_annual,
            "monthly": seg_monthly,
        },
        "q3_sam": {
            "share": sam_share,
            "by_category": sam_by_cat,
            "top_counties": top_counties,
            "county_annual": sam_county_annual,
            "county_monthly": sam_county_monthly,
            "projection_2026_count": sam_proj_count,
            "projection_2026_valuation": sam_proj_val,
        },
        "q4_som": som,
        "q5_near_term": {
            "horizon_months": 4,
            "by_county": near_term,
        },
        "q6_contractors": {
            "coverage": {
                "tom": int(contractor_cov[0]),
                "tom_with_name": int(contractor_cov[1]),
                "tom_coverage_pct": _pct(contractor_cov[1], contractor_cov[0]),
                "sam": int(contractor_cov[3]),
                "sam_with_name": int(contractor_cov[2]),
                "sam_coverage_pct": _pct(contractor_cov[2], contractor_cov[3]),
            },
            "top": top_contractors,
            "gaps_by_jurisdiction": contractor_gaps,
            "notes": (
                "Owner-builder and blank/NA names excluded from ranking. "
                "Several jurisdictions lack contractor fields entirely — see gaps."
            ),
        },
        "jurisdictions": by_jur,
        "formatted_headlines": {
            "tom_count": f"{int(meta[0]):,}",
            "sam_count": f"{int(meta[1]):,}",
            "sam_share": f"{_pct(meta[1], meta[0])}%" if meta[0] else "n/a",
            "tom_valuation": _fmt(float(sam_usd[1] or 0)),
            "sam_valuation": _fmt(float(sam_usd[0] or 0)),
            "som": _fmt(som_total),
            "som_material": _fmt(som_total * mat_share),
            "som_labor": _fmt(som_total * lab_share),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {args.out} ({args.out.stat().st_size:,} bytes)")
    print(
        f"TOM={meta[0]:,} SAM={meta[1]:,} SAM$={_fmt(sam_addressable)} SOM={_fmt(som_total)}"
    )


if __name__ == "__main__":
    main()

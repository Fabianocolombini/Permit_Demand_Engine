#!/usr/bin/env python3
"""Apply material fittings model to SAM rows; write gold summary + docs report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.rules import SAM_CATEGORIES  # noqa: E402
from src.db import connect  # noqa: E402
from src.model.material import estimate_fittings_value  # noqa: E402
from src.registry import load_assumptions  # noqa: E402


def _fmt_usd(n: float) -> str:
    if abs(n) >= 1e9:
        return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"${n/1e6:.1f}M"
    if abs(n) >= 1e3:
        return f"${n/1e3:.1f}K"
    return f"${n:,.0f}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=ROOT / "permits.duckdb")
    p.add_argument("--gold-dir", type=Path, default=ROOT / "data" / "gold")
    p.add_argument("--docs-report", type=Path, default=None)
    args = p.parse_args()

    assumptions = load_assumptions()
    con = connect(args.db)
    # Ensure gold schema + material_estimates table
    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    con.execute("DROP TABLE IF EXISTS gold.material_estimates")
    con.execute(
        """
        CREATE TABLE gold.material_estimates (
            jurisdiction_id VARCHAR,
            permit_id VARCHAR,
            category VARCHAR,
            declared_valuation DOUBLE,
            fittings_low DOUBLE,
            fittings_base DOUBLE,
            fittings_high DOUBLE,
            PRIMARY KEY (jurisdiction_id, permit_id)
        )
        """
    )

    cats = sorted(SAM_CATEGORIES)
    placeholders = ",".join("?" * len(cats))
    rows = con.execute(
        f"""
        SELECT jurisdiction_id, permit_id, category, declared_valuation
        FROM silver.permits
        WHERE category IN ({placeholders})
        """,
        cats,
    ).fetchall()

    estimates = []
    for jid, pid, cat, val in rows:
        est = estimate_fittings_value(cat, val, assumptions)
        estimates.append(
            {
                "jurisdiction_id": jid,
                "permit_id": pid,
                "category": cat,
                "declared_valuation": val,
                "fittings_low": est.low,
                "fittings_base": est.base,
                "fittings_high": est.high,
            }
        )

    if estimates:
        import polars as pl

        df = pl.DataFrame(estimates)
        con.register("_mat", df.to_arrow())
        con.execute("INSERT INTO gold.material_estimates SELECT * FROM _mat")
        con.unregister("_mat")

    # Aggregations
    by_cat = con.execute(
        """
        SELECT category,
               COUNT(*) AS rows,
               SUM(CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 THEN 1 ELSE 0 END) AS with_val,
               SUM(COALESCE(declared_valuation, 0)) AS valuation_sum,
               SUM(fittings_low) AS fittings_low,
               SUM(fittings_base) AS fittings_base,
               SUM(fittings_high) AS fittings_high
        FROM gold.material_estimates
        GROUP BY 1
        ORDER BY fittings_base DESC
        """
    ).fetchall()
    by_jur = con.execute(
        """
        SELECT jurisdiction_id,
               COUNT(*) AS rows,
               SUM(fittings_low) AS fittings_low,
               SUM(fittings_base) AS fittings_base,
               SUM(fittings_high) AS fittings_high
        FROM gold.material_estimates
        GROUP BY 1
        ORDER BY fittings_base DESC
        """
    ).fetchall()
    totals = con.execute(
        """
        SELECT COUNT(*) AS rows,
               SUM(fittings_low), SUM(fittings_base), SUM(fittings_high),
               SUM(COALESCE(declared_valuation, 0))
        FROM gold.material_estimates
        """
    ).fetchone()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = {
        "generated_at": stamp,
        "sam_rows": int(totals[0] or 0),
        "fittings_low": float(totals[1] or 0),
        "fittings_base": float(totals[2] or 0),
        "fittings_high": float(totals[3] or 0),
        "declared_valuation_sum": float(totals[4] or 0),
        "by_category": [
            {
                "category": r[0],
                "rows": int(r[1]),
                "with_valuation": int(r[2]),
                "valuation_sum": float(r[3] or 0),
                "fittings_low": float(r[4] or 0),
                "fittings_base": float(r[5] or 0),
                "fittings_high": float(r[6] or 0),
            }
            for r in by_cat
        ],
        "by_jurisdiction": [
            {
                "jurisdiction_id": r[0],
                "rows": int(r[1]),
                "fittings_low": float(r[2] or 0),
                "fittings_base": float(r[3] or 0),
                "fittings_high": float(r[4] or 0),
            }
            for r in by_jur
        ],
        "assumptions_source": "config/assumptions.yaml → material_content",
    }

    args.gold_dir.mkdir(parents=True, exist_ok=True)
    gold_json = args.gold_dir / "fittings_summary.json"
    gold_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # CSV summary by category
    gold_csv = args.gold_dir / "fittings_by_category.csv"
    with gold_csv.open("w", encoding="utf-8") as fh:
        fh.write("category,rows,with_valuation,valuation_sum,fittings_low,fittings_base,fittings_high\n")
        for c in summary["by_category"]:
            fh.write(
                f"{c['category']},{c['rows']},{c['with_valuation']},{c['valuation_sum']:.2f},"
                f"{c['fittings_low']:.2f},{c['fittings_base']:.2f},{c['fittings_high']:.2f}\n"
            )

    lines = [
        "# Material fittings demand — SAM (low / base / high)",
        "",
        f"Generated: {stamp} from `gold.material_estimates` · assumptions in `config/assumptions.yaml`.",
        "",
        "## Units",
        "",
        "**USD fittings demand** estimated from declared project valuation (or fixed $/project for repipe), "
        "not declared construction value itself.",
        "",
        "- `res_new_plumbing`: valuation × plumbing_share × material_share × fittings_share",
        "- `res_repipe`: fixed `$320 / $450 / $640` per project",
        "- `irrigation` / `pool_spa`: valuation × fittings_share_of_project",
        "",
        f"**SAM rows modeled:** {summary['sam_rows']:,}",
        "",
        f"| Scenario | Fittings $ |",
        f"|---|---:|",
        f"| **low** | **{_fmt_usd(summary['fittings_low'])}** (`${summary['fittings_low']:,.0f}`) |",
        f"| **base** | **{_fmt_usd(summary['fittings_base'])}** (`${summary['fittings_base']:,.0f}`) |",
        f"| **high** | **{_fmt_usd(summary['fittings_high'])}** (`${summary['fittings_high']:,.0f}`) |",
        "",
        "## By SAM category",
        "",
        "| Category | Rows | Fittings low | Fittings base | Fittings high |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in summary["by_category"]:
        lines.append(
            f"| {c['category']} | {c['rows']:,} | {_fmt_usd(c['fittings_low'])} | "
            f"{_fmt_usd(c['fittings_base'])} | {_fmt_usd(c['fittings_high'])} |"
        )
    lines += [
        "",
        "## By jurisdiction",
        "",
        "| Jurisdiction | SAM rows | Fittings base |",
        "|---|---:|---:|",
    ]
    for j in summary["by_jurisdiction"]:
        lines.append(f"| {j['jurisdiction_id']} | {j['rows']:,} | {_fmt_usd(j['fittings_base'])} |")
    lines += [
        "",
        "## Caveats",
        "",
        "- Multiplicative assumptions (± bands) produce ~2× low–high span; confidence is **low** until calibrated with sell-out.",
        "- Rows with missing/≤0 valuation contribute $0 for share-of-valuation methods (repipe still counts fixed $).",
        "- Extreme Miami-Dade valuations inflate share-based fittings — same outlier caveat as declared-valuation reports.",
        "",
    ]

    gold_md = args.gold_dir / "fittings_summary.md"
    gold_md.write_text("\n".join(lines), encoding="utf-8")

    if args.docs_report:
        args.docs_report.parent.mkdir(parents=True, exist_ok=True)
        args.docs_report.write_text("\n".join(lines), encoding="utf-8")

    print(f"SAM rows={summary['sam_rows']:,}")
    print(
        f"fittings low={_fmt_usd(summary['fittings_low'])}  "
        f"base={_fmt_usd(summary['fittings_base'])}  "
        f"high={_fmt_usd(summary['fittings_high'])}"
    )
    print(f"→ {gold_json}")
    print(f"→ {gold_md}")
    if args.docs_report:
        print(f"→ {args.docs_report}")


if __name__ == "__main__":
    main()

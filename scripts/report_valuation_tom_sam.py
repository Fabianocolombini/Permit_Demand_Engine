#!/usr/bin/env python3
"""Recompute declared-valuation TOM/SAM report from silver.permits."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.rules import SAM_CATEGORIES  # noqa: E402
from src.db import connect  # noqa: E402


def _fmt_usd(n: float) -> str:
    if abs(n) >= 1e9:
        return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"${n/1e6:.1f}M"
    return f"${n:,.0f}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=ROOT / "permits.duckdb")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "reference" / "valuation_tom_sam.md")
    args = p.parse_args()

    con = connect(args.db)
    cats = sorted(SAM_CATEGORIES)
    ph = ",".join("?" * len(cats))

    overall = con.execute(
        f"""
        SELECT
          COUNT(*) AS tom,
          SUM(CASE WHEN category IN ({ph}) THEN 1 ELSE 0 END) AS sam,
          SUM(CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 THEN 1 ELSE 0 END) AS tom_decl,
          SUM(CASE WHEN category IN ({ph}) AND declared_valuation IS NOT NULL AND declared_valuation > 0 THEN 1 ELSE 0 END) AS sam_decl,
          SUM(CASE WHEN declared_valuation IS NULL THEN 1 ELSE 0 END) AS tom_null,
          SUM(CASE WHEN declared_valuation IS NOT NULL AND declared_valuation <= 0 THEN 1 ELSE 0 END) AS tom_zero,
          SUM(CASE WHEN category IN ({ph}) AND declared_valuation IS NULL THEN 1 ELSE 0 END) AS sam_null,
          SUM(CASE WHEN category IN ({ph}) AND declared_valuation IS NOT NULL AND declared_valuation <= 0 THEN 1 ELSE 0 END) AS sam_zero,
          SUM(CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 THEN declared_valuation ELSE 0 END) AS tom_usd,
          SUM(CASE WHEN category IN ({ph}) AND declared_valuation IS NOT NULL AND declared_valuation > 0 THEN declared_valuation ELSE 0 END) AS sam_usd
        FROM silver.permits
        """,
        cats * 5,
    ).fetchone()

    by_jur = con.execute(
        f"""
        SELECT jurisdiction_id,
          COUNT(*) AS tom,
          SUM(CASE WHEN category IN ({ph}) THEN 1 ELSE 0 END) AS sam,
          SUM(CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 THEN 1 ELSE 0 END) AS tom_decl,
          SUM(CASE WHEN category IN ({ph}) AND declared_valuation IS NOT NULL AND declared_valuation > 0 THEN 1 ELSE 0 END) AS sam_decl,
          SUM(CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 THEN declared_valuation ELSE 0 END) AS tom_usd,
          SUM(CASE WHEN category IN ({ph}) AND declared_valuation IS NOT NULL AND declared_valuation > 0 THEN declared_valuation ELSE 0 END) AS sam_usd
        FROM silver.permits
        GROUP BY 1
        ORDER BY tom_usd DESC
        """,
        cats * 3,
    ).fetchall()

    by_sam = con.execute(
        f"""
        SELECT category,
          COUNT(*) AS rows,
          SUM(CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 THEN 1 ELSE 0 END) AS decl,
          SUM(CASE WHEN declared_valuation IS NOT NULL AND declared_valuation > 0 THEN declared_valuation ELSE 0 END) AS usd
        FROM silver.permits
        WHERE category IN ({ph})
        GROUP BY 1
        ORDER BY usd DESC
        """,
        cats,
    ).fetchall()

    outliers = con.execute(
        f"""
        SELECT
          SUM(CASE WHEN declared_valuation >= 1e9 THEN 1 ELSE 0 END),
          SUM(CASE WHEN category IN ({ph}) AND declared_valuation >= 1e9 THEN 1 ELSE 0 END),
          SUM(CASE WHEN declared_valuation >= 1e9 THEN declared_valuation ELSE 0 END),
          SUM(CASE WHEN category IN ({ph}) AND declared_valuation >= 1e9 THEN declared_valuation ELSE 0 END)
        FROM silver.permits
        """,
        cats * 2,
    ).fetchone()

    tom, sam = int(overall[0]), int(overall[1])
    tom_decl, sam_decl = int(overall[2]), int(overall[3])
    tom_null, tom_zero = int(overall[4]), int(overall[5])
    sam_null, sam_zero = int(overall[6]), int(overall[7])
    tom_usd, sam_usd = float(overall[8] or 0), float(overall[9] or 0)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def pct(a, b):
        return round(100.0 * a / b, 2) if b else 0.0

    lines = [
        "# Declared project valuation — TOM / SAM",
        "",
        f"Generated: {stamp} from `{args.db}` (`silver.permits`).",
        "",
        "## Units",
        "",
        "**USD declared project value** (`declared_valuation`). "
        "This is the **permit's stated construction value**, not fittings demand.",
        "",
        "**Declared** = `declared_valuation IS NOT NULL AND declared_valuation > 0`.",
        "",
        "## % of permits that declare valuation",
        "",
        "| Universe | % declared | Declared rows | Missing (null/≤0) | Total rows |",
        "|---|---:|---:|---:|---:|",
        f"| **TOM** | **{pct(tom_decl, tom)}%** | {tom_decl:,} | {tom-tom_decl:,} (null {tom_null:,} · zero {tom_zero:,}) | {tom:,} |",
        f"| **SAM** | **{pct(sam_decl, sam)}%** | {sam_decl:,} | {sam-sam_decl:,} (null {sam_null:,} · zero {sam_zero:,}) | {sam:,} |",
        "",
        "### By jurisdiction",
        "",
        "| Jurisdiction | TOM % declared | SAM % declared | TOM declared/total | SAM declared/total |",
        "|---|---:|---:|---:|---:|",
    ]
    for jid, jtom, jsam, jtd, jsd, *_ in by_jur:
        sam_pct = f"{pct(jsd, jsam)}%" if jsam else "n/a%"
        lines.append(
            f"| {jid} | {pct(jtd, jtom)}% | {sam_pct} | {jtd:,}/{jtom:,} | {jsd:,}/{jsam:,} |"
        )
    lines += [
        f"| **TOTAL** | **{pct(tom_decl, tom)}%** | **{pct(sam_decl, sam)}%** | **{tom_decl:,}/{tom:,}** | **{sam_decl:,}/{sam:,}** |",
        "",
        "## Dollar sums (declared project value)",
        "",
        "| Metric | $ valuation | Rows | % declared |",
        "|---|---:|---:|---:|",
        f"| **TOM** | **{_fmt_usd(tom_usd)}** (`${tom_usd:,.0f}`) | {tom:,} | {pct(tom_decl, tom)}% |",
        f"| **SAM** | **{_fmt_usd(sam_usd)}** (`${sam_usd:,.0f}`) | {sam:,} | {pct(sam_decl, sam)}% |",
        f"| SAM / TOM | **{pct(sam_usd, tom_usd)}%** of $ · **{pct(sam, tom)}%** of rows | | |",
        "",
        "### Data-quality note (outliers)",
        "",
        f"**{int(outliers[0] or 0)}** TOM rows and **{int(outliers[1] or 0)}** SAM rows have valuation ≥ $1B "
        f"(${float(outliers[2] or 0):,.0f} / ${float(outliers[3] or 0):,.0f} of the sums above).",
        "",
        f"If those ≥$1B rows are excluded: TOM **{_fmt_usd(tom_usd - float(outliers[2] or 0))}** · "
        f"SAM **{_fmt_usd(sam_usd - float(outliers[3] or 0))}**.",
        "",
        "## By jurisdiction — $ and coverage",
        "",
        "| Jurisdiction | TOM $ | SAM $ | SAM/TOM $ % | TOM % declared | SAM % declared | TOM missing | SAM missing |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for jid, jtom, jsam, jtd, jsd, jtu, jsu in by_jur:
        jtu, jsu = float(jtu or 0), float(jsu or 0)
        sam_pct_d = f"{pct(jsd, jsam)}%" if jsam else "0%"
        lines.append(
            f"| {jid} | {_fmt_usd(jtu)} | {_fmt_usd(jsu)} | {pct(jsu, jtu) if jtu else 0.0} | "
            f"{pct(jtd, jtom)}% | {sam_pct_d} | {jtom-jtd:,} | {jsam-jsd:,} |"
        )
    lines += [
        f"| **TOTAL** | **{_fmt_usd(tom_usd)}** | **{_fmt_usd(sam_usd)}** | **{pct(sam_usd, tom_usd)}** | "
        f"**{pct(tom_decl, tom)}%** | **{pct(sam_decl, sam)}%** | **{tom-tom_decl:,}** | **{sam-sam_decl:,}** |",
        "",
        "## By SAM category",
        "",
        "| SAM category | $ valuation | Rows | % declared | Missing | % of SAM $ |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cat, nrows, decl, usd in by_sam:
        usd = float(usd or 0)
        lines.append(
            f"| {cat} | {_fmt_usd(usd)} (`${usd:,.0f}`) | {nrows:,} | {pct(decl, nrows)}% | "
            f"{nrows-decl:,} | {pct(usd, sam_usd)} |"
        )
    lines += [
        "",
        "## Definitions",
        "",
        "- **TOM** = all rows in `silver.permits`.",
        "- **SAM** = categories `res_new_plumbing`, `res_repipe`, `res_remodel_plumbing`, `pool_spa`, `irrigation`.",
        "- **% declared** = share with `declared_valuation` not null and > 0.",
        "- Valuation is **not** fittings demand; see material fittings report.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"TOM={tom:,} SAM={sam:,} TOM$={_fmt_usd(tom_usd)} SAM$={_fmt_usd(sam_usd)}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()

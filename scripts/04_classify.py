#!/usr/bin/env python3
"""Classify silver.permits and report TOM / SAM metrics.

TOM = total permits ingested (all rows).
SAM = Tigre/Dura subset: new/repipe/remodel plumbing + pool/spa + irrigation.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.rules import SAM_CATEGORIES, classify_text, is_sam  # noqa: E402
from src.db import connect  # noqa: E402
from src.registry import load_jurisdictions  # noqa: E402


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 2) if d else 0.0


def _jurisdictions_in_db(con) -> list[str]:
    rows = con.execute(
        "SELECT DISTINCT jurisdiction_id FROM silver.permits ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]


def classify_jurisdiction(con, jurisdiction_id: str) -> dict:
    rows = con.execute(
        """
        SELECT permit_id, permit_type_raw, work_class_raw, description_raw
        FROM silver.permits
        WHERE jurisdiction_id = ?
        """,
        [jurisdiction_id],
    ).fetchall()

    updates: list[dict] = []
    cat_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    sam_cat_counts: Counter[str] = Counter()
    unclassified_examples: Counter[str] = Counter()

    for permit_id, ptype, work, desc in rows:
        cat, method, conf = classify_text(ptype, work, desc)
        updates.append(
            {
                "permit_id": permit_id,
                "category": cat,
                "classification_method": method,
                "classification_confidence": float(conf),
            }
        )
        cat_counts[cat] += 1
        method_counts[method] += 1
        if is_sam(cat):
            sam_cat_counts[cat] += 1
        if method == "unclassified":
            key = " | ".join(
                x.strip()
                for x in (ptype or "", work or "", (desc or "")[:80])
                if x and str(x).strip()
            ) or "(empty)"
            unclassified_examples[key] += 1

    if updates:
        df = pl.DataFrame(updates)
        con.register("_cls", df.to_arrow())
        con.execute(
            """
            UPDATE silver.permits AS p
            SET
              category = c.category,
              classification_method = c.classification_method,
              classification_confidence = c.classification_confidence
            FROM _cls AS c
            WHERE p.jurisdiction_id = ?
              AND p.permit_id = c.permit_id
            """,
            [jurisdiction_id],
        )

    tom = len(rows)
    sam = sum(sam_cat_counts.values())
    excluded = sum(n for m, n in method_counts.items() if m.startswith("excluded_"))
    unclassified = method_counts.get("unclassified", 0)

    return {
        "jurisdiction_id": jurisdiction_id,
        "TOM": tom,
        "SAM": sam,
        "SAM_pct_of_TOM": _pct(sam, tom),
        "category_counts": dict(cat_counts.most_common()),
        "sam_category_counts": dict(sam_cat_counts.most_common()),
        "method_counts": dict(method_counts.most_common()),
        "excluded_noise_rows": excluded,
        "excluded_noise_pct": _pct(excluded, tom),
        "unclassified_rows": unclassified,
        "unclassified_pct": _pct(unclassified, tom),
        "top_unclassified": [
            {"text": t, "n": n} for t, n in unclassified_examples.most_common(25)
        ],
    }


def _print_tom_sam(rep: dict) -> None:
    print(
        f"  TOM={rep['TOM']:,}  SAM={rep['SAM']:,}  "
        f"SAM/TOM={rep['SAM_pct_of_TOM']}%  "
        f"excluded={rep['excluded_noise_pct']}%  unclassified={rep['unclassified_pct']}%"
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jurisdiction", action="append", dest="jurisdictions")
    p.add_argument("--all", action="store_true", help="Classify every jurisdiction in silver.permits")
    p.add_argument("--db", type=Path, default=ROOT / "permits.duckdb")
    p.add_argument(
        "--report",
        type=Path,
        default=ROOT / "data" / "reference" / "classification_report.json",
    )
    args = p.parse_args()

    con = connect(args.db)
    if args.all:
        targets = _jurisdictions_in_db(con)
    elif args.jurisdictions:
        targets = args.jurisdictions
    else:
        targets = ["fl_miami_dade_county"]

    if args.all:
        known = [
            j.id
            for j in load_jurisdictions()
            if str(j.tier).upper() == "A" and j.id in set(targets)
        ]
        rest = [t for t in targets if t not in known]
        targets = known + rest

    reports = []
    for jid in targets:
        print(f"\n=== classify {jid} ===", flush=True)
        rep = classify_jurisdiction(con, jid)
        reports.append(rep)
        _print_tom_sam(rep)
        for cat, n in list(rep["sam_category_counts"].items()):
            print(f"    SAM {cat}: {n:,}")
        for cat, n in list(rep["category_counts"].items())[:12]:
            if cat in SAM_CATEGORIES:
                continue
            print(f"    other {cat}: {n:,}")
        print("  top unclassified:")
        for item in rep["top_unclassified"][:8]:
            print(f"    {item['n']:>5}  {item['text'][:100]}")

    combined_cats: Counter[str] = Counter()
    combined_sam: Counter[str] = Counter()
    combined_methods: Counter[str] = Counter()
    combined_uncl: Counter[str] = Counter()
    tom = 0
    sam = 0
    for rep in reports:
        tom += rep["TOM"]
        sam += rep["SAM"]
        combined_cats.update(rep["category_counts"])
        combined_sam.update(rep["sam_category_counts"])
        combined_methods.update(rep["method_counts"])
        for item in rep["top_unclassified"]:
            combined_uncl[item["text"]] += item["n"]

    excluded = sum(n for m, n in combined_methods.items() if m.startswith("excluded_"))
    unclassified = combined_methods.get("unclassified", 0)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "definitions": {
            "TOM": "Total permits ingested (all rows; raw universe).",
            "SAM": (
                "Subset affecting Tigre USA / Dura: res_new_plumbing (incl. new "
                "residential construction / SFR/townhouse — implied plumbing rough-in), "
                "res_repipe, res_remodel_plumbing, pool_spa, irrigation. Excludes "
                "roof/windows/AC-only/fence/demo/electrical-only noise."
            ),
            "SAM_categories": sorted(SAM_CATEGORIES),
        },
        "jurisdictions": [r["jurisdiction_id"] for r in reports],
        "TOM": tom,
        "SAM": sam,
        "SAM_pct_of_TOM": _pct(sam, tom),
        "category_counts": dict(combined_cats.most_common()),
        "sam_category_counts": dict(combined_sam.most_common()),
        "method_counts": dict(combined_methods.most_common()),
        "excluded_noise_rows": excluded,
        "excluded_noise_pct": _pct(excluded, tom),
        "unclassified_rows": unclassified,
        "unclassified_pct": _pct(unclassified, tom),
        "top_unclassified": [
            {"text": t, "n": n} for t, n in combined_uncl.most_common(40)
        ],
        "by_jurisdiction": [
            {
                "jurisdiction_id": r["jurisdiction_id"],
                "TOM": r["TOM"],
                "SAM": r["SAM"],
                "SAM_pct_of_TOM": r["SAM_pct_of_TOM"],
                "sam_category_counts": r["sam_category_counts"],
                "unclassified_pct": r["unclassified_pct"],
            }
            for r in reports
        ],
        "by_jurisdiction_detail": reports,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_path = args.report.with_suffix(".md")
    lines = [
        "# Classification report — TOM / SAM (Tigre USA + Dura)",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "- **TOM** = total permits ingested (raw universe).",
        "- **SAM** = plumbing (new/repipe/remodel) **including new residential "
        "construction** (implied rough-in) + pool/spa + irrigation "
        "(excludes roof/windows/AC-only/fence noise).",
        "",
        f"**Overall:** TOM **{tom:,}** · SAM **{sam:,}** · SAM/TOM **{summary['SAM_pct_of_TOM']}%**  ·  "
        f"excluded noise {summary['excluded_noise_pct']}% · unclassified {summary['unclassified_pct']}%",
        "",
        "## TOM / SAM by jurisdiction",
        "",
        "| Jurisdiction | TOM | SAM | SAM/TOM % |",
        "|---|---:|---:|---:|",
    ]
    for r in reports:
        lines.append(
            f"| {r['jurisdiction_id']} | {r['TOM']:,} | {r['SAM']:,} | {r['SAM_pct_of_TOM']} |"
        )
    lines.append(f"| **TOTAL** | **{tom:,}** | **{sam:,}** | **{summary['SAM_pct_of_TOM']}** |")

    lines += [
        "",
        "## SAM category mix (overall)",
        "",
        "| SAM category | Rows | % of TOM | % of SAM |",
        "|---|---:|---:|---:|",
    ]
    for cat, n in combined_sam.most_common():
        lines.append(
            f"| {cat} | {n:,} | {_pct(n, tom)} | {_pct(n, sam)} |"
        )

    lines += [
        "",
        "## Full category mix (TOM)",
        "",
        "| Category | Rows | % of TOM | in SAM? |",
        "|---|---:|---:|:---:|",
    ]
    for cat, n in combined_cats.most_common():
        flag = "yes" if cat in SAM_CATEGORIES else ""
        lines.append(f"| {cat} | {n:,} | {_pct(n, tom)} | {flag} |")

    lines += ["", "## Top unclassified (text signatures)", "", "| n | Text |", "|---:|---|"]
    for item in summary["top_unclassified"][:25]:
        text = item["text"].replace("|", "\\|")
        lines.append(f"| {item['n']:,} | `{text[:120]}` |")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nSummary → {args.report}")
    print(f"Markdown → {md_path}")
    print(f"TOTAL TOM={tom:,}  SAM={sam:,}  SAM/TOM={summary['SAM_pct_of_TOM']}%")


if __name__ == "__main__":
    main()

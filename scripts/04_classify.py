#!/usr/bin/env python3
"""Classify stub — apply regex rules to silver.permits categories (in-place update)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.rules import classify_text  # noqa: E402
from src.db import connect  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jurisdiction", default="fl_miami_dade_county")
    p.add_argument("--db", type=Path, default=ROOT / "permits.duckdb")
    args = p.parse_args()

    con = connect(args.db)
    rows = con.execute(
        """
        SELECT permit_id, permit_type_raw, work_class_raw, description_raw
        FROM silver.permits
        WHERE jurisdiction_id = ?
        """,
        [args.jurisdiction],
    ).fetchall()

    updated = 0
    for permit_id, ptype, work, desc in rows:
        cat, method, conf = classify_text(ptype, work, desc)
        con.execute(
            """
            UPDATE silver.permits
            SET category = ?, classification_method = ?, classification_confidence = ?
            WHERE jurisdiction_id = ? AND permit_id = ?
            """,
            [cat, method, conf, args.jurisdiction, permit_id],
        )
        updated += 1

    dist = con.execute(
        """
        SELECT category, COUNT(*) AS n
        FROM silver.permits
        WHERE jurisdiction_id = ?
        GROUP BY 1 ORDER BY n DESC
        """,
        [args.jurisdiction],
    ).fetchall()
    print(f"Classified {updated} rows for {args.jurisdiction}")
    for cat, n in dist[:15]:
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Enrich geography: optional Census batch geocode for missing site ZIP (small sample).

Never uses ContractorZip. Writes coverage report under data/reference/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import connect  # noqa: E402
from src.enrich.geocode import (  # noqa: E402
    coverage_stats,
    enrich_missing_zip,
    write_coverage_report,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jurisdiction", default="fl_miami_dade_county")
    p.add_argument("--db", type=Path, default=ROOT / "permits.duckdb")
    p.add_argument(
        "--geocode-sample",
        type=int,
        default=100,
        help="Max rows missing ZIP to send to Census batch (0 to skip)",
    )
    p.add_argument("--no-geocode", action="store_true", help="Skip Census geocode entirely")
    args = p.parse_args()

    con = connect(args.db)
    cols = [
        "permit_id",
        "address_raw",
        "city",
        "state",
        "zip",
        "lat",
        "lon",
        "geocode_source",
        "geocode_confidence",
        "declared_valuation",
    ]
    cur = con.execute(
        f"SELECT {', '.join(cols)} FROM silver.permits WHERE jurisdiction_id = ?",
        [args.jurisdiction],
    )
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    before = coverage_stats(rows)
    print(
        f"Before enrich: n={before['n']} city={before['pct_city']:.1f}% "
        f"zip={before['pct_zip']:.1f}% valuation={before['pct_valuation']:.1f}%"
    )

    enabled = not args.no_geocode and args.geocode_sample > 0
    rows, meta = enrich_missing_zip(
        rows, max_sample=args.geocode_sample, enabled=enabled
    )

    # Persist updates for geocoded rows
    updated = 0
    for r in rows:
        if r.get("geocode_source") == "census_batch":
            con.execute(
                """
                UPDATE silver.permits
                SET zip = COALESCE(zip, ?),
                    lat = COALESCE(lat, ?),
                    lon = COALESCE(lon, ?),
                    geocode_source = ?,
                    geocode_confidence = ?
                WHERE jurisdiction_id = ? AND permit_id = ?
                """,
                [
                    r.get("zip"),
                    r.get("lat"),
                    r.get("lon"),
                    r.get("geocode_source"),
                    r.get("geocode_confidence"),
                    args.jurisdiction,
                    r["permit_id"],
                ],
            )
            updated += 1

    # Re-read for final stats
    cur = con.execute(
        f"SELECT {', '.join(cols)} FROM silver.permits WHERE jurisdiction_id = ?",
        [args.jurisdiction],
    )
    final_rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    after = coverage_stats(final_rows)

    report = ROOT / "data" / "reference" / f"coverage_{args.jurisdiction}.md"
    write_coverage_report(after, meta, report)

    print(
        f"After enrich:  n={after['n']} city={after['pct_city']:.1f}% "
        f"zip={after['pct_zip']:.1f}% valuation={after['pct_valuation']:.1f}% "
        f"(geocode updates={updated})"
    )
    print(f"Coverage report → {report}")


if __name__ == "__main__":
    main()

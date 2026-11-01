#!/usr/bin/env python3
"""Normalize staged JSONL → DuckDB silver.permits (Pydantic validated)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import connect  # noqa: E402
from src.normalize.mapper import map_row  # noqa: E402
from src.registry import get_jurisdiction, load_assumptions  # noqa: E402

PERMIT_COLUMNS = [
    "permit_id",
    "jurisdiction_id",
    "source_tier",
    "ingested_at",
    "applied_date",
    "issued_date",
    "final_date",
    "address_raw",
    "city",
    "county",
    "county_fips",
    "state",
    "zip",
    "lat",
    "lon",
    "geocode_confidence",
    "geocode_source",
    "permit_type_raw",
    "work_class_raw",
    "description_raw",
    "category",
    "classification_method",
    "classification_confidence",
    "is_new_construction",
    "is_residential",
    "declared_valuation",
    "square_feet",
    "units",
    "contractor_name",
    "contractor_license",
    "is_owner_builder",
    "project_key",
]


def _latest_staging(jurisdiction_id: str) -> Path:
    staging = ROOT / "data" / "bronze" / jurisdiction_id / "_staging"
    files = sorted(staging.glob("raw_*.jsonl"))
    if not files:
        raise FileNotFoundError(
            f"No staged JSONL in {staging}. Run scripts/02_ingest.py first."
        )
    return files[-1]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jurisdiction", default="fl_miami_dade_county")
    p.add_argument("--db", type=Path, default=ROOT / "permits.duckdb")
    p.add_argument("--staging", type=Path, default=None)
    p.add_argument(
        "--since",
        default=None,
        help="Override issued_date_min (YYYY-MM-DD). Default from jurisdiction/assumptions.",
    )
    p.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing rows for this jurisdiction first",
    )
    args = p.parse_args()

    j = get_jurisdiction(args.jurisdiction)
    assumptions = load_assumptions()
    since_s = (
        args.since
        or j.issued_date_min
        or assumptions.get("window", {}).get("issued_date_min")
    )
    issued_min = date.fromisoformat(since_s) if since_s else date(2021, 1, 1)

    staging_path = args.staging or _latest_staging(j.id)
    print(f"Normalizing {staging_path} (issued_date >= {issued_min})")

    ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    permits: list[dict] = []
    skipped = 0
    with staging_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            permit = map_row(raw, j, ingested_at=ingested_at, issued_date_min=issued_min)
            if permit is None:
                skipped += 1
                continue
            permits.append(permit.model_dump())

    by_key: dict[tuple[str, str], dict] = {}
    for row in permits:
        by_key[(row["jurisdiction_id"], row["permit_id"])] = row
    permits = list(by_key.values())

    con = connect(args.db)
    if args.replace:
        con.execute("DELETE FROM silver.permits WHERE jurisdiction_id = ?", [j.id])

    if permits:
        # Normalize Python types before Polars (mixed None/str/int breaks inference)
        for row in permits:
            if row.get("units") is not None:
                try:
                    row["units"] = int(row["units"])
                except (TypeError, ValueError):
                    row["units"] = None
            if row.get("zip") is not None:
                row["zip"] = str(row["zip"]).strip() or None
            for fcol in ("declared_valuation", "square_feet", "lat", "lon", "geocode_confidence"):
                if row.get(fcol) is not None:
                    try:
                        row[fcol] = float(row[fcol])
                    except (TypeError, ValueError):
                        row[fcol] = None

        df = pl.DataFrame(permits, infer_schema_length=len(permits))
        for col in PERMIT_COLUMNS:
            if col not in df.columns:
                df = df.with_columns(pl.lit(None).alias(col))
        df = df.select(PERMIT_COLUMNS)
        for dcol in ("applied_date", "issued_date", "final_date"):
            df = df.with_columns(pl.col(dcol).cast(pl.Date, strict=False))
        df = df.with_columns(pl.col("ingested_at").cast(pl.Datetime, strict=False))
        df = df.with_columns(pl.col("zip").cast(pl.Utf8, strict=False))

        con.register("_permits_in", df.to_arrow())
        if not args.replace:
            con.execute(
                """
                DELETE FROM silver.permits
                WHERE jurisdiction_id = ?
                  AND permit_id IN (SELECT permit_id FROM _permits_in)
                """,
                [j.id],
            )
        cols = ", ".join(PERMIT_COLUMNS)
        con.execute(
            f"INSERT INTO silver.permits ({cols}) SELECT {cols} FROM _permits_in"
        )

    stats = con.execute(
        """
        SELECT COUNT(*), MIN(issued_date), MAX(issued_date)
        FROM silver.permits WHERE jurisdiction_id = ?
        """,
        [j.id],
    ).fetchone()

    con.execute(
        """
        INSERT OR REPLACE INTO silver.jurisdictions
        (jurisdiction_id, name, county_fips, level, covers, tier, connector,
         last_pull_at, last_pull_status, records_total, earliest_permit, latest_permit, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            j.id,
            j.name,
            j.county_fips,
            j.level,
            j.covers,
            j.tier,
            "file",
            ingested_at,
            "ok",
            stats[0] if stats else 0,
            stats[1] if stats else None,
            stats[2] if stats else None,
            j.notes,
        ],
    )

    total = stats[0] if stats else 0
    n_val = con.execute(
        """
        SELECT COUNT(*) FROM silver.permits
        WHERE jurisdiction_id = ? AND declared_valuation IS NOT NULL
        """,
        [j.id],
    ).fetchone()[0]
    n_zip = con.execute(
        """
        SELECT COUNT(*) FROM silver.permits
        WHERE jurisdiction_id = ? AND zip IS NOT NULL AND zip <> ''
        """,
        [j.id],
    ).fetchone()[0]
    n_city = con.execute(
        """
        SELECT COUNT(*) FROM silver.permits
        WHERE jurisdiction_id = ? AND city IS NOT NULL AND city <> ''
        """,
        [j.id],
    ).fetchone()[0]

    print(
        f"Loaded {total} permits into silver.permits "
        f"(skipped={skipped}, unique_mapped={len(permits)})"
    )
    if total:
        print(
            f"  city={100 * n_city / total:.1f}%  "
            f"site_zip={100 * n_zip / total:.1f}%  "
            f"valuation={100 * n_val / total:.1f}%"
        )
    print(f"  DB: {args.db}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Bootstrap helper: export a manageable Miami-Dade sample from ArcGIS → CSV.

Primary ingest path remains file CSV/XLS under data/bronze/ or data/raw/.
This script only downloads a thin post-2021 sample so local pipelines can run.

Usage:
  python scripts/export_arcgis_sample.py
  python scripts/export_arcgis_sample.py --max-records 5000 --since 2024-01-01
  python scripts/export_arcgis_sample.py --since 2021-01-01 --max-records 50000  # larger pull

Full layer is ~487k rows (Hub table); prefer a dated window + max-records cap.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_ENDPOINT = (
    "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/"
    "miamidade_permit_data/FeatureServer"
)
DEFAULT_LAYER = 0
DEFAULT_OUT = ROOT / "data" / "bronze" / "fl_miami_dade_county" / "miami_dade_sample.csv"


def fetch_page(
    client: httpx.Client,
    endpoint: str,
    layer: int,
    where: str,
    offset: int,
    page_size: int,
    attempt: int = 0,
) -> dict:
    url = f"{endpoint}/{layer}/query"
    try:
        r = client.get(
            url,
            params={
                "where": where,
                "outFields": "*",
                "returnGeometry": "false",
                "resultOffset": offset,
                "resultRecordCount": page_size,
                "orderByFields": "ObjectId",
                "f": "json",
            },
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.TransportError):
        if attempt >= 4:
            raise
        time.sleep(2**attempt)
        return fetch_page(client, endpoint, layer, where, offset, page_size, attempt + 1)


def export_sample(
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    layer: int = DEFAULT_LAYER,
    since: str = "2021-01-01",
    until: str | None = None,
    max_records: int = 5000,
    page_size: int = 1000,
    out_path: Path = DEFAULT_OUT,
) -> tuple[int, Path]:
    where = f"PermitIssuedDate >= '{since}'"
    if until:
        where += f" AND PermitIssuedDate < '{until}'"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    fieldnames: list[str] | None = None

    with httpx.Client() as client, out_path.open("w", newline="", encoding="utf-8") as fh:
        writer: csv.DictWriter | None = None
        offset = 0
        while rows_written < max_records:
            payload = fetch_page(client, endpoint, layer, where, offset, page_size)
            if payload.get("error"):
                raise RuntimeError(f"ArcGIS error: {payload['error']}")
            features = payload.get("features") or []
            if not features:
                break
            for feat in features:
                attrs = feat.get("attributes") or {}
                if fieldnames is None:
                    fieldnames = list(attrs.keys())
                    writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                assert writer is not None
                writer.writerow(attrs)
                rows_written += 1
                if rows_written >= max_records:
                    break
            offset += len(features)
            # CRITICAL: trust exceededTransferLimit, not page length alone
            if not payload.get("exceededTransferLimit", False):
                break
            print(f"  … {rows_written} rows (offset={offset})")

    return rows_written, out_path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    p.add_argument("--layer", type=int, default=DEFAULT_LAYER)
    p.add_argument(
        "--since",
        default="2024-01-01",
        help="PermitIssuedDate lower bound (inclusive). Default favors recent demand; "
        "use 2021-01-01 for full post-pandemic bootstrap (large).",
    )
    p.add_argument("--until", default=None, help="PermitIssuedDate upper bound (exclusive)")
    p.add_argument("--max-records", type=int, default=5000, help="Cap rows for a manageable sample")
    p.add_argument("--page-size", type=int, default=1000)
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output CSV (default: data/bronze/fl_miami_dade_county/miami_dade_sample.csv)",
    )
    args = p.parse_args()

    print(f"Exporting Miami-Dade sample since={args.since} max={args.max_records}")
    print(f"  → {args.out}")
    n, path = export_sample(
        endpoint=args.endpoint,
        layer=args.layer,
        since=args.since,
        until=args.until,
        max_records=args.max_records,
        page_size=args.page_size,
        out_path=args.out,
    )
    print(f"Wrote {n} rows to {path}")
    print(
        "To pull more: raise --max-records or widen --since/--until. "
        "Full post-2021 pull is large (~hundreds of thousands); paginate with this script."
    )


if __name__ == "__main__":
    main()

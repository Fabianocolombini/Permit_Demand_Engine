#!/usr/bin/env python3
"""File-based ingest: CSV/XLS under data/bronze|raw → bronze parquet staging.

Live ArcGIS/Socrata connectors are deferred. Use export_arcgis_sample.py to
bootstrap a CSV first if needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest.file_csv import FileCSVConnector, discover_files  # noqa: E402
from src.registry import get_jurisdiction  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jurisdiction", default="fl_miami_dade_county")
    p.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Optional explicit CSV/XLS paths (else bronze/ then raw/)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Staging dir (default: data/bronze/<id>/_staging)",
    )
    args = p.parse_args()

    j = get_jurisdiction(args.jurisdiction)
    if j.connector and j.connector not in {"file", "csv", "xlsx"}:
        print(
            f"NOTE: jurisdiction connector={j.connector!r} but this script uses "
            "file ingest only. Live ArcGIS/Socrata comes later."
        )

    globs = []
    if j.bronze_glob:
        globs.append(j.bronze_glob)
    if j.raw_glob:
        globs.append(j.raw_glob)

    files = (
        [Path(f) for f in args.files]
        if args.files
        else discover_files(*globs, jurisdiction_id=j.id, root=ROOT)
    )
    # Ignore staging dirs / our own outputs
    files = [
        f
        for f in files
        if "_staging" not in f.parts and f.name != "normalized_preview.csv"
    ]
    if not files:
        raise SystemExit(
            f"No input CSV/XLS for {j.id}. Place files under data/bronze/{j.id}/ "
            f"or run: python scripts/export_arcgis_sample.py"
        )

    connector = FileCSVConnector(files=files, root=ROOT)
    out_dir = args.out_dir or (ROOT / "data" / "bronze" / j.id / "_staging")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Stream to JSONL for normalize (simple, schema-flexible)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"raw_{stamp}.jsonl"
    n = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for row in connector.fetch():
            fh.write(json.dumps(row, default=str) + "\n")
            n += 1

    manifest = {
        "jurisdiction_id": j.id,
        "connector": "file",
        "files": [str(f) for f in files],
        "rows": n,
        "staged": str(out_path),
        "ingested_at": stamp,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Staged {n} raw rows from {len(files)} file(s) → {out_path}")


if __name__ == "__main__":
    main()

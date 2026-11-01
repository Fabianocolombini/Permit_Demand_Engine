#!/usr/bin/env python3
"""Download Pinellas PCPAO RP_PERMITS CSV (ZIP) and filter issued >= since.

Respectful single POST to the public database-file endpoint used by the
pcpao.gov Downloads UI (jquery.database_files.js).

  python3 scripts/export_pcpao_pinellas.py --since 2021-01-01
"""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://www.pcpao.gov/dal/databasefile/downloadDatabaseFile"
UA = (
    "PermitDemandEngine/1.0 (+https://github.com/Fabianocolombini/Permit_Demand_Engine)"
)


def parse_issue(row: dict[str, str]) -> date | None:
    issue = (row.get("ISSUE_DT") or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(issue[:19], fmt).date()
        except ValueError:
            continue
    year_s = (row.get("PERMIT_YEAR") or "").strip()
    if year_s.isdigit():
        return date(int(year_s), 1, 1)
    return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", default="2021-01-01")
    p.add_argument("--preview-rows", type=int, default=100)
    args = p.parse_args()
    since = date.fromisoformat(args.since)

    bronze = ROOT / "data" / "bronze" / "fl_pinellas_county"
    bronze.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_csv = bronze / f"fl_pinellas_county_permits_{since.isoformat()}_{stamp}.csv"
    preview_csv = bronze / "sample_preview.csv"
    meta_path = bronze / "fl_pinellas_county_extract_meta.json"

    print("POST", ENDPOINT, "RP_PERMITS csv …", flush=True)
    with httpx.Client(timeout=600.0, follow_redirects=True, headers={"User-Agent": UA}) as client:
        resp = client.post(
            ENDPOINT,
            data={"hdn_tbl_name": "RP_PERMITS", "hdn_ftype": "csv"},
            headers={"Referer": "https://www.pcpao.gov/tools-data/data-downloads/raw-database-files"},
        )
        resp.raise_for_status()
        raw_zip = bronze / "RP_PERMITS_csv.zip"
        raw_zip.write_bytes(resp.content)
        print(f"  downloaded ZIP {len(resp.content)/1e6:.1f} MB → {raw_zip}", flush=True)

    total = kept = 0
    dmin = dmax = None
    preview: list[dict[str, str]] = []
    fieldnames: list[str] | None = None

    with zipfile.ZipFile(BytesIO(resp.content)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(name) as fh, out_csv.open("w", newline="", encoding="utf-8") as out:
            # TextIO wrapper for csv
            import io

            text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline="")
            reader = csv.DictReader(text)
            fieldnames = list(reader.fieldnames or [])
            writer = csv.DictWriter(out, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                total += 1
                dt = parse_issue(row)
                if dt is None or dt < since:
                    continue
                kept += 1
                if dmin is None or dt < dmin:
                    dmin = dt
                if dmax is None or dt > dmax:
                    dmax = dt
                writer.writerow(row)
                if len(preview) < args.preview_rows:
                    preview.append(row)
                if kept % 50000 == 0:
                    print(f"  … kept {kept:,} / scanned {total:,}", flush=True)

    if preview and fieldnames:
        with preview_csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(preview)

    meta = {
        "jurisdiction_id": "fl_pinellas_county",
        "connector": "file",
        "endpoint": ENDPOINT,
        "rows": kept,
        "rows_scanned": total,
        "date_field": "ISSUE_DT",
        "date_min": dmin.isoformat() if dmin else None,
        "date_max": dmax.isoformat() if dmax else None,
        "since": since.isoformat(),
        "csv_path": str(out_csv.resolve()),
        "bytes": out_csv.stat().st_size,
        "notes": "PCPAO RP_PERMITS bulk ZIP filtered to ISSUE_DT >= since",
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {kept:,} / {total:,} → {out_csv} ({out_csv.stat().st_size/1e6:.1f} MB)")
    print(f"date window {dmin} … {dmax}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Merge per-jurisdiction extract_meta.json + probe notes → extract_manifest.md."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "reference" / "extract_manifest.md",
    )
    args = p.parse_args()

    metas = []
    for path in sorted((ROOT / "data" / "bronze").glob("*/*_extract_meta.json")):
        metas.append(json.loads(path.read_text()))
    # Also pick up latest aggregate if present
    agg = ROOT / "data" / "reference" / "extract_manifest.json"
    if agg.exists():
        try:
            for row in json.loads(agg.read_text()):
                if row.get("jurisdiction_id") and not any(
                    m.get("jurisdiction_id") == row["jurisdiction_id"] for m in metas
                ):
                    metas.append(row)
        except json.JSONDecodeError:
            pass

    lines = [
        "# Permit extract manifest — Florida Onda 1",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Window: **issued ≥ 2021-01-01** (post-pandemic). Raw/full permits — no market classification filter.",
        "",
        "## Completed extracts (Tier A)",
        "",
        "| Jurisdiction | Covers | Rows | Date min | Date max | CSV path | Size | Notes |",
        "|---|---|---:|---|---|---|---:|---|",
    ]

    for m in sorted(metas, key=lambda x: x.get("jurisdiction_id") or ""):
        if m.get("error") and not m.get("rows"):
            continue
        size = m.get("bytes") or 0
        size_s = f"{size/1e6:.1f} MB" if size else ""
        notes = (m.get("notes") or "")[:160].replace("|", "/")
        lines.append(
            f"| {m.get('jurisdiction_id')} | {m.get('covers')} | {m.get('rows', 0):,} | "
            f"{m.get('date_min')} | {m.get('date_max')} | `{m.get('csv_path')}` | {size_s} | {notes} |"
        )

    lines.extend(
        [
            "",
            "## Endpoint reference",
            "",
            "| Jurisdiction | Connector | URL |",
            "|---|---|---|",
        ]
    )
    for m in sorted(metas, key=lambda x: x.get("jurisdiction_id") or ""):
        if m.get("endpoint"):
            url = m.get("endpoint")
            if (m.get("connector") or "").lower() != "socrata" and m.get("layer") is not None:
                url = f"{url}/{m.get('layer')}"
            lines.append(f"| {m.get('jurisdiction_id')} | {m.get('connector')} | {url} |")

    lines.extend(
        [
            "",
            "## Coverage caveats",
            "",
            "- **Miami-Dade Hub = unincorporated only.** City of Miami is a separate extract (`fl_miami_city`).",
            "- **Cape Coral / Manatee layers are Active permits**, not full historical archives.",
            "- **Broward HCED Posse** is a small geocoded subset (engineering-leaning), not full BCS building volume.",
            "- Orange County unincorporated, Duval/Jacksonville, Palm Beach building, Pinellas, Lee unincorporated,",
            "  Polk, Brevard, Volusia, Pasco, Osceola, Sarasota: **Tier B** (portal / no open record API found).",
            "",
            "## Preview CSVs",
            "",
            "Each bronze folder has `sample_preview.csv` (≤100 rows). A combined committed preview lives at",
            "`data/reference/sample_preview.csv` (Miami-Dade first 100).",
            "",
        ]
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} ({len(metas)} jurisdictions)")


if __name__ == "__main__":
    main()

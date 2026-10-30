#!/usr/bin/env python3
"""Probe ArcGIS / Socrata endpoints listed in jurisdictions.yaml or --url."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest.arcgis import ArcGISConnector  # noqa: E402
from src.ingest.socrata import SocrataConnector  # noqa: E402
from src.registry import load_jurisdictions_raw as load_jurisdictions  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jurisdiction", action="append", dest="jurisdictions")
    p.add_argument("--all", action="store_true")
    p.add_argument("--url", help="Ad-hoc ArcGIS service URL (FeatureServer/MapServer root)")
    p.add_argument("--layer", type=int, default=0)
    p.add_argument("--socrata", help="Ad-hoc Socrata resource URL")
    p.add_argument("--date-field", default=None)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    results = []

    if args.url:
        with ArcGISConnector(endpoint=args.url, layer=args.layer) as conn:
            meta = conn.probe()
            meta["endpoint"] = args.url
            meta["layer"] = args.layer
            if args.date_field:
                try:
                    from datetime import date

                    meta["count_since_2021"] = conn.count(since=date(2021, 1, 1), until=None)
                except Exception as exc:  # noqa: BLE001
                    meta["count_since_2021_error"] = str(exc)
            results.append(meta)

    if args.socrata:
        with SocrataConnector(endpoint=args.socrata, date_field=args.date_field or "issue_permit_date") as conn:
            results.append(conn.probe())

    registry = load_jurisdictions()
    targets = registry if args.all else []
    if args.jurisdictions:
        by_id = {j["id"]: j for j in registry}
        for jid in args.jurisdictions:
            targets.append(by_id[jid])

    for jur in targets:
        endpoint = jur.get("endpoint")
        if not endpoint:
            results.append({"jurisdiction_id": jur["id"], "error": "no endpoint"})
            continue
        connector = (jur.get("connector") or "").lower()
        try:
            if connector == "socrata":
                with SocrataConnector(
                    endpoint=endpoint,
                    date_field=jur.get("export_date_field")
                    or (jur.get("field_map") or {}).get("issued_date")
                    or "issue_permit_date",
                ) as conn:
                    meta = conn.probe()
            else:
                with ArcGISConnector(
                    endpoint=endpoint,
                    layer=int(jur.get("layer") or 0),
                    date_field=jur.get("export_date_field")
                    or (jur.get("field_map") or {}).get("issued_date")
                    or "PermitIssuedDate",
                    date_format=jur.get("arcgis_date_format") or "date_only",
                ) as conn:
                    meta = conn.probe()
                    from datetime import date

                    try:
                        meta["count_since_2021"] = conn.count(since=date(2021, 1, 1))
                    except Exception as exc:  # noqa: BLE001
                        meta["count_since_2021_error"] = str(exc)
            meta["jurisdiction_id"] = jur["id"]
            meta["endpoint"] = endpoint
            results.append(meta)
            print(f"OK {jur['id']}: total={meta.get('total_features')} since2021={meta.get('count_since_2021')} fields={len(meta.get('fields') or [])}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {jur['id']}: {exc}")
            results.append({"jurisdiction_id": jur["id"], "endpoint": endpoint, "error": str(exc)})

    text = json.dumps(results, indent=2, default=str)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()

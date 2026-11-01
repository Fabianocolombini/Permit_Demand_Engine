#!/usr/bin/env python3
"""Probe a curated list of Onda 1 Florida permit endpoint candidates.

Writes data/reference/onda1_probe_results.json with success/failure per candidate.
Does not scrape HTML portals aggressively — known Hub/FeatureServer/Socrata URLs only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest.arcgis import ArcGISConnector  # noqa: E402
from src.ingest.socrata import SocrataConnector  # noqa: E402

# Curated candidates — probe before promoting into jurisdictions.yaml
CANDIDATES: list[dict] = [
    {
        "id": "fl_miami_dade_county",
        "name": "Miami-Dade County (unincorporated)",
        "county": "Miami-Dade",
        "county_fips": "12086",
        "connector": "arcgis",
        "endpoint": "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/miamidade_permit_data/FeatureServer",
        "layer": 0,
        "date_field": "PermitIssuedDate",
        "date_format": "date_only",
        "covers_guess": "unincorporated_only",
    },
    {
        "id": "fl_broward_county",
        "name": "Broward County HCED Posse Permits",
        "county": "Broward",
        "county_fips": "12011",
        "connector": "arcgis",
        "endpoint": "https://bcgishub.broward.org/posse/rest/services/HCED/HCEDPossePermitsRef/FeatureServer",
        "layer": 4,
        "date_field": None,  # discover from fields
        "covers_guess": "unknown",
    },
    {
        "id": "fl_broward_building_permits_since_2014",
        "name": "Building_Permits_Since_2014 (AGOL)",
        "county": "Broward?",
        "county_fips": "12011",
        "connector": "arcgis",
        "endpoint": "https://services1.arcgis.com/CvuPhqcTQpZPT9qY/arcgis/rest/services/Building_Permits_Since_2014/FeatureServer",
        "layer": 0,
        "date_field": None,
        "covers_guess": "unknown",
    },
    {
        "id": "fl_hillsborough_county",
        "name": "Hillsborough / Planning Commission Building Permits",
        "county": "Hillsborough",
        "county_fips": "12057",
        "connector": "arcgis",
        "endpoint": "https://gis.tpcmaps.org/arcgis/rest/services/Websites/BuildingPermits/MapServer",
        "layer": 1,
        "date_field": "ISSUE_DATE",
        "date_format": "date_only",
        "covers_guess": "full_county",  # includes Tampa/Plant City/Temple Terrace labels
    },
    {
        "id": "fl_orlando_city",
        "name": "City of Orlando",
        "county": "Orange",
        "county_fips": "12095",
        "connector": "socrata",
        "endpoint": "https://data.cityoforlando.net/resource/ryhf-m453.json",
        "date_field": "issue_permit_date",
        "covers_guess": "city",
    },
    {
        "id": "fl_jacksonville_city",
        "name": "City of Jacksonville / Duval",
        "county": "Duval",
        "county_fips": "12031",
        "connector": "socrata",
        "endpoint": "https://data.coj.net/resource/7y2g-y4pd.json",  # candidate — may fail
        "date_field": None,
        "covers_guess": "city",
    },
    {
        "id": "fl_tampa_city",
        "name": "City of Tampa permits (Socrata candidate)",
        "county": "Hillsborough",
        "county_fips": "12057",
        "connector": "socrata",
        "endpoint": "https://data.tampagov.net/resource/xkb4-rr4z.json",  # candidate
        "date_field": None,
        "covers_guess": "city",
    },
    {
        "id": "fl_lee_county",
        "name": "Lee County building permits AGOL candidate",
        "county": "Lee",
        "county_fips": "12071",
        "connector": "arcgis",
        "endpoint": "https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/LeeCounty_BuildingPermits/FeatureServer",
        "layer": 0,
        "date_field": None,
        "covers_guess": "unknown",
    },
    {
        "id": "fl_pinellas_county",
        "name": "Pinellas open data permits candidate",
        "county": "Pinellas",
        "county_fips": "12103",
        "connector": "arcgis",
        "endpoint": "https://gis.pinellas.gov/arcgis/rest/services/OpenData/BuildingPermits/FeatureServer",
        "layer": 0,
        "date_field": None,
        "covers_guess": "unknown",
    },
    {
        "id": "fl_palm_beach_epermits",
        "name": "Palm Beach County ePermits (likely ROW — probe)",
        "county": "Palm Beach",
        "county_fips": "12099",
        "connector": "arcgis",
        "endpoint": "https://maps.co.palm-beach.fl.us/arcgis/rest/services/Ags/3/MapServer",
        "layer": 0,
        "date_field": "DT_ENT",
        "date_format": "epoch_ms",
        "covers_guess": "unknown",
    },
    {
        "id": "fl_sarasota_county",
        "name": "Sarasota County permits candidate",
        "county": "Sarasota",
        "county_fips": "12115",
        "connector": "arcgis",
        "endpoint": "https://sarasota.maps.arcgis.com",  # hub only — expect fail as FeatureServer
        "layer": 0,
        "date_field": None,
        "covers_guess": "unknown",
        "skip": True,
    },
    {
        "id": "fl_polk_county",
        "name": "Polk County AGOL permits candidate",
        "county": "Polk",
        "county_fips": "12105",
        "connector": "arcgis",
        "endpoint": "https://services1.arcgis.com/Y6TrTHx1pFtL1d56/arcgis/rest/services/Building_Permits/FeatureServer",
        "layer": 0,
        "date_field": None,
        "covers_guess": "unknown",
    },
    {
        "id": "fl_orange_county",
        "name": "Orange County FastTrack — no open API known",
        "county": "Orange",
        "county_fips": "12095",
        "connector": None,
        "endpoint": None,
        "covers_guess": "unincorporated_only",
        "tier_guess": "B",
        "skip": True,
        "notes": "Portal search only (fasttrack.ocfl.net) — Tier B",
    },
]


def guess_date_field(fields: list[dict]) -> str | None:
    names = [f.get("name") or "" for f in fields]
    lower = {n.lower(): n for n in names}
    for key in (
        "permitissueddate",
        "issuedate",
        "issue_date",
        "issued_date",
        "dateissued",
        "date_issued",
        "issued",
        "permit_issue_date",
        "issue_permit_date",
        "issueddate",
        "issudate",
        "cofo_date",
    ):
        if key in lower:
            return lower[key]
    for n in names:
        ln = n.lower()
        if "issue" in ln and "date" in ln:
            return n
    for n in names:
        if "date" in n.lower():
            return n
    return None


def probe_one(c: dict) -> dict:
    out = {**c, "status": "pending"}
    if c.get("skip") or not c.get("endpoint") or not c.get("connector"):
        out["status"] = "skipped"
        out["tier_guess"] = c.get("tier_guess") or "B"
        return out

    try:
        if c["connector"] == "arcgis":
            with ArcGISConnector(
                endpoint=c["endpoint"],
                layer=int(c.get("layer") or 0),
                date_field=c.get("date_field") or "OBJECTID",
                date_format=c.get("date_format") or "date_only",
            ) as conn:
                meta = conn.probe()
                fields = meta.get("fields") or []
                date_field = c.get("date_field") or guess_date_field(fields)
                out.update(
                    {
                        "status": "ok",
                        "tier_guess": "A",
                        "name_remote": meta.get("name"),
                        "total_features": meta.get("total_features"),
                        "max_record_count": meta.get("max_record_count"),
                        "geometry_type": meta.get("geometry_type"),
                        "field_names": [f["name"] for f in fields],
                        "date_field_resolved": date_field,
                    }
                )
                if date_field:
                    conn.date_field = date_field
                    # Try a few date formats
                    for fmt in (c.get("date_format"), "date_only", "sql_date", "epoch_ms"):
                        if not fmt:
                            continue
                        conn.date_format = fmt
                        try:
                            out["count_since_2021"] = conn.count(since=date(2021, 1, 1))
                            out["date_format_ok"] = fmt
                            break
                        except Exception as exc:  # noqa: BLE001
                            out.setdefault("date_format_errors", []).append(f"{fmt}: {exc}")
        elif c["connector"] == "socrata":
            with SocrataConnector(
                endpoint=c["endpoint"],
                date_field=c.get("date_field") or "issue_permit_date",
            ) as conn:
                meta = conn.probe()
                fields = meta.get("fields") or []
                date_field = c.get("date_field") or guess_date_field(fields) or c.get("date_field")
                if date_field:
                    conn.date_field = date_field
                out.update(
                    {
                        "status": "ok",
                        "tier_guess": "A",
                        "name_remote": meta.get("name"),
                        "total_features": meta.get("total_features"),
                        "field_names": [f.get("name") for f in fields],
                        "date_field_resolved": date_field,
                        "dataset_id": meta.get("dataset_id"),
                    }
                )
                try:
                    out["count_since_2021"] = conn.count(since=date(2021, 1, 1))
                except Exception as exc:  # noqa: BLE001
                    out["count_error"] = str(exc)
        else:
            out["status"] = "skipped"
            out["tier_guess"] = "B"
    except Exception as exc:  # noqa: BLE001
        out["status"] = "fail"
        out["tier_guess"] = "B"
        out["error"] = str(exc)[:500]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "reference" / "onda1_probe_results.json",
    )
    args = p.parse_args()

    results = []
    for c in CANDIDATES:
        print(f"Probing {c['id']} …", flush=True)
        r = probe_one(c)
        status = r.get("status")
        print(
            f"  → {status} total={r.get('total_features')} since2021={r.get('count_since_2021')} "
            f"date={r.get('date_field_resolved')} err={r.get('error', '')[:80]}",
            flush=True,
        )
        results.append(r)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

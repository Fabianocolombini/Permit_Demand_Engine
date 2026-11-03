#!/usr/bin/env python3
"""Build contractor project cards + mesoregion tags for the landing dashboard.

Reads pipeline window dates from metrics.json, queries silver.permits, writes:
  dashboard/public/data/contractor_details.json
and patches metrics.json pipeline.*.by_contractor with `mesoregions`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.rules import SAM_CATEGORIES  # noqa: E402
from src.db import connect  # noqa: E402
from src.registry import load_assumptions  # noqa: E402

SOM_SHARE = 0.05
METRICS = ROOT / "dashboard" / "public" / "data" / "metrics.json"
OUT = ROOT / "dashboard" / "public" / "data" / "contractor_details.json"

MIAMI_AREA_RE = re.compile(
    r"(MIAMI BEACH|CORAL GABLES|HIALEAH|HOMESTEAD|KENDALL|DORAL|CUTLER BAY|"
    r"NORTH MIAMI|AVENTURA|KEY BISCAYNE|MIAMI GARDENS|OPA[\s-]?LOCKA|SWEETWATER|"
    r"FLORIDA CITY|PINECREST|PALMETTO BAY|SUNNY ISLES|MIAMI LAKES|MEDLEY|"
    r"MIAMI SPRINGS|SOUTH MIAMI|WEST MIAMI|NORTH MIAMI BEACH)",
    re.I,
)

EXCLUDE = {
    "",
    "OWNER",
    "OWNER BUILDER",
    "OWNER/BUILDER",
    "N/A",
    "NA",
    "NONE",
    "UNKNOWN",
}


def _miami_area(address: str | None, city: str | None, jid: str) -> str:
    if jid == "fl_miami_city":
        return "City of Miami"
    blob = " ".join(filter(None, [address or "", city or ""]))
    m = MIAMI_AREA_RE.search(blob.upper())
    if m:
        return m.group(1).title().replace("Opa-Locka", "Opa Locka")
    if city and city.strip().upper() not in ("", "MIAMI", "FL"):
        return city.strip().title()
    return "Unincorporated / other Miami-Dade"


def _material(cat: str, valuation: float, assumptions: dict) -> float:
    cfg = assumptions.get("material_content", {})
    if cat in ("res_new_plumbing", "res_remodel_plumbing"):
        c = cfg.get(cat, cfg.get("res_new_plumbing", {}))
        pl = float(c.get("plumbing_share_of_project_value", {}).get("base", 0.045))
        ms = float(c.get("material_share_of_plumbing", {}).get("base", 0.35))
        return valuation * pl * ms
    if cat == "res_repipe":
        return float(cfg.get("res_repipe", {}).get("fittings_value_usd", {}).get("base", 450))
    if cat == "pool_spa":
        return valuation * float(
            cfg.get("pool_spa", {}).get("fittings_share_of_project", {}).get("base", 0.08)
        )
    if cat == "irrigation":
        return valuation * float(
            cfg.get("irrigation", {}).get("fittings_share_of_project", {}).get("base", 0.12)
        )
    return 0.0


def main() -> None:
    metrics = json.loads(METRICS.read_text())
    assumptions = load_assumptions()
    cats = sorted(SAM_CATEGORIES)
    ph = ", ".join(f"'{c}'" for c in cats)

    windows: dict[str, dict[str, str]] = {}
    for key in ("ytd", "d30", "d60"):
        w = metrics.get("pipeline", {}).get(key)
        if not w:
            continue
        windows[key] = {"start": w["start"], "end": w["end"], "label": w.get("label") or key}

    # Names we need detail for (union of top contractors across windows)
    names: set[str] = set()
    for key in windows:
        for c in metrics["pipeline"][key].get("by_contractor") or []:
            names.add(c["contractor_name"])

    con = connect()
    try:
        details: dict[str, Any] = {
            "as_of": metrics.get("as_of"),
            "note": (
                "Open permit feeds expose contractor_name + license when present; "
                "phone / website are not in bronze. Search links use name + license."
            ),
            "windows": {},
        }

        for wkey, wmeta in windows.items():
            start, end = wmeta["start"], wmeta["end"]
            rows = con.execute(
                f"""
                SELECT
                  UPPER(TRIM(contractor_name)) AS cname,
                  permit_id,
                  issued_date,
                  COALESCE(declared_valuation, 0) AS valuation,
                  city,
                  zip,
                  address_raw,
                  category,
                  description_raw,
                  contractor_license,
                  county,
                  jurisdiction_id,
                  project_key
                FROM silver.permits
                WHERE category IN ({ph})
                  AND issued_date > DATE '{start}'
                  AND issued_date <= DATE '{end}'
                  AND contractor_name IS NOT NULL
                  AND TRIM(contractor_name) <> ''
                  AND UPPER(TRIM(contractor_name)) NOT IN (
                    'OWNER','OWNER BUILDER','OWNER/BUILDER','N/A','NA','NONE','UNKNOWN'
                  )
                  AND COALESCE(is_owner_builder, FALSE) = FALSE
                ORDER BY valuation DESC
                """
            ).fetchall()

            by_name: dict[str, dict[str, Any]] = {}
            for (
                cname,
                pid,
                issued,
                val,
                city,
                zip_,
                addr,
                cat,
                descr,
                lic,
                county,
                jid,
                pkey,
            ) in rows:
                if cname in EXCLUDE:
                    continue
                meso = (
                    _miami_area(addr, city, jid or "")
                    if (county or "") == "Miami-Dade"
                    else None
                )
                mat = _material(str(cat), float(val or 0), assumptions)
                bucket = by_name.setdefault(
                    cname,
                    {
                        "contractor_name": cname,
                        "license": None,
                        "mesoregions": set(),
                        "counties": set(),
                        "projects": [],
                        "permits": 0,
                        "valuation": 0.0,
                        "material_usd": 0.0,
                    },
                )
                bucket["permits"] += 1
                bucket["valuation"] += float(val or 0)
                bucket["material_usd"] += mat
                if county:
                    bucket["counties"].add(county)
                if meso:
                    bucket["mesoregions"].add(meso)
                if lic and str(lic).strip() and not bucket["license"]:
                    bucket["license"] = str(lic).strip()
                # keep top projects by valuation (cap later)
                bucket["projects"].append(
                    {
                        "permit_id": str(pid),
                        "issued_date": issued.isoformat() if issued else None,
                        "valuation": float(val or 0),
                        "material_usd": mat,
                        "som_material_usd": mat * SOM_SHARE,
                        "city": city,
                        "zip": zip_,
                        "address": addr,
                        "category": cat,
                        "description": (descr or "")[:180] or None,
                        "county": county,
                        "mesoregion": meso,
                        "jurisdiction_id": jid,
                        "project_key": pkey,
                        "license": str(lic).strip() if lic and str(lic).strip() else None,
                    }
                )

            # Keep metrics top-40 PLUS top contractors per Miami mesoregion
            ranked = {
                c["contractor_name"]
                for c in metrics["pipeline"][wkey].get("by_contractor") or []
            }
            meso_rank: dict[str, list[tuple[str, float]]] = {}
            for cname, b in by_name.items():
                # valuation attributed per meso from that contractor's projects
                by_m: dict[str, float] = {}
                for p in b["projects"]:
                    if p.get("mesoregion"):
                        by_m[p["mesoregion"]] = by_m.get(p["mesoregion"], 0.0) + float(
                            p["valuation"]
                        )
                for area, v in by_m.items():
                    meso_rank.setdefault(area, []).append((cname, v))
            for area, lst in meso_rank.items():
                lst.sort(key=lambda x: -x[1])
                for cname, _ in lst[:15]:
                    ranked.add(cname)

            out_contractors: dict[str, Any] = {}
            for cname, b in by_name.items():
                if cname not in ranked:
                    continue
                projects = sorted(b["projects"], key=lambda p: -p["valuation"])[:25]
                out_contractors[cname] = {
                    "contractor_name": cname,
                    "license": b["license"],
                    "mesoregions": sorted(b["mesoregions"]),
                    "counties": sorted(b["counties"]),
                    "permits": int(b["permits"]),
                    "valuation": float(b["valuation"]),
                    "material_usd": float(b["material_usd"]),
                    "som_material_usd": float(b["material_usd"]) * SOM_SHARE,
                    "projects": projects,
                    "search_query": " ".join(
                        filter(None, [cname, b["license"] or "", "Florida contractor"])
                    ),
                }

            details["windows"][wkey] = {
                "label": wmeta["label"],
                "start": start,
                "end": end,
                "contractors": out_contractors,
            }

            # Patch metrics top contractors with mesoregions; append meso-only rows for UI lists
            existing = {
                c["contractor_name"]: c
                for c in metrics["pipeline"][wkey].get("by_contractor") or []
            }
            for c in existing.values():
                d = out_contractors.get(c["contractor_name"])
                c["mesoregions"] = d["mesoregions"] if d else []
                c["license"] = d.get("license") if d else None

            extras = []
            for cname, d in out_contractors.items():
                if cname in existing:
                    continue
                extras.append(
                    {
                        "contractor_name": cname,
                        "permits": d["permits"],
                        "valuation": d["valuation"],
                        "material_usd": d["material_usd"],
                        "som_material_usd": d["som_material_usd"],
                        "counties": ", ".join(d["counties"]),
                        "categories": ", ".join(
                            sorted({p["category"] for p in d["projects"] if p.get("category")})
                        ),
                        "mesoregions": d["mesoregions"],
                        "license": d.get("license"),
                        "meso_only": True,
                    }
                )
            metrics["pipeline"][wkey]["by_contractor"] = list(existing.values()) + sorted(
                extras, key=lambda x: -float(x["som_material_usd"])
            )

        OUT.write_text(json.dumps(details, separators=(",", ":")))
        METRICS.write_text(json.dumps(metrics, separators=(",", ":")))
        print(
            f"Wrote {OUT.relative_to(ROOT)} "
            f"({OUT.stat().st_size:,} bytes) and patched mesoregions on metrics contractors"
        )
        for wkey, w in details["windows"].items():
            print(f"  {wkey}: {len(w['contractors'])} contractors")
    finally:
        con.close()


if __name__ == "__main__":
    main()

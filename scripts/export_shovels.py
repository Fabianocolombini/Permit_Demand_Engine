#!/usr/bin/env python3
"""Export Florida Tier B (and backfill) permits via Shovels.ai API → data/bronze/.

Requires env secret ``SHOVELS_API_KEY`` (never printed or committed).

Examples:
  python3 scripts/export_shovels.py --check-key
  python3 scripts/export_shovels.py --resolve-only
  python3 scripts/export_shovels.py --tier-b --since 2021-01-01
  python3 scripts/export_shovels.py --jurisdiction fl_palm_beach_county --max-records 100
  python3 scripts/export_shovels.py --backfill-active-only
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest.shovels import (  # noqa: E402
    ENV_API_KEY,
    ShovelsAuthError,
    ShovelsConnector,
    ShovelsCreditLimitError,
    api_key_length,
    require_api_key,
)
from src.registry import load_jurisdictions_raw as load_jurisdictions  # noqa: E402

DEFAULT_SINCE = date(2021, 1, 1)

# Onda 1 Tier B gaps + Broward full + Cape Coral / Manatee historical backfill
TIER_B_IDS = [
    "fl_palm_beach_county",
    "fl_orange_county",
    "fl_duval_jacksonville",
    "fl_pinellas_county",
    "fl_lee_county",
    "fl_polk_county",
    "fl_brevard_county",
    "fl_volusia_county",
    "fl_pasco_county",
    "fl_osceola_county",
    "fl_sarasota_county",
    "fl_broward_full_building",
]

BACKFILL_IDS = [
    "fl_cape_coral_shovels",
    "fl_manatee_county_shovels",
]


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    return date.fromisoformat(s)


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return v


def write_csv(path: Path, rows: Iterator[dict[str, Any]], *, max_records: int | None = None) -> tuple[int, list[str]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] | None = None
    n = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer: csv.DictWriter | None = None
        for row in rows:
            flat = {k: _cell(v) for k, v in row.items()}
            if fieldnames is None:
                fieldnames = list(flat.keys())
                writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
            assert writer is not None
            extra = [k for k in flat if k not in fieldnames]
            if extra:
                fieldnames.extend(extra)
                writer.fieldnames = fieldnames
            writer.writerow(flat)
            n += 1
            if n % 500 == 0:
                print(f"  … {n} rows → {path.name}", flush=True)
            if max_records is not None and n >= max_records:
                break
    return n, fieldnames or []


def resolve_geo(conn: ShovelsConnector, jur: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return (geo_id, resolution meta)."""
    if jur.get("shovels_geo_id"):
        return str(jur["shovels_geo_id"]), {"source": "config", "geo_id": jur["shovels_geo_id"]}

    state = jur.get("state") or "FL"
    meta: dict[str, Any] = {"source": "search", "state": state}

    if jur.get("shovels_jurisdiction_q"):
        q = str(jur["shovels_jurisdiction_q"])
        hits = conn.search_jurisdictions(q, state=state)
        meta["q"] = q
        meta["kind"] = "jurisdiction"
        meta["hits"] = [{"geo_id": h.get("geo_id"), "name": h.get("name")} for h in hits[:5]]
        if not hits:
            raise RuntimeError(f"{jur['id']}: no jurisdiction match for {q!r}")
        from src.ingest.shovels import _best_geo_hit

        best = _best_geo_hit(hits, q)
        return str(best["geo_id"]), {**meta, "chosen": best}

    if jur.get("shovels_city_q"):
        q = str(jur["shovels_city_q"])
        hits = conn.search_cities(q, state=state)
        meta["q"] = q
        meta["kind"] = "city"
        meta["hits"] = [{"geo_id": h.get("geo_id"), "name": h.get("name")} for h in hits[:5]]
        if not hits:
            raise RuntimeError(f"{jur['id']}: no city match for {q!r}")
        from src.ingest.shovels import _best_geo_hit

        best = _best_geo_hit(hits, q)
        return str(best["geo_id"]), {**meta, "chosen": best}

    q = str(jur.get("shovels_county_q") or jur.get("county") or "")
    if not q:
        raise RuntimeError(f"{jur['id']}: need shovels_geo_id / shovels_county_q / city / jurisdiction")
    hits = conn.search_counties(q, state=state)
    meta["q"] = q
    meta["kind"] = "county"
    meta["hits"] = [{"geo_id": h.get("geo_id"), "name": h.get("name")} for h in hits[:5]]
    if not hits:
        raise RuntimeError(f"{jur['id']}: no county match for {q!r}")
    from src.ingest.shovels import _best_geo_hit

    best = _best_geo_hit(hits, q)
    return str(best["geo_id"]), {**meta, "chosen": best}


def export_one(
    conn: ShovelsConnector,
    jur: dict[str, Any],
    *,
    since: date,
    until: date,
    max_records: int | None,
    preview_rows: int,
    dry_run: bool,
) -> dict[str, Any]:
    jid = jur["id"]
    bronze = ROOT / "data" / "bronze" / jid
    bronze.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_csv = bronze / f"{jid}_shovels_permits_{since.isoformat()}_{stamp}.csv"
    preview_csv = bronze / "sample_preview.csv"

    print(f"\n=== {jid} ({jur.get('name')}) ===", flush=True)
    geo_id, reso = resolve_geo(conn, jur)
    print(f"  geo_id={geo_id} via {reso.get('kind') or reso.get('source')} q={reso.get('q')}", flush=True)
    if reso.get("chosen"):
        print(f"  matched={reso['chosen'].get('name')}", flush=True)

    count_info = None
    try:
        count_info = conn.count(geo_id, since, until)
        print(f"  total_count≈{count_info}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"  count skipped: {exc}", flush=True)

    result: dict[str, Any] = {
        "jurisdiction_id": jid,
        "name": jur.get("name"),
        "covers": jur.get("covers"),
        "tier": jur.get("tier"),
        "connector": "shovels",
        "shovels_geo_id": geo_id,
        "geo_resolution": reso,
        "total_count": count_info,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "credits": dict(conn.last_credits),
    }

    if dry_run:
        result["dry_run"] = True
        result["rows"] = 0
        side = bronze / f"{jid}_extract_meta.json"
        side.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    preview_buf: list[dict[str, Any]] = []

    def streaming() -> Iterator[dict[str, Any]]:
        for row in conn.fetch(
            since=since,
            until=until,
            geo_id=geo_id,
            max_records=max_records,
            flatten=True,
            require_issue_since=since,
        ):
            if len(preview_buf) < preview_rows:
                preview_buf.append(row)
            yield row

    try:
        n, cols = write_csv(out_csv, streaming(), max_records=max_records)
    except ShovelsCreditLimitError as exc:
        # Partial file may exist from prior pages written — recount if present
        n = 0
        cols = []
        if out_csv.exists():
            with out_csv.open(newline="", encoding="utf-8") as fh:
                n = max(0, sum(1 for _ in fh) - 1)
        result["error"] = f"credit_limit: {exc}"
        result["credit_limit"] = exc.limit
        result["upgrade_url"] = exc.upgrade_url
        result["stopped_reason"] = "credit_limit"
        print(f"  CREDIT LIMIT hit after ~{conn.rows_fetched} fetched / {n} on disk", flush=True)
    else:
        result["stopped_reason"] = conn.stopped_reason

    if preview_buf:
        write_csv(preview_csv, iter(preview_buf), max_records=preview_rows)

    dmin, dmax = _scan_dates(out_csv)
    size_b = out_csv.stat().st_size if out_csv.exists() else 0
    result.update(
        {
            "rows": n if "rows" not in result else result.get("rows", n),
            "date_min": dmin,
            "date_max": dmax,
            "csv_path": str(out_csv.resolve()) if out_csv.exists() else None,
            "preview_path": str(preview_csv.resolve()) if preview_csv.exists() else None,
            "bytes": size_b,
            "columns": len(cols),
            "credits_after": dict(conn.last_credits),
            "notes": (jur.get("notes") or "").strip().replace("\n", " "),
        }
    )
    if "rows" not in result or result["rows"] is None:
        result["rows"] = n
    # Prefer disk count when streaming completed
    if out_csv.exists() and result.get("stopped_reason") != "credit_limit":
        result["rows"] = n

    side = bronze / f"{jid}_extract_meta.json"
    side.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(
        f"  wrote {result.get('rows', 0):,} rows ({size_b/1e6:.2f} MB) "
        f"credits_remaining={conn.last_credits.get('remaining')} → {out_csv.name}",
        flush=True,
    )
    return result


def _scan_dates(csv_path: Path) -> tuple[str | None, str | None]:
    if not csv_path.exists():
        return None, None
    dmin = dmax = None
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        date_field = None
        for cand in ("issue_date", "issued_date", "start_date", "file_date"):
            if cand in fields:
                date_field = cand
                break
        if not date_field:
            return None, None
        for row in reader:
            v = (row.get(date_field) or "").strip()[:10]
            if not v:
                continue
            if dmin is None or v < dmin:
                dmin = v
            if dmax is None or v > dmax:
                dmax = v
    return dmin, dmax


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check-key", action="store_true", help="Print API key length only and exit")
    p.add_argument("--resolve-only", action="store_true", help="Resolve geo_ids + counts; no CSV pull")
    p.add_argument("--dry-run", action="store_true", help="Alias for --resolve-only")
    p.add_argument("--tier-b", action="store_true", help="Export configured Onda 1 Tier B gaps")
    p.add_argument("--backfill-active-only", action="store_true", help="Cape Coral + Manatee Shovels history")
    p.add_argument("--jurisdiction", action="append", dest="jurisdictions")
    p.add_argument("--since", default="2021-01-01")
    p.add_argument("--until", default=None, help="Exclusive upper bound (default: tomorrow UTC)")
    p.add_argument("--max-records", type=int, default=None, help="Per-jurisdiction hard cap")
    p.add_argument("--preview-rows", type=int, default=100)
    p.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "reference" / "shovels_extract_manifest.json",
    )
    args = p.parse_args()

    key_len = api_key_length()
    print(f"{ENV_API_KEY} length: {key_len}", flush=True)
    if args.check_key:
        if key_len == 0:
            raise SystemExit(1)
        raise SystemExit(0)

    try:
        require_api_key()
    except ShovelsAuthError as exc:
        print(str(exc), flush=True)
        raise SystemExit(2) from exc

    since = parse_date(args.since) or DEFAULT_SINCE
    until = parse_date(args.until) or (date.today() + timedelta(days=1))

    registry = load_jurisdictions()
    by_id = {j["id"]: j for j in registry}

    targets: list[dict[str, Any]] = []
    if args.tier_b:
        for jid in TIER_B_IDS:
            if jid not in by_id:
                print(f"WARN missing registry entry: {jid}", flush=True)
                continue
            targets.append(by_id[jid])
    if args.backfill_active_only:
        for jid in BACKFILL_IDS:
            if jid not in by_id:
                print(f"WARN missing registry entry: {jid}", flush=True)
                continue
            targets.append(by_id[jid])
    if args.jurisdictions:
        for jid in args.jurisdictions:
            if jid not in by_id:
                raise SystemExit(f"Unknown jurisdiction: {jid}")
            targets.append(by_id[jid])

    # de-dupe
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for j in targets:
        if j["id"] not in seen:
            seen.add(j["id"])
            uniq.append(j)
    targets = uniq

    if not targets:
        raise SystemExit("No jurisdictions selected. Use --tier-b, --backfill-active-only, or --jurisdiction.")

    dry = bool(args.resolve_only or args.dry_run)
    results: list[dict[str, Any]] = []
    usage_before = usage_after = None

    with ShovelsConnector() as conn:
        try:
            usage_before = conn.usage()
            print(f"usage before: {usage_before}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"usage probe failed: {exc}", flush=True)

        for jur in targets:
            try:
                results.append(
                    export_one(
                        conn,
                        jur,
                        since=since,
                        until=until,
                        max_records=args.max_records,
                        preview_rows=args.preview_rows,
                        dry_run=dry,
                    )
                )
            except ShovelsCreditLimitError as exc:
                results.append(
                    {
                        "jurisdiction_id": jur["id"],
                        "name": jur.get("name"),
                        "error": f"credit_limit: {exc}",
                        "credit_limit": exc.limit,
                        "upgrade_url": exc.upgrade_url,
                        "stopped_reason": "credit_limit",
                    }
                )
                print(f"STOP remaining jurisdictions — credit limit ({exc})", flush=True)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED {jur['id']}: {exc}", flush=True)
                results.append(
                    {
                        "jurisdiction_id": jur["id"],
                        "name": jur.get("name"),
                        "error": str(exc),
                    }
                )

        try:
            usage_after = conn.usage()
            print(f"usage after: {usage_after}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"usage after failed: {exc}", flush=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_key_length": key_len,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "usage_before": usage_before,
        "usage_after": usage_after,
        "results": results,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nManifest JSON → {args.manifest}", flush=True)

    # Human summary
    print("\n--- rows per jurisdiction ---", flush=True)
    for r in results:
        print(
            f"  {r.get('jurisdiction_id')}: rows={r.get('rows', '—')} "
            f"count={r.get('total_count')} err={r.get('error', '')}",
            flush=True,
        )


if __name__ == "__main__":
    main()

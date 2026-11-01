#!/usr/bin/env python3
"""Export full (or windowed) permit CSVs from ArcGIS / Socrata into data/bronze/.

Reads config/jurisdictions.yaml. Paginates with retry/backoff. Optionally slices
by calendar month when servers truncate large result sets.

Examples:
  python3 scripts/export_permits_csv.py --jurisdiction fl_miami_dade_county
  python3 scripts/export_permits_csv.py --jurisdiction fl_miami_dade_county --monthly
  python3 scripts/export_permits_csv.py --all-tier-a --since 2021-01-01
  python3 scripts/export_permits_csv.py --jurisdiction fl_orlando_city --preview-rows 100
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest.arcgis import ArcGISConnector  # noqa: E402
from src.ingest.socrata import SocrataConnector  # noqa: E402
from src.registry import load_jurisdictions_raw as load_jurisdictions  # noqa: E402


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    return date.fromisoformat(s)


def month_slices(since: date, until: date) -> list[tuple[date, date]]:
    """Half-open [start, end) monthly slices covering [since, until)."""
    out: list[tuple[date, date]] = []
    y, m = since.year, since.month
    cur = date(y, m, 1)
    if since.day != 1:
        # first partial month
        if m == 12:
            nxt = date(y + 1, 1, 1)
        else:
            nxt = date(y, m + 1, 1)
        end = min(nxt, until)
        out.append((since, end))
        cur = nxt
    while cur < until:
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
        end = min(nxt, until)
        out.append((cur, end))
        cur = nxt
    return out


def default_until() -> date:
    # exclusive upper bound: tomorrow UTC
    return date.today().replace(day=date.today().day) + __import__("datetime").timedelta(days=1)


def _resolve_date_format(jur: dict[str, Any]) -> str:
    if jur.get("arcgis_date_format"):
        return str(jur["arcgis_date_format"])
    if jur.get("date_format") == "epoch_ms":
        return "epoch_ms"
    if jur.get("date_format") == "sql_date":
        return "sql_date"
    return "date_only"


def iter_rows(
    jur: dict[str, Any],
    since: date,
    until: date,
    *,
    return_geometry: bool = False,
) -> Iterator[dict[str, Any]]:
    connector = (jur.get("connector") or "").lower()
    endpoint = jur.get("endpoint")
    if not endpoint:
        raise SystemExit(f"{jur['id']}: no endpoint")

    date_field = (
        jur.get("export_date_field")
        or (jur.get("field_map") or {}).get("issued_date")
        or "PermitIssuedDate"
    )
    date_format = _resolve_date_format(jur)
    export_where = jur.get("export_where")

    if connector in ("arcgis", "file", "arcgis_file"):
        # file jurisdictions still document an ArcGIS endpoint for export
        layer = int(jur.get("layer") or 0)
        extra_headers = jur.get("arcgis_headers") or None
        with ArcGISConnector(
            endpoint=endpoint,
            layer=layer,
            date_field=date_field,
            date_format=date_format,
            page_size=jur.get("page_size"),
            return_geometry=return_geometry or bool(jur.get("return_geometry")),
            order_by_fields=jur.get("order_by_fields"),
            endpoint_is_layer=bool(jur.get("endpoint_is_layer")),
            extra_headers=extra_headers,
        ) as conn:
            conn.probe()
            if export_where:
                # Bypass date builder — paginate a fixed WHERE
                offset = 0
                page_size = conn.effective_page_size()
                order = conn.order_by_fields or (conn._meta or {}).get("objectIdField")
                while True:
                    params: dict[str, Any] = {
                        "where": export_where,
                        "outFields": "*",
                        "returnGeometry": "true" if conn.return_geometry else "false",
                        "resultOffset": offset,
                        "resultRecordCount": page_size,
                        "f": "json",
                    }
                    if conn.return_geometry:
                        params["outSR"] = conn.out_sr
                    if order:
                        params["orderByFields"] = order
                    payload = conn._get_json(f"{conn.layer_url()}/query", params)
                    if payload.get("error"):
                        raise RuntimeError(f"ArcGIS error: {payload['error']}")
                    features = payload.get("features") or []
                    if not features:
                        break
                    for feat in features:
                        attrs = dict(feat.get("attributes") or {})
                        geom = feat.get("geometry")
                        if geom and conn.return_geometry and "x" in geom and "y" in geom:
                            attrs["_lon"] = geom.get("x")
                            attrs["_lat"] = geom.get("y")
                        yield attrs
                    offset += len(features)
                    if not payload.get("exceededTransferLimit", False) and len(features) < page_size:
                        break
                    if "exceededTransferLimit" in payload and not payload["exceededTransferLimit"]:
                        break
            else:
                yield from conn.fetch(since=since, until=until)
        return

    if connector == "socrata":
        with SocrataConnector(
            endpoint=endpoint,
            date_field=date_field,
            page_size=int(jur.get("page_size") or 5000),
        ) as conn:
            yield from conn.fetch(since=since, until=until)
        return

    raise SystemExit(f"{jur['id']}: unsupported connector={connector!r} for live export")


def write_csv(
    path: Path,
    rows: Iterator[dict[str, Any]],
    *,
    max_records: int | None = None,
) -> tuple[int, list[str]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] | None = None
    n = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer: csv.DictWriter | None = None
        for row in rows:
            # stringify nested values
            flat = {k: _cell(v) for k, v in row.items()}
            if fieldnames is None:
                fieldnames = list(flat.keys())
                writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
            assert writer is not None
            # evolve columns if new keys appear
            extra = [k for k in flat.keys() if k not in fieldnames]
            if extra:
                fieldnames.extend(extra)
                # rewrite is expensive; append empty for prior — DictWriter already set.
                # Simpler: ignore late columns via extrasaction, but we want them —
                # reopen with union is complex; collect extras into JSON blob instead.
                for k in extra:
                    flat[k] = flat.get(k)
                # Update writer fieldnames for subsequent rows (header already written)
                writer.fieldnames = fieldnames
            writer.writerow(flat)
            n += 1
            if n % 5000 == 0:
                print(f"  … {n} rows → {path.name}", flush=True)
            if max_records is not None and n >= max_records:
                break
    return n, fieldnames or []


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return v


def _compose_address(row: dict[str, Any]) -> dict[str, Any]:
    """Fill ADDRESS from house/street parts when split (Manatee PermitData)."""
    if row.get("ADDRESS"):
        return row
    parts: list[str] = []
    for key in ("HOUSE", "STREETDIR", "STREETNAME", "STREETSUFFIX", "UNITNUM"):
        val = row.get(key)
        if val is None:
            continue
        s = str(val).strip()
        if not s or s.upper() in {"NA", "N/A", "NONE", "NULL"}:
            continue
        parts.append(s)
    if parts:
        out = dict(row)
        out["ADDRESS"] = " ".join(parts)
        return out
    return row


def export_jurisdiction(
    jur: dict[str, Any],
    *,
    since: date,
    until: date,
    monthly: bool,
    max_records: int | None,
    preview_rows: int,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    jid = jur["id"]
    bronze = out_dir or (ROOT / "data" / "bronze" / jid)
    bronze.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_csv = bronze / f"{jid}_permits_{since.isoformat()}_{stamp}.csv"
    preview_csv = bronze / "sample_preview.csv"

    print(f"\n=== {jid} ({jur.get('name')}) ===")
    print(f"  connector={jur.get('connector')} endpoint={jur.get('endpoint')}")
    print(f"  window=[{since}, {until}) monthly={monthly}")

    # Optional pre-count
    expected = None
    try:
        expected = _count(jur, since, until)
        if expected is not None:
            print(f"  server count (window) ≈ {expected:,}")
    except Exception as exc:  # noqa: BLE001
        print(f"  count skipped: {exc}")

    # Stream to disk without holding all in memory — keep a small preview buffer
    preview_buf: list[dict[str, Any]] = []
    date_field = (
        jur.get("export_date_field")
        or (jur.get("field_map") or {}).get("issued_date")
        or "PermitIssuedDate"
    )

    def streaming() -> Iterator[dict[str, Any]]:
        nonlocal preview_buf
        # export_where is a full-window filter — never monthly-slice it (would re-pull N times)
        use_monthly = monthly and not jur.get("export_where")
        if use_monthly:
            for a, b in month_slices(since, until):
                print(f"  slice {a} → {b}", flush=True)
                for row in iter_rows(jur, a, b):
                    row = _compose_address(row)
                    if len(preview_buf) < preview_rows:
                        preview_buf.append(row)
                    yield row
        else:
            for row in iter_rows(jur, since, until):
                row = _compose_address(row)
                if len(preview_buf) < preview_rows:
                    preview_buf.append(row)
                yield row

    n, cols = write_csv(out_csv, streaming(), max_records=max_records)

    # Write preview
    if preview_buf:
        write_csv(preview_csv, iter(preview_buf), max_records=preview_rows)

    # Scan date min/max from file (streaming second pass on issued field)
    dmin, dmax = _scan_dates(out_csv, date_field)

    size_b = out_csv.stat().st_size if out_csv.exists() else 0
    result = {
        "jurisdiction_id": jid,
        "name": jur.get("name"),
        "covers": jur.get("covers"),
        "tier": jur.get("tier"),
        "connector": jur.get("connector"),
        "endpoint": jur.get("endpoint"),
        "layer": jur.get("layer"),
        "rows": n,
        "expected_count": expected,
        "date_field": date_field,
        "date_min": dmin,
        "date_max": dmax,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "csv_path": str(out_csv.resolve()),
        "preview_path": str(preview_csv.resolve()) if preview_csv.exists() else None,
        "bytes": size_b,
        "columns": len(cols),
        "notes": (jur.get("notes") or "").strip().replace("\n", " "),
    }
    # Sidecar manifest JSON per jurisdiction
    side = bronze / f"{jid}_extract_meta.json"
    side.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"  wrote {n:,} rows ({size_b/1e6:.1f} MB) → {out_csv}")
    return result


def _count(jur: dict[str, Any], since: date, until: date) -> int | None:
    connector = (jur.get("connector") or "").lower()
    endpoint = jur.get("endpoint")
    date_field = (
        jur.get("export_date_field")
        or (jur.get("field_map") or {}).get("issued_date")
        or "PermitIssuedDate"
    )
    if connector in ("arcgis", "file", "arcgis_file"):
        date_format = _resolve_date_format(jur)
        with ArcGISConnector(
            endpoint=endpoint,
            layer=int(jur.get("layer") or 0),
            date_field=date_field,
            date_format=date_format,
            endpoint_is_layer=bool(jur.get("endpoint_is_layer")),
            extra_headers=jur.get("arcgis_headers") or None,
        ) as conn:
            if jur.get("export_where"):
                payload = conn._get_json(
                    f"{conn.layer_url()}/query",
                    {"where": jur["export_where"], "returnCountOnly": "true", "f": "json"},
                )
                if payload.get("error"):
                    raise RuntimeError(f"ArcGIS error: {payload['error']}")
                return payload.get("count")
            return conn.count(since=since, until=until)
    if connector == "socrata":
        with SocrataConnector(endpoint=endpoint, date_field=date_field) as conn:
            return conn.count(since=since, until=until)
    return None


def _scan_dates(csv_path: Path, date_field: str) -> tuple[str | None, str | None]:
    if not csv_path.exists() or not date_field:
        return None, None
    dmin = dmax = None
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if date_field not in (reader.fieldnames or []):
            # try common alternates
            for alt in ("PermitIssuedDate", "ISSUE_DATE", "issue_permit_date", "issued_date"):
                if alt in (reader.fieldnames or []):
                    date_field = alt
                    break
            else:
                return None, None
        for row in reader:
            v = (row.get(date_field) or "").strip()
            if not v:
                continue
            # Normalize epoch ms to ISO date for stats
            if v.isdigit() and len(v) >= 12:
                try:
                    v = datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc).date().isoformat()
                except (OverflowError, ValueError, OSError):
                    pass
            else:
                v = v[:10]
            if dmin is None or v < dmin:
                dmin = v
            if dmax is None or v > dmax:
                dmax = v
    return dmin, dmax


def main() -> None:
    from datetime import timedelta

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--jurisdiction", action="append", dest="jurisdictions", help="Jurisdiction id (repeatable)")
    p.add_argument("--all-tier-a", action="store_true", help="Export every Tier A with an endpoint")
    p.add_argument("--since", default="2021-01-01")
    p.add_argument("--until", default=None, help="Exclusive upper bound (default: tomorrow UTC)")
    p.add_argument("--monthly", action="store_true", help="Slice queries by calendar month")
    p.add_argument("--max-records", type=int, default=None, help="Optional hard cap (tests)")
    p.add_argument("--preview-rows", type=int, default=100)
    p.add_argument("--manifest", type=Path, default=ROOT / "data" / "reference" / "extract_manifest.json")
    args = p.parse_args()

    since = parse_date(args.since)
    assert since is not None
    until = parse_date(args.until) or (date.today() + timedelta(days=1))

    registry = load_jurisdictions()
    by_id = {j["id"]: j for j in registry}

    targets: list[dict[str, Any]] = []
    if args.all_tier_a:
        targets = [
            j
            for j in registry
            if str(j.get("tier", "")).upper() == "A"
            and j.get("endpoint")
            and (j.get("connector") or "").lower() in ("arcgis", "socrata", "file", "arcgis_file")
        ]
    if args.jurisdictions:
        for jid in args.jurisdictions:
            if jid not in by_id:
                raise SystemExit(f"Unknown jurisdiction: {jid}")
            targets.append(by_id[jid])

    # de-dupe preserving order
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for j in targets:
        if j["id"] not in seen:
            seen.add(j["id"])
            uniq.append(j)
    targets = uniq

    if not targets:
        raise SystemExit("No jurisdictions selected. Use --jurisdiction or --all-tier-a.")

    results = []
    for jur in targets:
        try:
            results.append(
                export_jurisdiction(
                    jur,
                    since=since,
                    until=until,
                    monthly=args.monthly or bool(jur.get("export_monthly")),
                    max_records=args.max_records,
                    preview_rows=args.preview_rows,
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {jur['id']}: {exc}", flush=True)
            results.append(
                {
                    "jurisdiction_id": jur["id"],
                    "name": jur.get("name"),
                    "error": str(exc),
                    "endpoint": jur.get("endpoint"),
                }
            )

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nManifest JSON → {args.manifest}")


if __name__ == "__main__":
    main()

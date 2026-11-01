#!/usr/bin/env python3
"""Ingest → normalize → classify every jurisdiction that has a full bronze CSV.

Unlike run_tier_a_pipeline.py, includes Tier B open fills (Cape history, FTL,
Pinellas, Lakeland, etc.) so TOM/SAM can be recomputed on the combined universe.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.registry import load_jurisdictions  # noqa: E402


def has_bronze(jid: str) -> bool:
    d = ROOT / "data" / "bronze" / jid
    if not d.exists():
        return False
    for p in d.glob("*.csv"):
        if p.name == "sample_preview.csv":
            continue
        if p.stat().st_size > 0:
            return True
    return False


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--skip-ingest", action="store_true")
    p.add_argument("--skip-normalize", action="store_true")
    p.add_argument("--skip-classify", action="store_true")
    p.add_argument("--tier", action="append", dest="tiers", help="Filter A/B (repeatable)")
    p.add_argument("--jurisdiction", action="append", dest="jurisdictions")
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Skip jurisdiction id (e.g. fl_cape_coral_city when history preferred)",
    )
    args = p.parse_args()

    registry = load_jurisdictions()
    if args.jurisdictions:
        targets = args.jurisdictions
    else:
        tiers = {t.upper() for t in (args.tiers or ["A", "B"])}
        targets = [
            j.id
            for j in registry
            if str(j.tier).upper() in tiers
            and has_bronze(j.id)
            and j.id not in set(args.exclude or [])
            and (j.connector or "").lower() != "shovels"  # never paid path this turn
        ]

    if not targets:
        raise SystemExit("No bronze CSVs found for selected jurisdictions")

    py = sys.executable
    print(f"Pipeline targets ({len(targets)}): {', '.join(targets)}", flush=True)
    for jid in targets:
        print(f"\n######## {jid} ########", flush=True)
        if not args.skip_ingest:
            subprocess.check_call([py, str(ROOT / "scripts" / "02_ingest.py"), "--jurisdiction", jid])
        if not args.skip_normalize:
            subprocess.check_call(
                [py, str(ROOT / "scripts" / "03_normalize.py"), "--jurisdiction", jid, "--replace"]
            )

    if not args.skip_classify:
        subprocess.check_call([py, str(ROOT / "scripts" / "04_classify.py"), "--all"])


if __name__ == "__main__":
    main()

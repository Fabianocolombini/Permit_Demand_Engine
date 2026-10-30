#!/usr/bin/env python3
"""Ingest → normalize → classify for every Tier A bronze CSV on disk."""

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
    p.add_argument("--jurisdiction", action="append", dest="jurisdictions")
    args = p.parse_args()

    if args.jurisdictions:
        targets = args.jurisdictions
    else:
        targets = [
            j.id
            for j in load_jurisdictions()
            if str(j.tier).upper() == "A" and has_bronze(j.id)
        ]

    if not targets:
        raise SystemExit("No Tier A bronze CSVs found under data/bronze/")

    py = sys.executable
    for jid in targets:
        print(f"\n######## {jid} ########", flush=True)
        if not args.skip_ingest:
            subprocess.check_call([py, str(ROOT / "scripts" / "02_ingest.py"), "--jurisdiction", jid])
        if not args.skip_normalize:
            subprocess.check_call(
                [py, str(ROOT / "scripts" / "03_normalize.py"), "--jurisdiction", jid, "--replace"]
            )

    if not args.skip_classify:
        cmd = [py, str(ROOT / "scripts" / "04_classify.py"), "--all"]
        subprocess.check_call(cmd)


if __name__ == "__main__":
    main()

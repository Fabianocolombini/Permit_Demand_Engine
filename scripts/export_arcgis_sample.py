#!/usr/bin/env python3
"""Backward-compatible thin wrapper around export_permits_csv.py.

Prefer:
  python3 scripts/export_permits_csv.py --jurisdiction fl_miami_dade_county --monthly

This wrapper keeps the old CLI for a capped Miami-Dade sample.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", default="2024-01-01")
    p.add_argument("--until", default=None)
    p.add_argument("--max-records", type=int, default=5000)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "bronze" / "fl_miami_dade_county" / "miami_dade_sample.csv",
    )
    p.add_argument("--jurisdiction", default="fl_miami_dade_county")
    p.add_argument("--monthly", action="store_true")
    args = p.parse_args()

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "export_permits_csv.py"),
        "--jurisdiction",
        args.jurisdiction,
        "--since",
        args.since,
        "--max-records",
        str(args.max_records),
        "--preview-rows",
        "100",
    ]
    if args.until:
        cmd.extend(["--until", args.until])
    if args.monthly:
        cmd.append("--monthly")
    print("Delegating to export_permits_csv.py:", " ".join(cmd))
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()

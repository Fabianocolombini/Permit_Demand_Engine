"""CSV / XLS(X) file connector — primary ingest path for this slice.

Reads local files under data/bronze/<jurisdiction_id>/ (preferred) or
data/raw/<jurisdiction_id>/. Live ArcGIS/Socrata connectors are deferred.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Iterator

import polars as pl

from src.ingest.base import Connector

SUPPORTED_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls"}


def discover_files(
    *globs_or_dirs: str | Path,
    jurisdiction_id: str | None = None,
    root: Path | None = None,
) -> list[Path]:
    """Find CSV/XLS files for a jurisdiction.

    Search order when jurisdiction_id is set and no explicit paths given:
      1. data/bronze/<id>/
      2. data/raw/<id>/
    """
    root = root or Path.cwd()
    found: list[Path] = []

    explicit = [Path(p) for p in globs_or_dirs if p]
    if explicit:
        for p in explicit:
            path = p if p.is_absolute() else root / p
            if path.is_dir():
                for suf in SUPPORTED_SUFFIXES:
                    found.extend(sorted(path.glob(f"*{suf}")))
            elif "*" in path.name or "?" in path.name or "{" in path.name:
                # simple glob from parent
                parent = path.parent
                pattern = path.name
                # brace expand {csv,xlsx,xls}
                if "{" in pattern and "}" in pattern:
                    import re

                    m = re.search(r"\{([^}]+)\}", pattern)
                    if m:
                        variants = m.group(1).split(",")
                        base = pattern[: m.start()] + "{}" + pattern[m.end() :]
                        for v in variants:
                            found.extend(sorted(parent.glob(base.format(v.strip()))))
                    else:
                        found.extend(sorted(parent.glob(pattern)))
                else:
                    found.extend(sorted(parent.glob(pattern)))
            elif path.exists():
                found.append(path)
    elif jurisdiction_id:
        for base in (root / "data" / "bronze" / jurisdiction_id, root / "data" / "raw" / jurisdiction_id):
            if base.is_dir():
                for suf in SUPPORTED_SUFFIXES:
                    found.extend(sorted(base.glob(f"*{suf}")))

    # de-dupe preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for f in found:
        rp = f.resolve()
        if rp not in seen and f.suffix.lower() in SUPPORTED_SUFFIXES:
            seen.add(rp)
            out.append(f)
    return out


def read_table(path: Path) -> pl.DataFrame:
    """Load one CSV or Excel file into a Polars DataFrame (all columns as Utf8 where practical)."""
    suf = path.suffix.lower()
    if suf in {".csv", ".tsv"}:
        sep = "\t" if suf == ".tsv" else ","
        return pl.read_csv(
            path,
            separator=sep,
            infer_schema_length=10_000,
            ignore_errors=True,
            truncate_ragged_lines=True,
        )
    if suf in {".xlsx", ".xls"}:
        # Polars read_excel uses fastexcel/openpyxl depending on install
        try:
            return pl.read_excel(path)
        except Exception:
            # Fallback via openpyxl → rows
            from openpyxl import load_workbook

            wb = load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return pl.DataFrame()
            headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
            data = [dict(zip(headers, r)) for r in rows[1:]]
            return pl.DataFrame(data)
    raise ValueError(f"Unsupported file type: {path}")


class FileCSVConnector(Connector):
    """Yield raw dicts from local CSV/XLS files."""

    def __init__(
        self,
        files: list[Path] | None = None,
        *,
        jurisdiction_id: str | None = None,
        root: Path | None = None,
        globs: list[str] | None = None,
    ):
        self.root = root or Path.cwd()
        if files:
            self.files = files
        else:
            self.files = discover_files(*(globs or []), jurisdiction_id=jurisdiction_id, root=self.root)
        if not self.files:
            raise FileNotFoundError(
                f"No CSV/XLS files found for jurisdiction={jurisdiction_id!r}. "
                f"Place files under data/bronze/{jurisdiction_id}/ or data/raw/{jurisdiction_id}/, "
                "or run scripts/export_arcgis_sample.py first."
            )

    def fetch(self, since: date | None = None, until: date | None = None) -> Iterator[dict[str, Any]]:
        # Date filtering is applied downstream in normalize (issued_date field varies by source).
        # Optional since/until kept for Connector interface parity.
        _ = since, until
        for path in self.files:
            df = read_table(path)
            for row in df.iter_rows(named=True):
                # Normalize None-ish and keep keys as strings
                clean = {str(k): (None if v is None else v) for k, v in row.items()}
                clean["_source_file"] = str(path)
                yield clean

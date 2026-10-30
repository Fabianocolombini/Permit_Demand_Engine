"""ArcGIS FeatureServer connector — DEFERRED.

Live ingest is out of scope for this PR. Use:
  - scripts/export_arcgis_sample.py to bootstrap a CSV sample
  - src/ingest/file_csv.py as the primary connector

This module will implement pagination via exceededTransferLimit (V1.1 §1.2) later.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterator

from src.ingest.base import Connector


class ArcGISConnector(Connector):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Live ArcGIS connector deferred. Export a CSV with "
            "scripts/export_arcgis_sample.py and ingest via FileCSVConnector."
        )

    def fetch(self, since: date | None = None, until: date | None = None) -> Iterator[dict[str, Any]]:
        raise NotImplementedError

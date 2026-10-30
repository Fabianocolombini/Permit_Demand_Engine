"""ArcGIS FeatureServer / MapServer query connector with pagination + retry."""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Iterator
from urllib.parse import urlparse

import httpx

from src.ingest.base import Connector

DEFAULT_TIMEOUT = 120.0
MAX_ATTEMPTS = 5


class ArcGISConnector(Connector):
    """Paginate via ``exceededTransferLimit`` (never page-size alone)."""

    def __init__(
        self,
        endpoint: str,
        layer: int = 0,
        date_field: str = "PermitIssuedDate",
        date_format: str = "date_only",  # date_only | epoch_ms | iso_text | sql_date
        page_size: int | None = None,
        order_by_fields: str | None = None,
        return_geometry: bool = False,
        out_sr: int = 4326,
        client: httpx.Client | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.layer = layer
        self.date_field = date_field
        self.date_format = date_format
        self.page_size = page_size
        self.order_by_fields = order_by_fields
        self.return_geometry = return_geometry
        self.out_sr = out_sr
        self._client = client
        self._owns_client = client is None
        self._meta: dict[str, Any] | None = None

    def __enter__(self) -> "ArcGISConnector":
        if self._client is None:
            self._client = httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True)
            self._owns_client = True
        return self._client

    def layer_url(self) -> str:
        return f"{self.endpoint}/{self.layer}"

    def probe(self) -> dict[str, Any]:
        meta = self._get_json(self.layer_url(), {"f": "json"})
        count = self._get_json(
            f"{self.layer_url()}/query",
            {"where": "1=1", "returnCountOnly": "true", "f": "json"},
        )
        self._meta = meta
        fields = [{"name": f["name"], "type": f["type"], "alias": f.get("alias")} for f in meta.get("fields") or []]
        return {
            "name": meta.get("name"),
            "type": meta.get("type"),
            "geometry_type": meta.get("geometryType"),
            "max_record_count": meta.get("maxRecordCount", 1000),
            "supports_pagination": bool(
                (meta.get("advancedQueryCapabilities") or {}).get("supportsPagination", True)
            ),
            "object_id_field": meta.get("objectIdField") or meta.get("objectIdFieldName"),
            "fields": fields,
            "total_features": count.get("count"),
            "host": urlparse(self.endpoint).netloc,
        }

    def effective_page_size(self) -> int:
        if self.page_size:
            return self.page_size
        if self._meta is None:
            try:
                self.probe()
            except Exception:
                return 1000
        mrc = int((self._meta or {}).get("maxRecordCount") or 1000)
        return max(1, min(mrc, 2000))

    def build_where(self, since: date | None, until: date | None) -> str:
        clauses: list[str] = []
        if since is not None:
            clauses.append(self._date_clause(">=", since))
        if until is not None:
            clauses.append(self._date_clause("<", until))
        return " AND ".join(clauses) if clauses else "1=1"

    def _date_clause(self, op: str, d: date) -> str:
        field = self.date_field
        iso = d.isoformat()
        fmt = self.date_format
        if fmt == "year_int":
            return f"{field} {op} {d.year}"
        if fmt == "epoch_ms":
            # midnight UTC
            from datetime import datetime, timezone

            ms = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
            return f"{field} {op} {ms}"
        if fmt == "sql_date":
            return f"{field} {op} DATE '{iso}'"
        # date_only / iso_text — string compare works for DateOnly and many ISO text fields
        return f"{field} {op} '{iso}'"

    def fetch(self, since: date | None = None, until: date | None = None) -> Iterator[dict[str, Any]]:
        where = self.build_where(since, until)
        page_size = self.effective_page_size()
        offset = 0
        oid_field = None
        if self._meta:
            oid_field = self._meta.get("objectIdField") or self._meta.get("objectIdFieldName")
        order = self.order_by_fields or oid_field

        while True:
            params: dict[str, Any] = {
                "where": where,
                "outFields": "*",
                "returnGeometry": "true" if self.return_geometry else "false",
                "resultOffset": offset,
                "resultRecordCount": page_size,
                "f": "json",
            }
            if self.return_geometry:
                params["outSR"] = self.out_sr
            if order:
                params["orderByFields"] = order

            payload = self._get_json(f"{self.layer_url()}/query", params)
            if payload.get("error"):
                raise RuntimeError(f"ArcGIS error: {payload['error']}")

            features = payload.get("features") or []
            if not features:
                break

            for feat in features:
                attrs = dict(feat.get("attributes") or {})
                geom = feat.get("geometry")
                if geom and self.return_geometry:
                    # Flatten common point geometry for CSV friendliness
                    if "x" in geom and "y" in geom:
                        attrs["_lon"] = geom.get("x")
                        attrs["_lat"] = geom.get("y")
                    attrs["_geometry_json"] = str(geom)
                yield attrs

            offset += len(features)
            if not payload.get("exceededTransferLimit", False):
                # Also stop if page came back short of page_size (some servers omit the flag)
                if len(features) < page_size:
                    break
                # Ambiguous: some hosts return full pages without the flag forever — break to be safe
                # only when flag is explicitly False/absent AND we already got a short page above.
                # If full page and no flag, continue one more? Spec says trust the flag.
                # When flag absent on full page, keep going (common on older MapServers).
                if "exceededTransferLimit" in payload and not payload["exceededTransferLimit"]:
                    break
                # No flag + full page → continue
                continue
            # exceededTransferLimit true → continue

    def count(self, since: date | None = None, until: date | None = None) -> int | None:
        where = self.build_where(since, until)
        payload = self._get_json(
            f"{self.layer_url()}/query",
            {"where": where, "returnCountOnly": "true", "f": "json"},
        )
        if payload.get("error"):
            raise RuntimeError(f"ArcGIS error: {payload['error']}")
        return payload.get("count")

    def _get_json(self, url: str, params: dict[str, Any], attempt: int = 0) -> dict[str, Any]:
        try:
            r = self.client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            # Soft errors sometimes return 200 with error object — retry transient codes
            if isinstance(data, dict) and data.get("error") and attempt < MAX_ATTEMPTS - 1:
                err = data["error"]
                code = err.get("code") if isinstance(err, dict) else None
                if code in (504, 503, 502, 500, 429, None):
                    time.sleep(2**attempt)
                    return self._get_json(url, params, attempt + 1)
            return data if isinstance(data, dict) else {"value": data}
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.TransportError):
            if attempt >= MAX_ATTEMPTS - 1:
                raise
            time.sleep(2**attempt)
            return self._get_json(url, params, attempt + 1)

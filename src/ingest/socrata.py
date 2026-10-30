"""Socrata SODA connector with pagination + retry."""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Iterator
from urllib.parse import urlparse

import httpx

from src.ingest.base import Connector

DEFAULT_TIMEOUT = 120.0
MAX_ATTEMPTS = 5


class SocrataConnector(Connector):
    def __init__(
        self,
        endpoint: str,
        date_field: str = "issue_permit_date",
        page_size: int = 5000,
        client: httpx.Client | None = None,
        app_token: str | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.date_field = date_field
        self.page_size = page_size
        self.app_token = app_token
        self._client = client
        self._owns_client = client is None

    def __enter__(self) -> "SocrataConnector":
        if self._client is None:
            headers = {}
            if self.app_token:
                headers["X-App-Token"] = self.app_token
            self._client = httpx.Client(
                timeout=DEFAULT_TIMEOUT, follow_redirects=True, headers=headers
            )
        return self

    def __exit__(self, *args: Any) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            headers = {}
            if self.app_token:
                headers["X-App-Token"] = self.app_token
            self._client = httpx.Client(
                timeout=DEFAULT_TIMEOUT, follow_redirects=True, headers=headers
            )
            self._owns_client = True
        return self._client

    def probe(self) -> dict[str, Any]:
        """Best-effort metadata via /api/views/{id}.json when endpoint looks like resource URL."""
        parsed = urlparse(self.endpoint)
        # e.g. https://data.cityoforlando.net/resource/ryhf-m453.json
        parts = [p for p in parsed.path.split("/") if p]
        dataset_id = None
        if "resource" in parts:
            idx = parts.index("resource")
            if idx + 1 < len(parts):
                dataset_id = parts[idx + 1].replace(".json", "")
        meta: dict[str, Any] = {"endpoint": self.endpoint, "host": parsed.netloc}
        if dataset_id:
            view = self._get_json(f"https://{parsed.netloc}/api/views/{dataset_id}.json", {})
            meta.update(
                {
                    "name": view.get("name"),
                    "fields": [
                        {"name": c.get("fieldName"), "type": c.get("dataTypeName")}
                        for c in view.get("columns") or []
                    ],
                    "row_count": view.get("columns") and view.get("viewCount"),
                    "dataset_id": dataset_id,
                }
            )
        # Live count via $select=count(*)
        try:
            rows = self._get_json(self.endpoint, {"$select": "count(*) as n"})
            if isinstance(rows, list) and rows:
                meta["total_features"] = int(rows[0].get("n") or rows[0].get("count") or 0)
        except Exception as exc:  # noqa: BLE001
            meta["count_error"] = str(exc)
        return meta

    def build_where(self, since: date | None, until: date | None) -> str | None:
        clauses: list[str] = []
        if since is not None:
            clauses.append(f"{self.date_field} >= '{since.isoformat()}'")
        if until is not None:
            clauses.append(f"{self.date_field} < '{until.isoformat()}'")
        return " AND ".join(clauses) if clauses else None

    def fetch(self, since: date | None = None, until: date | None = None) -> Iterator[dict[str, Any]]:
        offset = 0
        where = self.build_where(since, until)
        while True:
            params: dict[str, Any] = {
                "$limit": self.page_size,
                "$offset": offset,
                "$order": self.date_field,
            }
            if where:
                params["$where"] = where
            rows = self._get_json(self.endpoint, params)
            if not isinstance(rows, list):
                raise RuntimeError(f"Unexpected Socrata response: {type(rows)}")
            if not rows:
                break
            yield from rows
            offset += len(rows)
            if len(rows) < self.page_size:
                break

    def count(self, since: date | None = None, until: date | None = None) -> int | None:
        params: dict[str, Any] = {"$select": "count(*) as n"}
        where = self.build_where(since, until)
        if where:
            params["$where"] = where
        rows = self._get_json(self.endpoint, params)
        if isinstance(rows, list) and rows:
            return int(rows[0].get("n") or rows[0].get("count") or 0)
        return None

    def _get_json(self, url: str, params: dict[str, Any], attempt: int = 0) -> Any:
        try:
            r = self.client.get(url, params=params)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.TransportError):
            if attempt >= MAX_ATTEMPTS - 1:
                raise
            time.sleep(2**attempt)
            return self._get_json(url, params, attempt + 1)

"""Shovels.ai API v2 connector — cursor pagination, retry, credit-aware.

Auth: ``SHOVELS_API_KEY`` via ``X-API-Key`` header. Never log or persist the key.
Docs: https://docs.shovels.ai/ — ``GET /v2/permits/search`` with ``geo_id``,
``permit_from``, ``permit_to``; page with ``cursor`` / ``next_cursor``; max ``size=100``.

Credits: one returned record = one credit (``X-Credits-*`` response headers).
HTTP 402 = credit limit exceeded; 429 = rate limit.
"""

from __future__ import annotations

import os
import time
from datetime import date, timedelta
from typing import Any, Iterator

import httpx

from src.ingest.base import Connector

BASE_URL = "https://api.shovels.ai/v2"
DEFAULT_TIMEOUT = 120.0
MAX_ATTEMPTS = 6
DEFAULT_PAGE_SIZE = 100  # API max
ENV_API_KEY = "SHOVELS_API_KEY"


class ShovelsAuthError(RuntimeError):
    """Missing or empty API key."""


class ShovelsCreditLimitError(RuntimeError):
    """HTTP 402 — plan credit limit reached."""

    def __init__(self, message: str, *, limit: Any = None, upgrade_url: str | None = None):
        super().__init__(message)
        self.limit = limit
        self.upgrade_url = upgrade_url


class ShovelsAPIError(RuntimeError):
    """Non-retryable API failure."""


def api_key_length(env: dict[str, str] | None = None) -> int:
    """Return length of ``SHOVELS_API_KEY`` without exposing the value."""
    src = env if env is not None else os.environ
    return len(src.get(ENV_API_KEY) or "")


def require_api_key(env: dict[str, str] | None = None) -> str:
    src = env if env is not None else os.environ
    key = src.get(ENV_API_KEY) or ""
    if not key:
        raise ShovelsAuthError(
            f"{ENV_API_KEY} is missing or empty (length={len(key)}). "
            "Configure it as a Cloud Agent environment secret."
        )
    return key


def flatten_permit(item: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested address / geo_ids for CSV-friendly bronze rows."""
    row: dict[str, Any] = {}
    for k, v in item.items():
        if k in ("address", "geo_ids") and isinstance(v, dict):
            prefix = "address_" if k == "address" else "geo_"
            for sk, sv in v.items():
                if sk == "latlng" and isinstance(sv, (list, tuple)) and len(sv) >= 2:
                    row["address_lat"] = sv[0]
                    row["address_lon"] = sv[1]
                elif isinstance(sv, (dict, list)):
                    import json

                    row[f"{prefix}{sk}"] = json.dumps(sv, ensure_ascii=False)
                else:
                    row[f"{prefix}{sk}"] = sv
        elif k == "tags" and isinstance(v, list):
            row["tags"] = "|".join(str(t) for t in v)
        elif isinstance(v, (dict, list)):
            import json

            row[k] = json.dumps(v, ensure_ascii=False)
        else:
            row[k] = v
    # Convenience aliases for PDE field_map
    if "number" in row and "permit_id" not in row:
        row["permit_id"] = row.get("number")
    if "issue_date" in row and "issued_date" not in row:
        row["issued_date"] = row.get("issue_date")
    if "job_value" in row and row["job_value"] is not None:
        try:
            # API returns cents — also expose USD dollars for downstream
            row["job_value_usd"] = float(row["job_value"]) / 100.0
        except (TypeError, ValueError):
            pass
    return row


class ShovelsConnector(Connector):
    """Live Shovels permit search with cursor pagination + exponential backoff."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        page_size: int = DEFAULT_PAGE_SIZE,
        client: httpx.Client | None = None,
        min_interval_s: float = 0.15,
    ) -> None:
        self.api_key = api_key if api_key is not None else require_api_key()
        self.base_url = base_url.rstrip("/")
        self.page_size = max(1, min(int(page_size), 100))
        self._client = client
        self._owns_client = client is None
        self.min_interval_s = min_interval_s
        self._last_request_at = 0.0
        self.last_credits: dict[str, str | None] = {}
        self.rows_fetched = 0
        self.stopped_reason: str | None = None

    def __enter__(self) -> "ShovelsConnector":
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key, "Accept": "application/json"},
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
            )
        return self

    def __exit__(self, *args: Any) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key, "Accept": "application/json"},
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
            )
            self._owns_client = True
        return self._client

    def usage(self) -> dict[str, Any]:
        return self._request_json("GET", "/usage")

    def release(self) -> dict[str, Any]:
        return self._request_json("GET", "/meta/release")

    def search_counties(self, q: str, *, state: str | None = "FL") -> list[dict[str, Any]]:
        data = self._request_json("GET", "/counties/search", params={"q": q})
        items = list(data.get("items") or [])
        if state:
            items = [i for i in items if (i.get("state") or "").upper() == state.upper()]
        return items

    def search_cities(self, q: str, *, state: str | None = "FL") -> list[dict[str, Any]]:
        data = self._request_json("GET", "/cities/search", params={"q": q})
        items = list(data.get("items") or [])
        if state:
            items = [i for i in items if (i.get("state") or "").upper() == state.upper()]
        return items

    def search_jurisdictions(self, q: str, *, state: str | None = "FL") -> list[dict[str, Any]]:
        data = self._request_json("GET", "/jurisdictions/search", params={"q": q})
        items = list(data.get("items") or [])
        if state:
            items = [i for i in items if (i.get("state") or "").upper() == state.upper()]
        return items

    def resolve_geo_id(
        self,
        *,
        geo_id: str | None = None,
        county_q: str | None = None,
        city_q: str | None = None,
        jurisdiction_q: str | None = None,
        state: str = "FL",
    ) -> str:
        if geo_id:
            return geo_id
        if county_q:
            hits = self.search_counties(county_q, state=state)
            if not hits:
                raise ShovelsAPIError(f"No county match for q={county_q!r} state={state}")
            # Prefer exact-ish name contains
            best = _best_geo_hit(hits, county_q)
            return str(best["geo_id"])
        if city_q:
            hits = self.search_cities(city_q, state=state)
            if not hits:
                raise ShovelsAPIError(f"No city match for q={city_q!r} state={state}")
            return str(_best_geo_hit(hits, city_q)["geo_id"])
        if jurisdiction_q:
            hits = self.search_jurisdictions(jurisdiction_q, state=state)
            if not hits:
                raise ShovelsAPIError(f"No jurisdiction match for q={jurisdiction_q!r} state={state}")
            return str(_best_geo_hit(hits, jurisdiction_q)["geo_id"])
        raise ShovelsAPIError("Provide geo_id, county_q, city_q, or jurisdiction_q")

    def count(
        self,
        geo_id: str,
        since: date,
        until: date,
    ) -> dict[str, Any] | None:
        """Return ``total_count`` object (``{value, relation}``) or None."""
        # API date window is inclusive on both ends; our until is exclusive → subtract 1 day
        permit_to = _inclusive_to(until)
        data = self._request_json(
            "GET",
            "/permits/search",
            params={
                "geo_id": geo_id,
                "permit_from": since.isoformat(),
                "permit_to": permit_to.isoformat(),
                "size": 1,
                "include_count": "true",
            },
        )
        return data.get("total_count")

    def fetch(
        self,
        since: date | None = None,
        until: date | None = None,
        *,
        geo_id: str | None = None,
        max_records: int | None = None,
        flatten: bool = True,
        require_issue_since: date | None = None,
    ) -> Iterator[dict[str, Any]]:
        if since is None:
            since = date(2021, 1, 1)
        if until is None:
            until = date.today() + timedelta(days=1)
        if not geo_id:
            raise ShovelsAPIError("fetch() requires geo_id=")

        permit_to = _inclusive_to(until)
        cursor: str | None = None
        self.rows_fetched = 0
        self.stopped_reason = None

        while True:
            params: dict[str, Any] = {
                "geo_id": geo_id,
                "permit_from": since.isoformat(),
                "permit_to": permit_to.isoformat(),
                "size": self.page_size,
            }
            if cursor:
                params["cursor"] = cursor
            else:
                params["include_count"] = "true"

            try:
                data = self._request_json("GET", "/permits/search", params=params)
            except ShovelsCreditLimitError:
                self.stopped_reason = "credit_limit"
                raise

            items = list(data.get("items") or [])
            if not items:
                self.stopped_reason = self.stopped_reason or "exhausted"
                break

            for item in items:
                if require_issue_since is not None:
                    iss = (item.get("issue_date") or "")[:10]
                    if iss and iss < require_issue_since.isoformat():
                        continue
                row = flatten_permit(item) if flatten else item
                yield row
                self.rows_fetched += 1
                if max_records is not None and self.rows_fetched >= max_records:
                    self.stopped_reason = "max_records"
                    return

            cursor = data.get("next_cursor")
            if not cursor:
                self.stopped_reason = "exhausted"
                break

    def _throttle(self) -> None:
        now = time.monotonic()
        wait = self.min_interval_s - (now - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        attempt: int = 0,
    ) -> dict[str, Any]:
        self._throttle()
        try:
            r = self.client.request(method, path, params=params)
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt >= MAX_ATTEMPTS - 1:
                raise
            time.sleep(min(60, 2**attempt))
            return self._request_json(method, path, params=params, attempt=attempt + 1)

        # Capture credit headers without logging the API key
        self.last_credits = {
            "request": r.headers.get("X-Credits-Request"),
            "limit": r.headers.get("X-Credits-Limit"),
            "remaining": r.headers.get("X-Credits-Remaining"),
        }

        if r.status_code == 402:
            detail = _safe_detail(r)
            raise ShovelsCreditLimitError(
                detail.get("error") if isinstance(detail, dict) else str(detail),
                limit=detail.get("limit") if isinstance(detail, dict) else None,
                upgrade_url=detail.get("upgrade_url") if isinstance(detail, dict) else None,
            )

        if r.status_code in (429, 500, 502, 503, 504):
            if attempt >= MAX_ATTEMPTS - 1:
                raise ShovelsAPIError(f"Shovels HTTP {r.status_code}: {r.text[:300]}")
            # Honor Retry-After when present
            ra = r.headers.get("Retry-After")
            try:
                delay = float(ra) if ra else min(60, 2**attempt)
            except ValueError:
                delay = min(60, 2**attempt)
            time.sleep(delay)
            return self._request_json(method, path, params=params, attempt=attempt + 1)

        if r.status_code in (401, 403):
            raise ShovelsAuthError(f"Shovels auth failed HTTP {r.status_code} (key length={len(self.api_key)})")

        if r.status_code >= 400:
            raise ShovelsAPIError(f"Shovels HTTP {r.status_code}: {r.text[:500]}")

        data = r.json()
        return data if isinstance(data, dict) else {"value": data}


def _inclusive_to(until_exclusive: date) -> date:
    """Convert half-open [since, until) window to inclusive permit_to date."""
    return until_exclusive - timedelta(days=1)


def _best_geo_hit(hits: list[dict[str, Any]], q: str) -> dict[str, Any]:
    qn = q.lower().replace(" county", "").strip()
    for h in hits:
        name = (h.get("name") or "").lower()
        if name.startswith(qn) or qn in name.split(",")[0]:
            return h
    return hits[0]


def _safe_detail(r: httpx.Response) -> Any:
    try:
        body = r.json()
    except Exception:
        return r.text[:300]
    if isinstance(body, dict) and "detail" in body:
        return body["detail"]
    return body

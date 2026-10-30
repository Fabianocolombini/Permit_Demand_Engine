"""Socrata connector — DEFERRED (statewide V1.1 wave later)."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterator

from src.ingest.base import Connector


class SocrataConnector(Connector):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Live Socrata connector deferred. Use file CSV/XLS ingest for now."
        )

    def fetch(self, since: date | None = None, until: date | None = None) -> Iterator[dict[str, Any]]:
        raise NotImplementedError

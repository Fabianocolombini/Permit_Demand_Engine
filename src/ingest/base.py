"""Connector interface — live ArcGIS/Socrata deferred; file connector implements this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Iterator


class Connector(ABC):
    @abstractmethod
    def fetch(self, since: date | None = None, until: date | None = None) -> Iterator[dict[str, Any]]:
        """Yield raw attribute dicts (one per permit row)."""

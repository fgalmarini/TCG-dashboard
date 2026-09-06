"""Provider boundaries shared by the Multi-TCG domain.

Provider-specific authentication, endpoint construction and local documentation now
live under ``backend/integrations/<provider>/``. This module remains the game-generic
protocol boundary for legacy/importer callers until runtime provider migration is
completed.

The dashboard API consumes normalized database rows only. Implementations may perform
network I/O in maintenance/import commands, never during an API request.
"""

from __future__ import annotations

from typing import Iterable, Protocol


class CatalogAdapter(Protocol):
    code: str

    def fetch_releases(self) -> Iterable[dict]: ...

    def fetch_printings(self, release_external_id: int) -> Iterable[dict]: ...


class PricingProvider(Protocol):
    code: str

    def fetch_exact_prices(self, external_printing_id: str, language: str) -> Iterable[dict]: ...


class ImageProvider(Protocol):
    code: str

    def resolve_image(self, printing: dict, language: str): ...


class MagicCatalogAdapter:
    """Marker for the existing Scryfall-backed Magic import path.

    The established importer remains the implementation because it already provides
    controlled fixtures/cache, physical-card filtering and exact Scryfall identity.
    New Scryfall auth/request policy belongs in ``backend/integrations/scryfall``.
    """

    code = "magic"

    def fetch_releases(self) -> Iterable[dict]:
        raise NotImplementedError("Use backend/scripts/import_magic_lotr_catalog.py")

    def fetch_printings(self, release_external_id: int) -> Iterable[dict]:
        raise NotImplementedError("Use backend/scripts/import_magic_lotr_catalog.py")

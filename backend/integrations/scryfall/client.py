"""Request construction for Magic metadata/images via Scryfall."""

from __future__ import annotations

from urllib.parse import quote
from urllib.request import Request

from .auth import build_headers

BASE_URL = "https://api.scryfall.com"


class ScryfallClient:
    def card_by_set_number_request(self, set_code: str, collector_number: str) -> Request:
        set_value = quote(set_code.strip().lower(), safe="")
        number = quote(collector_number.strip(), safe="")
        if not set_value or not number:
            raise ValueError("set_code and collector_number are required")
        return Request(
            f"{BASE_URL}/cards/{set_value}/{number}",
            headers=build_headers(),
            method="GET",
        )

    def bulk_data_index_request(self) -> Request:
        return Request(
            f"{BASE_URL}/bulk-data",
            headers=build_headers(),
            method="GET",
        )

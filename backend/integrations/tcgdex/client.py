"""Request construction for Pokémon metadata/images via TCGdex."""

from __future__ import annotations

from urllib.parse import quote
from urllib.request import Request

from .auth import build_headers

BASE_URL = "https://api.tcgdex.net/v2"


class TcgdexClient:
    def card_request(self, card_id: str, *, language: str = "en") -> Request:
        card = quote(card_id.strip(), safe="")
        lang = quote(language.strip().lower(), safe="")
        if not card or not lang:
            raise ValueError("card_id and language are required")
        return Request(
            f"{BASE_URL}/{lang}/cards/{card}",
            headers=build_headers(),
            method="GET",
        )

    def set_card_request(
        self,
        set_id: str,
        local_id: str,
        *,
        language: str = "en",
    ) -> Request:
        set_value = quote(set_id.strip(), safe="")
        local = quote(local_id.strip(), safe="")
        lang = quote(language.strip().lower(), safe="")
        if not set_value or not local or not lang:
            raise ValueError("set_id, local_id and language are required")
        return Request(
            f"{BASE_URL}/{lang}/sets/{set_value}/{local}",
            headers=build_headers(),
            method="GET",
        )

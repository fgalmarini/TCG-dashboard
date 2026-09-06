"""Request construction for secondary TCGplayer-oriented analytics."""

from __future__ import annotations

from urllib.parse import urlencode
from urllib.request import Request

from .auth import build_headers

BASE_URL = "https://api.tcgapi.dev/v1"


class TcgApiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._headers = build_headers(api_key)

    def card_prices_request(self, card_id: int | str) -> Request:
        card = str(card_id).strip()
        if not card.isdigit():
            raise ValueError("TCG API card_id must be numeric")
        return Request(
            f"{BASE_URL}/cards/{card}/prices",
            headers=self._headers,
            method="GET",
        )

    def top_movers_request(self, *, game: str, period: str = "7d") -> Request:
        query = urlencode({"game": game.strip().lower(), "period": period})
        return Request(
            f"{BASE_URL}/prices/top-movers?{query}",
            headers=self._headers,
            method="GET",
        )

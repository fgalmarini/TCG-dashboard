"""Request construction for the FALLBACK current-EUR price provider."""

from __future__ import annotations

import json
from urllib.request import Request

from .auth import build_headers

# The provider's current documentation examples expose this API origin.
# Keep it provider-local so a future host change is isolated here.
BASE_URL = "https://tcg-api-production-5148.up.railway.app"


class TcgCardmarketClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._headers = build_headers(api_key)

    def card_request(self, game: str, product_id: int | str) -> Request:
        slug = game.strip().lower()
        product = str(product_id).strip()
        if not slug:
            raise ValueError("game slug is required")
        if not product.isdigit():
            raise ValueError("Cardmarket product_id must be numeric")
        return Request(
            f"{BASE_URL}/cards/{slug}/{product}",
            headers=self._headers,
            method="GET",
        )

    def batch_request(self, game: str, product_ids: list[int | str]) -> Request:
        slug = game.strip().lower()
        ids = [str(value).strip() for value in product_ids]
        if not slug:
            raise ValueError("game slug is required")
        if not ids or any(not value.isdigit() for value in ids):
            raise ValueError("batch requires numeric Cardmarket product IDs")
        headers = {**self._headers, "Content-Type": "application/json"}
        body = json.dumps({"game": slug, "cardIds": ids}).encode("utf-8")
        return Request(
            f"{BASE_URL}/cards/batch",
            data=body,
            headers=headers,
            method="POST",
        )

"""Request construction for the PRIMARY current-EUR price provider.

No request is executed by this module. Maintenance code may use the returned Request
objects after applying retry/rate-limit policy.
"""

from __future__ import annotations

from urllib.parse import urlencode
from urllib.request import Request

from .auth import build_headers

BASE_URL = "https://cardmarketapi.com/api/v1"
DEFAULT_LANGUAGE = "english"
DEFAULT_CONDITION = "nm"


class CardmarketPrimaryClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._headers = build_headers(api_key)

    def card_request(
        self,
        product_id: int | str,
        *,
        language: str = DEFAULT_LANGUAGE,
        condition: str = DEFAULT_CONDITION,
    ) -> Request:
        product = str(product_id).strip()
        if not product.isdigit():
            raise ValueError("Cardmarket product_id must be numeric")
        query = urlencode({"language": language, "condition": condition})
        return Request(
            f"{BASE_URL}/card/{product}?{query}",
            headers=self._headers,
            method="GET",
        )

    def usage_request(self) -> Request:
        return Request(f"{BASE_URL}/usage", headers=self._headers, method="GET")

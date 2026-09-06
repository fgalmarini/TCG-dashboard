"""Authentication contract for cardmarketapi.com."""

from __future__ import annotations

import os
from collections.abc import Mapping

ENV_API_KEY = "CARDMARKET_PRIMARY_API_KEY"
HEADER_NAME = "X-API-Key"


class MissingCredentialError(RuntimeError):
    """Raised when this provider is invoked without its configured API key."""


def build_headers(
    api_key: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source = os.environ if environ is None else environ
    key = (api_key or source.get(ENV_API_KEY, "")).strip()
    if not key:
        raise MissingCredentialError(
            f"{ENV_API_KEY} is required for cardmarketapi.com requests"
        )
    return {HEADER_NAME: key, "Accept": "application/json"}

"""Authentication contract for tcgapi.dev."""

from __future__ import annotations

import os
from collections.abc import Mapping

ENV_API_KEY = "TCGAPI_KEY"
HEADER_NAME = "X-API-Key"


class MissingCredentialError(RuntimeError):
    """Raised when an authenticated TCG API endpoint is called without a key."""


def build_headers(
    api_key: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source = os.environ if environ is None else environ
    key = (api_key or source.get(ENV_API_KEY, "")).strip()
    if not key:
        raise MissingCredentialError(f"{ENV_API_KEY} is required for this TCG API request")
    return {HEADER_NAME: key, "Accept": "application/json"}

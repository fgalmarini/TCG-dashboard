"""Authentication contract for TCGdex."""

from __future__ import annotations

AUTH_REQUIRED = False


def build_headers() -> dict[str, str]:
    """TCGdex REST access currently requires no API credential."""
    return {"Accept": "application/json"}

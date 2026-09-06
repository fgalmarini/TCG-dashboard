"""Authentication/request-header contract for Scryfall."""

from __future__ import annotations

AUTH_REQUIRED = False
USER_AGENT = "TCG-Dashboard/1.0"
ACCEPT = "application/json;q=0.9,*/*;q=0.8"


def build_headers() -> dict[str, str]:
    """Scryfall requires no API key; send explicit well-formed request headers."""
    return {"User-Agent": USER_AGENT, "Accept": ACCEPT}

"""Game-generic exact-language price normalization."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class MarketplacePrice:
    current_price: float | None
    currency: str | None
    sample_size: int
    lowest_price: float | None
    median_price: float | None
    confidence: str | None


def _false(value) -> bool:
    return value in (False, 0, "false", "False", None)


def resolve_cardtrader_marketplace(offers: list[dict], language: str) -> MarketplacePrice:
    """Median of the five cheapest distinct eligible sellers.

    Missing bundle_size is accepted as one only because callers fetch One Piece Single
    Card Blueprints. Any explicit non-one bundle is rejected.
    """
    cheapest_by_seller: dict[int | str, tuple[int, str]] = {}
    for offer in offers:
        props = offer.get("properties_hash") or {}
        user = offer.get("user") or {}
        seller_id = user.get("id")
        if seller_id is None or offer.get("on_vacation") is True:
            continue
        if offer.get("graded") not in (False, 0, "false", None):
            continue
        if props.get("condition") != "Near Mint":
            continue
        if props.get("onepiece_language") != language:
            continue
        if not _false(props.get("signed")) or not _false(props.get("altered")):
            continue
        if offer.get("bundle_size") not in (None, 1, "1"):
            continue
        price = offer.get("price") or {}
        cents = offer.get("price_cents", price.get("cents"))
        currency = offer.get("price_currency", price.get("currency"))
        if not isinstance(cents, int) or cents < 0 or not currency:
            continue
        current = cheapest_by_seller.get(seller_id)
        if current is None or cents < current[0]:
            cheapest_by_seller[seller_id] = (cents, str(currency))

    candidates = sorted(cheapest_by_seller.values(), key=lambda value: value[0])[:5]
    if not candidates:
        return MarketplacePrice(None, None, 0, None, None, None)
    currencies = {value[1] for value in candidates}
    if len(currencies) != 1:
        return MarketplacePrice(None, None, 0, None, None, None)
    values = [value[0] / 100 for value in candidates]
    sample_size = len(values)
    confidence = "high" if sample_size >= 5 else "medium" if sample_size >= 3 else "low"
    median_value = round(float(median(values)), 2)
    return MarketplacePrice(
        current_price=median_value,
        currency=currencies.pop(),
        sample_size=sample_size,
        lowest_price=round(values[0], 2),
        median_price=median_value,
        confidence=confidence,
    )

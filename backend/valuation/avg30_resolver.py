"""Deterministic, read-only Cardmarket Avg30 valuation resolver."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any, Literal

NULL_REASONS = {
    "MISSING_AVG30", "IDENTITY_UNRESOLVED", "LANGUAGE_UNRESOLVED",
    "FINISH_UNRESOLVED", "VARIANT_UNRESOLVED", "PRODUCT_UNRESOLVED",
}

ValuationScope = Literal["collection", "wishlist", "global"]

# This predicate is deliberately independent from ``is_current``.  Legacy
# current-price rows and additive valuation rows have different lifecycles.
USABLE_VALUATION_SQL = """(
    r.valuation_status IN ('ESTIMATED', 'EXACT')
    AND r.valuation_method IS NOT NULL
    AND r.valuation_value IS NOT NULL
    AND r.valuation_value > 0
)"""


@dataclass(frozen=True)
class CurrentValuation:
    valuation_status: str
    valuation_method: str
    valuation_value: float
    reason: str | None
    valuation_currency: str | None
    valuation_source: str | None
    resolution_scope: str
    resolution_id: int


def resolve_current_valuation(
    conn: sqlite3.Connection,
    *,
    card_id: int | None,
    language_id: int | None,
    scope: ValuationScope,
    scope_item_id: int | None = None,
) -> CurrentValuation | None:
    """Resolve one item with scoped -> global precedence.

    ``scope_item_id`` is required for collection/wishlist scopes so a scoped
    resolution can never leak from another item.  Language is an exact key;
    there is intentionally no cross-language fallback.
    """
    if scope not in {"collection", "wishlist", "global"}:
        raise ValueError(f"unsupported valuation scope: {scope}")
    if scope != "global" and scope_item_id is None:
        raise ValueError("scope_item_id is required for scoped valuation resolution")
    if card_id is None or language_id is None:
        return None

    scoped_column = {
        "collection": "collection_item_id",
        "wishlist": "wishlist_item_id",
    }.get(scope)
    scoped_clause = "1=0"
    params: list[Any] = []
    if scoped_column:
        scoped_clause = f"r.{scoped_column} = ?"
        params.append(scope_item_id)
        params.extend([card_id, language_id])
    # The global branch is always present, including for a global-only lookup.
    params.extend([card_id, language_id])
    row = conn.execute(
        f"""WITH candidates AS (
                SELECT r.id, r.valuation_status, r.valuation_method,
                       r.valuation_value, r.reason,
                       COALESCE(r.source_currency, r.currency) AS valuation_currency,
                       r.source AS valuation_source,
                       r.resolution_scope, 0 AS precedence
                  FROM printing_price_resolutions r
                 WHERE {scoped_clause}
                   AND r.card_id = ?
                   AND r.language_id = ?
                   AND {USABLE_VALUATION_SQL}
                UNION ALL
                SELECT r.id, r.valuation_status, r.valuation_method,
                       r.valuation_value, r.reason,
                       COALESCE(r.source_currency, r.currency) AS valuation_currency,
                       r.source AS valuation_source,
                       r.resolution_scope, 1 AS precedence
                  FROM printing_price_resolutions r
                 WHERE r.resolution_scope = 'global'
                   AND r.collection_item_id IS NULL
                   AND r.wishlist_item_id IS NULL
                   AND r.card_id = ?
                   AND r.language_id = ?
                   AND {USABLE_VALUATION_SQL}
            )
            SELECT * FROM candidates
             ORDER BY precedence, id DESC
             LIMIT 1""",
        params,
    ).fetchone()
    if row is None:
        return None
    return CurrentValuation(
        valuation_status=row["valuation_status"],
        valuation_method=row["valuation_method"],
        valuation_value=float(row["valuation_value"]),
        reason=row["reason"],
        valuation_currency=row["valuation_currency"],
        valuation_source=row["valuation_source"],
        resolution_scope=row["resolution_scope"],
        resolution_id=row["id"],
    )


def _usable(value: Any) -> bool:
    try:
        return value is not None and float(value) > 0
    except (TypeError, ValueError):
        return False


def _as_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def _age_days(observed_at: str | None, as_of: str) -> int | None:
    if not observed_at:
        return None
    raw = str(observed_at).replace("Z", "+00:00")
    try:
        observed = dt.datetime.fromisoformat(raw).date()
    except ValueError:
        try:
            observed = dt.date.fromisoformat(str(observed_at)[:10])
        except ValueError:
            return None
    return (_as_date(as_of) - observed).days


@dataclass(frozen=True)
class ValuationDecision:
    valuation_status: str | None
    valuation_method: str | None
    valuation_value: float | None
    reason: str | None
    metric_family: str | None
    metric_name: str | None


def resolve_valuation(
    *,
    card: dict[str, Any],
    product: dict[str, Any] | None,
    observation: dict[str, Any] | None,
    identity_evidence: dict[str, Any],
    as_of: str,
) -> ValuationDecision:
    """Resolve one valuation from local evidence; never falls back across metrics."""
    del as_of
    if product is None or not identity_evidence.get("product_valid"):
        return ValuationDecision(None, None, None, "PRODUCT_UNRESOLVED", None, None)
    if not identity_evidence.get("canonical_valid") or identity_evidence.get("identity_blocked"):
        return ValuationDecision(None, None, None, "IDENTITY_UNRESOLVED", None, None)
    if not identity_evidence.get("language_compatible"):
        return ValuationDecision(None, None, None, "LANGUAGE_UNRESOLVED", None, None)
    if not identity_evidence.get("variant_compatible"):
        return ValuationDecision(None, None, None, "VARIANT_UNRESOLVED", None, None)
    family = identity_evidence.get("metric_family")
    if family not in {"base", "foil"} or not identity_evidence.get("finish_compatible"):
        return ValuationDecision(None, None, None, "FINISH_UNRESOLVED", family, None)
    if observation is None:
        return ValuationDecision(None, None, None, "MISSING_AVG30", family, "avg30_alt" if family == "foil" else "avg30")
    metric_name = "avg30_alt" if family == "foil" else "avg30"
    value = observation.get(metric_name)
    if not _usable(value):
        return ValuationDecision(None, None, None, "MISSING_AVG30", family, metric_name)
    if identity_evidence.get("exact_evidence"):
        return ValuationDecision("EXACT", "CARDMARKET_AVG30", float(value), None, family, metric_name)
    return ValuationDecision("ESTIMATED", "CARDMARKET_AVG30", float(value), None, family, metric_name)


def latest_observations(conn: sqlite3.Connection, as_of: str) -> dict[int, dict[str, Any]]:
    """Return one local market snapshot per product, bounded by as_of."""
    upper_bound = (_as_date(as_of) + dt.timedelta(days=1)).isoformat()
    rows = conn.execute(
        """SELECT * FROM market_price_history
           WHERE observed_at < ?
           ORDER BY cardmarket_product_id, observed_at DESC, id DESC""",
        (upper_bound,),
    ).fetchall()
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        result.setdefault(int(row["cardmarket_product_id"]), dict(row))
    return result


def _json_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
        return [str(item).casefold() for item in parsed] if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def build_identity_evidence(
    *, card: dict[str, Any], product: dict[str, Any] | None,
    product_mapping: dict[str, Any] | None,
    scope_mapping: dict[str, Any] | None,
    metric_mapping: dict[str, Any] | None,
    language_exact: bool,
) -> dict[str, Any]:
    product_valid = product is not None
    direct_card = bool(product_mapping and product_mapping.get("status") == "mapped" and product_mapping.get("card_id") == card.get("id"))
    canonical_valid = bool(
        direct_card
        or (scope_mapping and scope_mapping.get("mapping_status") == "EXACT"
            and scope_mapping.get("canonical_card_id") == card.get("canonical_card_id"))
    )
    finish = str(card.get("finish") or "").casefold()
    family = "foil" if finish == "foil" else "base"
    metric_ok = bool(
        (family == "base" and (direct_card or (scope_mapping and scope_mapping.get("mapping_status") == "EXACT")))
        or (metric_mapping
            and metric_mapping.get("metric_family") == "foil"
            and metric_mapping.get("metric_mapping_status") == "EXACT"
            and int(metric_mapping.get("pricing_eligible") or 0) == 1
            and (not metric_mapping.get("card_id") or metric_mapping.get("card_id") == card.get("id")))
    )
    compatible_finishes = _json_list(metric_mapping.get("compatible_finishes") if metric_mapping else None)
    finish_compatible = metric_ok and (not compatible_finishes or finish in compatible_finishes)
    variant_compatible = direct_card or bool(scope_mapping and scope_mapping.get("card_id") == card.get("id"))
    metric_exact = bool(
        metric_mapping
        and metric_mapping.get("metric_family") == family
        and metric_mapping.get("metric_mapping_status") == "EXACT"
        and int(metric_mapping.get("pricing_eligible") or 0) == 1
    )
    exact_evidence = bool(direct_card and language_exact and finish_compatible and variant_compatible and metric_exact)
    return {
        "product_valid": product_valid,
        "canonical_valid": canonical_valid,
        "language_compatible": language_exact,
        "finish_compatible": finish_compatible,
        "variant_compatible": variant_compatible,
        "metric_family": family,
        "exact_evidence": exact_evidence,
        "identity_blocked": bool(scope_mapping and scope_mapping.get("mapping_status") in {"AMBIGUOUS", "MISMATCH", "UNRESOLVED"}),
        "product_mapping_status": product_mapping.get("status") if product_mapping else None,
        "scope_mapping_status": scope_mapping.get("mapping_status") if scope_mapping else None,
        "metric_mapping_status": metric_mapping.get("metric_mapping_status") if metric_mapping else None,
        "pricing_eligible": bool(metric_mapping and metric_mapping.get("pricing_eligible")),
        "metric_exact": metric_exact,
    }

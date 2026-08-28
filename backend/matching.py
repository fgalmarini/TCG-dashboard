"""Canonical Collection identity resolver (printing and physical finish)."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field

FINISH_ALIASES = {
    "normal": "nonfoil", "regular": "nonfoil", "nonfoil": "nonfoil", "non-foil": "nonfoil",
    "foil": "foil", "traditional foil": "foil", "traditional_foil": "foil",
    "etched": "etched", "etched foil": "etched", "etched_foil": "etched", "foil etched": "etched",
    "surge": "surge_foil", "surge foil": "surge_foil", "surge_foil": "surge_foil",
}

@dataclass
class MatchResult:
    status: str
    printing_match_quality: str
    finish_match_quality: str
    matched_card_id: int | None = None
    finish: str | None = None
    treatment: str | None = None
    match_reason: str = ""
    candidates: list[int] = field(default_factory=list)

def normalize(value: str | None) -> str:
    if not value: return ""
    value = unicodedata.normalize("NFKD", value)
    return "".join(c for c in value if not unicodedata.combining(c)).casefold().strip()

def canonical_finish(value: str | None) -> str | None:
    if not value: return None
    key = re.sub(r"\s+", " ", value.replace("_", " ").strip().casefold())
    return FINISH_ALIASES.get(key)

def _raw(card) -> dict:
    try: return json.loads(card["scryfall_raw"] or "{}")
    except (TypeError, ValueError): return {}

def derive_finish(card) -> tuple[str | None, str | None, str]:
    explicit = canonical_finish(card["collection_finish"] or card["finish"])
    if explicit:
        return explicit, card["collection_treatment"] or card["treatment"], "persisted_finish"
    label = normalize(card["variant_label"])
    raw = _raw(card)
    promos = {normalize(v) for v in raw.get("promo_types", [])}
    if "surgefoil" in promos or "surge foil" in label:
        return "surge_foil", "surge_foil", "explicit_surge_metadata"
    if "etched" in label or "etchedfoil" in promos:
        return "etched", "etched", "explicit_etched_metadata"
    # A label describing the owned variant is stronger evidence than the
    # Scryfall `finishes` availability list, which describes the printing.
    if re.search(r"\bnon ?foil\b|\bnormal\b|\bregular\b", label):
        return "nonfoil", card["collection_treatment"] or card["treatment"], "variant_label_exact"
    if re.search(r"\bfoil\b", label):
        return "foil", card["collection_treatment"] or card["treatment"], "variant_label_exact"
    finishes = {canonical_finish(v) for v in raw.get("finishes", [])}
    finishes.discard(None)
    if len(finishes) == 1:
        return next(iter(finishes)), card["treatment"], "single_supported_finish"
    return None, card["treatment"], "finish_not_evident"

def resolve_collection_item(conn, item_id: int) -> MatchResult:
    row = conn.execute("""SELECT ci.*, ci.finish AS collection_finish, ci.treatment AS collection_treatment, c.*, g.code AS game_code
        FROM collection_items ci LEFT JOIN cards c ON c.id=ci.card_id
        LEFT JOIN games g ON g.id=c.game_id WHERE ci.id=?""", (item_id,)).fetchone()
    if row is None: return MatchResult("unmatched", "unmatched", "unresolved", match_reason="collection_item_missing")
    if row["card_id"] is None or row["game_code"] is None:
        return MatchResult("unmatched", "unmatched", "unresolved", match_reason="no_valid_card_id")
    finish, treatment, reason = derive_finish(row)
    fquality = "exact" if finish else "unresolved"
    status = "exact" if finish else "ambiguous"
    return MatchResult(status, "exact", fquality, row["card_id"], finish, treatment, reason)

"""Deteccion y clasificacion de grupos de variantes/parallels.

Se agrupa por (idExpansion, idMetacard) dentro de los productos en scope. La
"sugerencia" de printing_variant nunca es una certeza (confirmado en fase2-cardmarket-
hallazgos-y-schema.md) -- el usuario puede pasar a 'confirmed_parallel' a mano despues.
"""

from dataclasses import dataclass

from config import AMBIGUITY_RELATIVE_THRESHOLD
from parser import extract_variant_label


@dataclass
class VariantDecision:
    id_product: int
    printing_variant: str  # 'normal' | 'suggested_parallel' | 'other'
    variant_label: str | None
    classification_note: str


def group_products(products: list[dict]) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = {}
    for p in products:
        metacard = p.get("idMetacard")
        if metacard is None:
            # No confirmado que pueda faltar, pero si pasa no se agrupa a ciegas:
            # grupo propio de 1, queda reportado por el classify de abajo igual.
            key = ("no_metacard", p["idProduct"])
        else:
            key = (p["idExpansion"], metacard)
        groups.setdefault(key, []).append(p)
    return groups


def classify_variant_group(
    group: list[dict], price_entries_by_product: dict[int, dict]
) -> list[VariantDecision]:
    if len(group) == 1:
        p = group[0]
        return [VariantDecision(p["idProduct"], "normal", extract_variant_label(p["name"]), "single")]

    trends: dict[int, float | None] = {}
    for p in group:
        entry = price_entries_by_product.get(p["idProduct"])
        trends[p["idProduct"]] = entry.get("trend") if entry else None
    known = {k: v for k, v in trends.items() if v is not None}

    winner: int | None = None
    if len(known) < len(group):
        note = "ambiguous_no_price"
    else:
        sorted_vals = sorted(known.values(), reverse=True)
        top, second = sorted_vals[0], sorted_vals[1]
        if top == 0 or (top - second) / top < AMBIGUITY_RELATIVE_THRESHOLD:
            note = "ambiguous_similar_price"
        else:
            note = "suggested"
            winner = max(known, key=known.get)

    decisions = []
    for p in group:
        label = extract_variant_label(p["name"])
        if winner is None:
            printing_variant = "other"
        elif p["idProduct"] == winner:
            printing_variant = "suggested_parallel"
        else:
            printing_variant = "normal"
        decisions.append(VariantDecision(p["idProduct"], printing_variant, label, note))
    return decisions

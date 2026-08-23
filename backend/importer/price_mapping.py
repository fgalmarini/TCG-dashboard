"""Mapeo defensivo de una entrada de price_guide a las columnas de market_price_history.

No hay campo `currency` en ningun archivo de Cardmarket -- se asume EUR implicito
(moneda nativa de Cardmarket), no se almacena (la tabla no tiene columna de currency).
"""

BASE_FIELDS = ("low", "avg", "trend", "avg1", "avg7", "avg30")


def map_price_guide_entry(entry: dict, alt_suffix: str) -> dict:
    """alt_suffix: '-foil' (Magic/One Piece) o '-holo' (Pokemon).

    dict.get() resuelve tanto "key ausente" como "key presente con null" -> None en
    ambos casos (json.loads ya convierte null a None), sin necesidad de logica especial.
    """
    result = {field: entry.get(field) for field in BASE_FIELDS}
    for field in BASE_FIELDS:
        result[f"{field}_alt"] = entry.get(f"{field}{alt_suffix}")
    return result

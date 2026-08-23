"""Carga y normalizacion de los JSON de Cardmarket."""

import json
from pathlib import Path

from config import INVALID_DATE_SENTINEL, ONE_PIECE_CARD_NUMBER_RE, VARIANT_LABEL_RE


def load_products(path: Path) -> tuple[str, list[dict]]:
    """Devuelve (createdAt, products) de un products_singles_*.json."""
    data = json.loads(path.read_text())
    return data["createdAt"], data["products"]


def load_price_guide(path: Path) -> tuple[str, list[dict]]:
    """Devuelve (createdAt, priceGuides) de un price_guide_*.json."""
    data = json.loads(path.read_text())
    return data["createdAt"], data["priceGuides"]


def index_price_guide_by_product(price_guide_entries: list[dict]) -> dict[int, dict]:
    return {entry["idProduct"]: entry for entry in price_guide_entries}


def parse_date_added(raw: str | None) -> str | None:
    """El sentinel "0000-00-00 00:00:00" (visto en ~11.5% de productos de Pokemon) se
    trata como fecha invalida/nula."""
    if raw is None or raw == INVALID_DATE_SENTINEL:
        return None
    return raw


def parse_one_piece_name(raw_name: str) -> tuple[str | None, str]:
    """Extrae card_number del name crudo de One Piece: "Nombre (OP01-001)" -> ("OP01-001", "Nombre").

    Regex validado contra el archivo real completo de One Piece (12106 productos):
    matchea 11569 (95.6%). El resto son cartas "DON!!" (sin card number tradicional,
    esperado) y unos pocos nombres sin parentesis (inconsistencia real de datos de
    Cardmarket) -- en ambos casos se devuelve (None, raw_name) sin intentar forzar un match.
    """
    m = ONE_PIECE_CARD_NUMBER_RE.match(raw_name)
    if m:
        name, card_number = m.group(1), m.group(2)
        return card_number, name
    return None, raw_name


def extract_variant_label(raw_name: str) -> str | None:
    """Extrae el sufijo literal "(V.N)" del nombre si esta presente, para cualquier juego."""
    m = VARIANT_LABEL_RE.search(raw_name)
    return m.group(0) if m else None

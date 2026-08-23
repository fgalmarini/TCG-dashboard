"""Constantes centrales del importer: URLs, mapeos de ids, scope, regex."""

import re
from pathlib import Path

CARDMARKET_BASE_URL = "https://downloads.s3.cardmarket.com/productCatalog"
PRICE_HISTORY_DIR = Path(__file__).resolve().parent.parent.parent / "price-history"

# cardmarket_game_id: id de Cardmarket (usado en las URLs de descarga).
# local_game_id: id de la fila en la tabla local `games` (seed de backend/db/seed.sql).
# OJO: son namespaces distintos, no confundir.
GAMES = {
    "magic": {"cardmarket_game_id": 1, "local_game_id": 3, "folder": "magic"},
    "pokemon": {"cardmarket_game_id": 6, "local_game_id": 1, "folder": "pokemon"},
    "one_piece": {"cardmarket_game_id": 18, "local_game_id": 2, "folder": "one-piece"},
}

# Sufijo de precio "alternativo" (foil/holo) por juego, tal como aparece literal en price_guide.
ALT_SUFFIX = {"magic": "-foil", "one_piece": "-foil", "pokemon": "-holo"}

# Scope de carga a la DB por juego: None = todo el catálogo de singles;
# set[int] = solo esos idExpansion; "skip" = no cargar catálogo/precios (se descarga igual).
SCOPE = {
    "magic": {5285, 5308, 5396},
    "one_piece": None,
    "pokemon": "skip",
}

INVALID_DATE_SENTINEL = "0000-00-00 00:00:00"

# Diferencia relativa mínima entre el trend más alto y el segundo de un grupo de variantes
# para considerar que hay una sugerencia con sustento. Por debajo de esto (o si falta algún
# trend del grupo) se clasifica como 'other' en vez de forzar 'suggested_parallel'.
# No especificado en el contrato de Fase 4 -- valor elegido, documentado, ajustable.
AMBIGUITY_RELATIVE_THRESHOLD = 0.10

# Validado contra el archivo real de One Piece (12106 productos): matchea 11569 (95.6%).
# El resto son cartas "DON!!" (sin card number tradicional, esperado) y 6 casos de
# "Monkey.D.Luffy" sin parentesis (inconsistencia real de datos de Cardmarket).
ONE_PIECE_CARD_NUMBER_RE = re.compile(r"^(.*)\s\(([A-Z0-9-]+)\)$")

VARIANT_LABEL_RE = re.compile(r"\(V\.\d+\)")

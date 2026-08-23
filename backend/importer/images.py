"""Resolucion de imagenes on-demand (fase2-cardmarket-hallazgos-y-schema.md, seccion 4).

No se invocan en la corrida bulk del importer (seria innecesario resolver miles de
imagenes de cartas que el usuario nunca va a tener) -- quedan listas para que Fase 5
(colección manual) las dispare cuando una carta se agregue a collection_items/want_list_items.
Pokemon queda fuera (pospuesto, ver fase2 seccion 5).
"""

import json
import urllib.error
import urllib.request

SCRYFALL_TIMEOUT_SECONDS = 10


def resolve_one_piece_image_url(card_number: str) -> str:
    return f"https://en.onepiece-cardgame.com/images/cardlist/card/{card_number}.png"


def resolve_magic_image_url(cardmarket_id_product: int) -> str | None:
    """GET https://api.scryfall.com/cards/cardmarket/{idProduct} -> campo de imagen.

    Devuelve None si Scryfall no tiene el producto mapeado o la llamada falla --
    no silenciosamente: quien llame a esta funcion es responsable de reportarlo.
    """
    url = f"https://api.scryfall.com/cards/cardmarket/{cardmarket_id_product}"
    try:
        with urllib.request.urlopen(url, timeout=SCRYFALL_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None

    image_uris = data.get("image_uris")
    if image_uris:
        return image_uris.get("normal") or image_uris.get("large") or image_uris.get("small")

    # Cartas de dos caras: Scryfall las devuelve en card_faces, cada cara con su propia imagen.
    for face in data.get("card_faces", []):
        face_images = face.get("image_uris")
        if face_images:
            return face_images.get("normal") or face_images.get("large") or face_images.get("small")

    return None

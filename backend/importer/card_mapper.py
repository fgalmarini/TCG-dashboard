"""Creacion de cards con manejo explicito de la colision UNIQUE(expansion_id, card_number,
printing_variant).

Puede pasar si 2+ productos de un mismo grupo de variantes terminan con el mismo
printing_variant y el mismo card_number no-nulo (en Magic no ocurre porque card_number
siempre es NULL y SQLite no colisiona multiples NULL; en One Piece si es posible).
Se captura el IntegrityError puntual de ESE insert y se marca ese producto puntual como
'ambiguous' -- no aborta el resto de la corrida (regla AGENTS.md: nunca descartar
mappings fallidos en silencio).
"""

import sqlite3


def get_or_create_card(
    conn: sqlite3.Connection,
    game_id: int,
    expansion_id: int,
    card_number: str | None,
    name: str,
    printing_variant: str,
    variant_label: str | None,
    cardmarket_id_metacard: int | None,
) -> tuple[int | None, str, str | None]:
    """Devuelve (card_id, mapping_status, notes). mapping_status es 'mapped' o 'ambiguous'."""
    try:
        cur = conn.execute(
            """INSERT INTO cards
                 (game_id, expansion_id, card_number, name, printing_variant,
                  variant_label, cardmarket_id_metacard)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               RETURNING id""",
            (game_id, expansion_id, card_number, name, printing_variant, variant_label, cardmarket_id_metacard),
        )
        card_id = cur.fetchone()[0]
        return card_id, "mapped", None
    except sqlite3.IntegrityError as exc:
        # No conn.rollback() aca: por default SQLite solo revierte la sentencia que
        # violo el constraint, no toda la transaccion -- un rollback() del connection
        # completo descartaria tambien los inserts ya exitosos de este mismo run.
        notes = (
            f"UNIQUE(expansion_id={expansion_id}, card_number={card_number!r}, "
            f"printing_variant={printing_variant!r}) collision: {exc}"
        )
        return None, "ambiguous", notes

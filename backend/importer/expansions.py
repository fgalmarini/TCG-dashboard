"""Self-healing de expansions: cada idExpansion nuevo se inserta con name=NULL."""

import sqlite3


def get_or_create_expansion(
    conn: sqlite3.Connection,
    game_id: int,
    cardmarket_id_expansion: int,
    cache: dict[int, int],
    report,
    game_key: str,
) -> int:
    """cache: dict cardmarket_id_expansion -> local expansion id, para no repetir SELECTs
    dentro de una misma corrida (se pasa por referencia desde el orquestador)."""
    if cardmarket_id_expansion in cache:
        return cache[cardmarket_id_expansion]

    row = conn.execute(
        "SELECT id FROM expansions WHERE cardmarket_id_expansion = ?",
        (cardmarket_id_expansion,),
    ).fetchone()
    if row is not None:
        cache[cardmarket_id_expansion] = row[0]
        return row[0]

    cur = conn.execute(
        "INSERT INTO expansions (game_id, cardmarket_id_expansion, name) VALUES (?, ?, NULL)",
        (game_id, cardmarket_id_expansion),
    )
    new_id = cur.lastrowid
    cache[cardmarket_id_expansion] = new_id
    report.new_expansions.append((game_key, cardmarket_id_expansion))
    return new_id

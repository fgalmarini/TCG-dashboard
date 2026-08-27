"""Wishlist read/write API.  Collection editing remains outside this router."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status

from ..db import get_db
from ..queries import fetch_wishlist_row, fetch_wishlist_rows
from ..schemas import WishlistCreateIn, WishlistItemOut, WishlistListResponse, WishlistUpdateIn


router = APIRouter(prefix="/api", tags=["wishlist"])


def ensure_catalog_card(conn: sqlite3.Connection, card_id: int) -> None:
    row = conn.execute(
        """SELECT c.id FROM cards c JOIN games g ON g.id=c.game_id
            WHERE c.id=? AND g.code='magic' AND lower(c.set_code) IN ('ltr','ltc')""",
        (card_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Carta LOTR no encontrada en el catálogo")


@router.get("/wishlist", response_model=WishlistListResponse)
def list_wishlist(
    status: str = "wanted",
    conn: sqlite3.Connection = Depends(get_db),
) -> WishlistListResponse:
    if status not in {"wanted", "acquired", "removed"}:
        raise HTTPException(status_code=400, detail="status inválido")
    return WishlistListResponse(
        items=[WishlistItemOut.from_row(row) for row in fetch_wishlist_rows(conn, status)]
    )


@router.post("/wishlist", response_model=WishlistItemOut, status_code=http_status.HTTP_201_CREATED)
def create_wishlist_item(
    payload: WishlistCreateIn,
    conn: sqlite3.Connection = Depends(get_db),
) -> WishlistItemOut:
    ensure_catalog_card(conn, payload.card_id)
    existing = conn.execute(
        "SELECT id FROM wishlist_items WHERE card_id=? AND status='wanted'",
        (payload.card_id,),
    ).fetchone()
    if existing:
        row = fetch_wishlist_row(conn, existing[0])
        assert row is not None
        return WishlistItemOut.from_row(row)
    cursor = conn.execute(
        """INSERT INTO wishlist_items
           (card_id, quantity_wanted, priority, max_price, currency, notes, status,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'wanted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
        (payload.card_id, payload.quantity_wanted, payload.priority, payload.max_price,
         payload.currency, payload.notes),
    )
    conn.commit()
    row = fetch_wishlist_row(conn, cursor.lastrowid)
    assert row is not None
    return WishlistItemOut.from_row(row)


@router.patch("/wishlist/{item_id}", response_model=WishlistItemOut)
def update_wishlist_item(
    item_id: int,
    payload: WishlistUpdateIn,
    conn: sqlite3.Connection = Depends(get_db),
) -> WishlistItemOut:
    current = conn.execute(
        "SELECT id, status FROM wishlist_items WHERE id=?", (item_id,)
    ).fetchone()
    if current is None:
        raise HTTPException(status_code=404, detail="Wishlist item no encontrado")
    if current["status"] != "wanted":
        raise HTTPException(status_code=409, detail="Solo los items wanted se editan desde esta API")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        row = fetch_wishlist_row(conn, item_id)
        assert row is not None
        return WishlistItemOut.from_row(row)
    assignments = [f"{key}=?" for key in updates]
    values = list(updates.values())
    assignments.append("updated_at=CURRENT_TIMESTAMP")
    conn.execute(
        f"UPDATE wishlist_items SET {', '.join(assignments)} WHERE id=?",
        [*values, item_id],
    )
    conn.commit()
    row = fetch_wishlist_row(conn, item_id)
    assert row is not None
    return WishlistItemOut.from_row(row)


@router.delete("/wishlist/{item_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def remove_wishlist_item(item_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    cursor = conn.execute(
        "UPDATE wishlist_items SET status='removed', updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='wanted'",
        (item_id,),
    )
    if cursor.rowcount == 0:
        exists = conn.execute("SELECT 1 FROM wishlist_items WHERE id=?", (item_id,)).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="Wishlist item no encontrado")
    conn.commit()
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post("/wishlist/{item_id}/move-to-collection", response_model=WishlistItemOut)
def move_to_collection(item_id: int, conn: sqlite3.Connection = Depends(get_db)) -> WishlistItemOut:
    row = conn.execute(
        "SELECT card_id, quantity_wanted, status FROM wishlist_items WHERE id=?", (item_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Wishlist item no encontrado")
    if row["status"] != "wanted":
        raise HTTPException(status_code=409, detail="El wishlist item ya no está wanted")
    try:
        conn.execute("BEGIN")
        collection = conn.execute(
            """SELECT id FROM collection_items
                WHERE card_id=? AND language_id=COALESCE(
                    (SELECT language_id FROM cards WHERE id=?), 1)
                ORDER BY id LIMIT 1""",
            (row["card_id"], row["card_id"]),
        ).fetchone()
        if collection:
            conn.execute(
                "UPDATE collection_items SET quantity=quantity+? WHERE id=?",
                (row["quantity_wanted"], collection[0]),
            )
        else:
            conn.execute(
                """INSERT INTO collection_items
                   (card_id, language_id, quantity, status, manual_entry)
                   VALUES (?, COALESCE((SELECT language_id FROM cards WHERE id=?), 1), ?, 'KEEP', 0)""",
                (row["card_id"], row["card_id"], row["quantity_wanted"]),
            )
        conn.execute(
            "UPDATE wishlist_items SET status='acquired', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (item_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    result = fetch_wishlist_row(conn, item_id)
    assert result is not None
    return WishlistItemOut.from_row(result)

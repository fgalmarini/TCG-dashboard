"""Wishlist planning API. Collection remains independent from acquired wishlist rows."""

import csv
import io
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status as http_status

from ..db import get_db
from ..queries import fetch_wishlist_row, fetch_wishlist_rows, fetch_wishlist_summary
from ..schemas import (
    WishlistCreateIn,
    WishlistItemOut,
    WishlistListResponse,
    WishlistSummaryOut,
    WishlistUpdateIn,
)


router = APIRouter(prefix="/api", tags=["wishlist"])


def ensure_catalog_card(conn: sqlite3.Connection, card_id: int) -> sqlite3.Row:
    row = conn.execute(
        """SELECT c.id, c.language_id, g.code AS game_code
             FROM cards c JOIN games g ON g.id=c.game_id
            WHERE c.id=? AND (
                c.catalog_status='active' OR (
                    g.code='magic' AND lower(c.set_code) IN ('ltr','ltc') AND c.finish IS NOT NULL
                )
            )""",
        (card_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Printing no encontrado en el catálogo")
    if row["game_code"] == "one_piece" and row["language_id"] is None:
        raise HTTPException(status_code=409, detail="One Piece requiere idioma exacto")
    return row


def comma_values(value: str | None) -> list[str] | None:
    values = [part.strip().casefold() for part in (value or "").split(",") if part.strip()]
    return values or None


def wishlist_response(conn: sqlite3.Connection, rows) -> WishlistListResponse:
    summary = fetch_wishlist_summary(conn)
    return WishlistListResponse(
        items=[WishlistItemOut.from_row(row) for row in rows],
        total=len(rows),
        summary=WishlistSummaryOut(
            wanted=summary.wanted,
            acquired=summary.acquired,
            missing_price=summary.missing_price,
            unmatched=summary.unmatched,
            estimated_total=summary.estimated_total,
        ),
    )


@router.get("/wishlist", response_model=WishlistListResponse)
def list_wishlist(
    status: str = Query("wanted", pattern="^(wanted|acquired|removed|all)$"),
    priority: str | None = None,
    sets: str | None = None,
    game: str | None = None,
    language: str | None = None,
    finish: str | None = Query(None, pattern="^(nonfoil|foil|etched)$"),
    has_price: bool | None = None,
    matched: bool | None = None,
    sort: str = Query("priority", pattern="^(priority|name|current_price|target_price|max_price)$"),
    conn: sqlite3.Connection = Depends(get_db),
) -> WishlistListResponse:
    rows = fetch_wishlist_rows(
        conn,
        status=status,
        priorities=comma_values(priority),
        sets=comma_values(sets),
        finish=finish,
        has_price=has_price,
        matched=matched,
        game=game,
        language=language,
        sort=sort,
    )
    return wishlist_response(conn, rows)


@router.post("/wishlist", response_model=WishlistItemOut, status_code=http_status.HTTP_201_CREATED)
def create_wishlist_item(
    payload: WishlistCreateIn,
    conn: sqlite3.Connection = Depends(get_db),
) -> WishlistItemOut:
    card = ensure_catalog_card(conn, payload.card_id)
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
           (card_id, language_id, quantity_wanted, priority, target_price, max_price, currency, notes, status,
            acquired_at, removed_at, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'wanted', NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
        (payload.card_id, card["language_id"], payload.quantity_wanted, payload.priority, payload.target_price,
         payload.max_price, payload.currency, payload.notes),
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
        "SELECT id, status, target_price, max_price FROM wishlist_items WHERE id=?", (item_id,)
    ).fetchone()
    if current is None:
        raise HTTPException(status_code=404, detail="Wishlist item no encontrado")
    updates = payload.model_dump(exclude_unset=True)
    target_price = updates.get("target_price", current["target_price"])
    max_price = updates.get("max_price", current["max_price"])
    if target_price is not None and max_price is not None and target_price > max_price:
        raise HTTPException(status_code=422, detail="target_price no puede ser mayor que max_price")
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
    row = conn.execute("SELECT status FROM wishlist_items WHERE id=?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Wishlist item no encontrado")
    if row["status"] != "wanted":
        raise HTTPException(status_code=409, detail="Solo los items wanted se pueden remover")
    conn.execute(
        """UPDATE wishlist_items
              SET status='removed', acquired_at=NULL, removed_at=CURRENT_TIMESTAMP,
                  updated_at=CURRENT_TIMESTAMP
            WHERE id=?""",
        (item_id,),
    )
    conn.commit()
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


def transition_wishlist_item(
    item_id: int,
    expected_status: str,
    new_status: str,
    conn: sqlite3.Connection,
) -> WishlistItemOut:
    row = conn.execute("SELECT status FROM wishlist_items WHERE id=?", (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Wishlist item no encontrado")
    if row["status"] != expected_status:
        raise HTTPException(status_code=409, detail=f"Transición inválida desde {row['status']}")
    if new_status == "acquired":
        sql = """UPDATE wishlist_items
                    SET status='acquired', acquired_at=CURRENT_TIMESTAMP,
                        removed_at=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?"""
    else:
        sql = """UPDATE wishlist_items
                    SET status='wanted', acquired_at=NULL,
                        removed_at=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?"""
    conn.execute(sql, (item_id,))
    conn.commit()
    result = fetch_wishlist_row(conn, item_id)
    assert result is not None
    return WishlistItemOut.from_row(result)


@router.post("/wishlist/{item_id}/mark-acquired", response_model=WishlistItemOut)
def mark_acquired(item_id: int, conn: sqlite3.Connection = Depends(get_db)) -> WishlistItemOut:
    return transition_wishlist_item(item_id, "wanted", "acquired", conn)


@router.post("/wishlist/{item_id}/restore", response_model=WishlistItemOut)
def restore_wishlist_item(item_id: int, conn: sqlite3.Connection = Depends(get_db)) -> WishlistItemOut:
    row = conn.execute(
        "SELECT status, card_id FROM wishlist_items WHERE id=?", (item_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Wishlist item no encontrado")
    if row["status"] not in {"acquired", "removed"}:
        raise HTTPException(status_code=409, detail="Solo los items históricos se pueden restaurar")
    duplicate = conn.execute(
        "SELECT 1 FROM wishlist_items WHERE card_id=? AND status='wanted' AND id<>?",
        (row["card_id"], item_id),
    ).fetchone()
    if duplicate:
        raise HTTPException(status_code=409, detail="Ya existe un wishlist item wanted para esta carta")
    return transition_wishlist_item(item_id, row["status"], "wanted", conn)


@router.get("/wishlist/export.csv")
def export_wishlist(
    status: str = Query("wanted", pattern="^(wanted|acquired|removed|all)$"),
    priority: str | None = None,
    sets: str | None = None,
    game: str | None = None,
    language: str | None = None,
    finish: str | None = Query(None, pattern="^(nonfoil|foil|etched)$"),
    has_price: bool | None = None,
    matched: bool | None = None,
    sort: str = Query("priority", pattern="^(priority|name|current_price|target_price|max_price)$"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    rows = fetch_wishlist_rows(
        conn,
        status=status,
        priorities=comma_values(priority),
        sets=comma_values(sets),
        finish=finish,
        has_price=has_price,
        matched=matched,
        game=game,
        language=language,
        sort=sort,
    )
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "game", "name", "set", "collector_number", "treatment", "finish", "language",
        "priority", "current_price", "current_price_currency", "target_price", "max_price",
        "status", "source", "resolution_method",
    ])
    for row in rows:
        writer.writerow([
            row.game_code, row.name, row.set_code or "", row.card_number or "", row.treatment or "",
            row.finish or "", row.language or "", row.priority,
            row.current_price if row.current_price is not None else "",
            row.price_currency or "",
            row.target_price if row.target_price is not None else "",
            row.max_price if row.max_price is not None else "", row.status, row.source or "",
            row.resolution_method or "",
        ])
    return Response(
        content=output.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=wishlist.csv"},
    )

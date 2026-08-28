"""GET /api/collection, GET /api/collection/{id} -- ver
fase6-dashboard-basico-sprint-contract.md seccion 3. Solo lectura."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..db import get_db
from ..queries import (
    build_collection_filters,
    build_order_by,
    count_collection_rows,
    fetch_collection_match_context,
    fetch_collection_row_by_id,
    fetch_collection_rows,
)
from ..schemas import (
    CollectionItemDetailOut,
    CollectionItemOut,
    CollectionListResponse,
    CollectionMatchContextOut,
    ResolveMatchIn,
    AddToCollectionIn,
)

router = APIRouter(prefix="/api", tags=["collection"])


@router.get("/collection", response_model=CollectionListResponse)
def list_collection(
    game: str | None = None,
    language: str | None = None,
    status: str | None = None,
    search: str | None = None,
    sort: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> CollectionListResponse:
    where_sql, params = build_collection_filters(
        game=game, language=language, status=status, search=search
    )
    order_by_sql = build_order_by(sort)

    total = count_collection_rows(conn, where_sql, params)
    offset = (page - 1) * page_size
    rows = fetch_collection_rows(
        conn,
        where_sql=where_sql,
        where_params=params,
        order_by_sql=order_by_sql,
        limit=page_size,
        offset=offset,
        include_images=True,
    )

    return CollectionListResponse(
        items=[CollectionItemOut.from_row(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/collection/{item_id}/match-candidates", response_model=CollectionMatchContextOut)
def get_match_candidates(
    item_id: int,
    search: str | None = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> CollectionMatchContextOut:
    context = fetch_collection_match_context(conn, item_id, search)
    if context is None:
        raise HTTPException(status_code=404, detail=f"collection_items.id={item_id} no encontrado")
    return CollectionMatchContextOut.from_data(context)


@router.post("/collection/{item_id}/resolve-match", response_model=CollectionItemDetailOut)
def resolve_match(
    item_id: int,
    payload: ResolveMatchIn,
    conn: sqlite3.Connection = Depends(get_db),
) -> CollectionItemDetailOut:
    current = conn.execute(
        """SELECT ci.id, ci.card_id, ci.cardmarket_product_id,
                  CASE WHEN g.code='magic'
                            AND lower(COALESCE(c.set_code, e.set_code)) IN ('ltr', 'ltc')
                            AND c.card_number IS NOT NULL AND c.finish IS NOT NULL
                       THEN 1 ELSE 0 END AS catalog_matched
             FROM collection_items ci
             LEFT JOIN cards c ON c.id=ci.card_id
             LEFT JOIN expansions e ON e.id=c.expansion_id
             LEFT JOIN games g ON g.id=c.game_id
            WHERE ci.id=?""",
        (item_id,),
    ).fetchone()
    if current is None:
        raise HTTPException(status_code=404, detail=f"collection_items.id={item_id} no encontrado")
    if current["catalog_matched"]:
        raise HTTPException(status_code=409, detail="La fila ya está asociada a una card canónica")

    candidate = conn.execute(
        """SELECT c.id FROM cards c
             JOIN expansions e ON e.id=c.expansion_id
             JOIN games g ON g.id=c.game_id
            WHERE c.id=? AND g.code='magic'
              AND lower(COALESCE(c.set_code, e.set_code)) IN ('ltr', 'ltc')
              AND c.card_number IS NOT NULL AND c.finish IS NOT NULL""",
        (payload.card_id,),
    ).fetchone()
    if candidate is None:
        raise HTTPException(status_code=404, detail="El candidato no pertenece al catálogo físico LOTR")

    product_id = current["cardmarket_product_id"]
    mapping = None
    other_rows = 0
    if product_id is not None:
        mapping = conn.execute(
            "SELECT id, card_id, status FROM cardmarket_product_mappings WHERE cardmarket_product_id=?",
            (product_id,),
        ).fetchone()
        other_rows = conn.execute(
            "SELECT COUNT(*) FROM collection_items WHERE cardmarket_product_id=? AND id<>?",
            (product_id, item_id),
        ).fetchone()[0]

    try:
        conn.execute("BEGIN")
        conn.execute("UPDATE collection_items SET card_id=?, finish=COALESCE(?, finish), treatment=COALESCE(?, treatment), match_status='exact', match_quality='manual', match_reason=? WHERE id=?", (payload.card_id, payload.finish, payload.treatment, 'manual_selection', item_id))
        if (
            mapping is not None
            and mapping["status"] == "mapped"
            and mapping["card_id"] == current["card_id"]
            and other_rows == 0
        ):
            conn.execute(
                "UPDATE cardmarket_product_mappings SET card_id=? WHERE id=?",
                (payload.card_id, mapping["id"]),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    result = fetch_collection_row_by_id(conn, item_id)
    assert result is not None
    return CollectionItemDetailOut.from_row(result)

@router.post("/collection", response_model=CollectionItemDetailOut, status_code=201)
def add_collection(payload: AddToCollectionIn, conn: sqlite3.Connection = Depends(get_db)) -> CollectionItemDetailOut:
    card = conn.execute("SELECT id, language_id, finish, treatment FROM cards WHERE id=? AND catalog_status='active'", (payload.card_id,)).fetchone()
    if card is None: raise HTTPException(status_code=404, detail="Printing no encontrado en el catálogo activo")
    if payload.finish and payload.finish != card["finish"]: raise HTTPException(status_code=422, detail="Finish incompatible con el printing")
    existing = conn.execute("SELECT id FROM collection_items WHERE card_id=? AND language_id=? AND status='KEEP'", (payload.card_id, card["language_id"] or 1)).fetchone()
    if existing:
        conn.execute("UPDATE collection_items SET quantity=quantity+? WHERE id=?", (payload.quantity, existing["id"])); item_id=existing["id"]
    else:
        cur=conn.execute("INSERT INTO collection_items(card_id,language_id,quantity,status,match_status,match_quality,match_reason) VALUES(?,?,?,'KEEP','exact','exact','catalog_add')", (payload.card_id, card["language_id"] or 1, payload.quantity)); item_id=cur.lastrowid
    conn.commit(); result=fetch_collection_row_by_id(conn,item_id); assert result is not None; return CollectionItemDetailOut.from_row(result)


@router.get("/collection/{item_id}", response_model=CollectionItemDetailOut)
def get_collection_item(item_id: int, conn: sqlite3.Connection = Depends(get_db)) -> CollectionItemDetailOut:
    row = fetch_collection_row_by_id(conn, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"collection_items.id={item_id} no encontrado")
    return CollectionItemDetailOut.from_row(row)

@router.delete("/collection/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_collection_item(item_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    exists = conn.execute("SELECT 1 FROM collection_items WHERE id=?", (item_id,)).fetchone()
    if exists is None:
        raise HTTPException(status_code=404, detail=f"collection_items.id={item_id} no encontrado")
    conn.execute("DELETE FROM collection_items WHERE id=?", (item_id,))
    conn.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

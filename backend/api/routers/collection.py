"""GET /api/collection, GET /api/collection/{id} -- ver
fase6-dashboard-basico-sprint-contract.md seccion 3. Solo lectura."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import get_db
from ..queries import (
    build_collection_filters,
    build_order_by,
    count_collection_rows,
    fetch_collection_row_by_id,
    fetch_collection_rows,
)
from ..schemas import CollectionItemDetailOut, CollectionItemOut, CollectionListResponse

router = APIRouter(prefix="/api", tags=["collection"])


@router.get("/collection", response_model=CollectionListResponse)
def list_collection(
    game: str | None = None,
    status: str | None = None,
    search: str | None = None,
    sort: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> CollectionListResponse:
    where_sql, params = build_collection_filters(game=game, status=status, search=search)
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


@router.get("/collection/{item_id}", response_model=CollectionItemDetailOut)
def get_collection_item(item_id: int, conn: sqlite3.Connection = Depends(get_db)) -> CollectionItemDetailOut:
    row = fetch_collection_row_by_id(conn, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"collection_items.id={item_id} no encontrado")
    return CollectionItemDetailOut.from_row(row)

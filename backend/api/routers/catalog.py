"""Read-only catalog browsing for physical Magic LOTR cards."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from ..db import get_db
from ..queries import build_catalog_filters, count_catalog_rows, fetch_catalog_rows
from ..schemas import CatalogItemOut, CatalogListResponse


router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog", response_model=CatalogListResponse)
def list_catalog(
    game: str = "magic",
    sets: str | None = None,
    search: str | None = None,
    ownership: str | None = Query(None, pattern="^(owned|not_owned|wishlist)$"),
    rarity: str | None = None,
    finish: str | None = Query(None, pattern="^(nonfoil|foil|etched)$"),
    treatment: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> CatalogListResponse:
    set_values = [value.strip().casefold() for value in (sets or "").split(",") if value.strip()]
    where_sql, params = build_catalog_filters(
        game=game, sets=set_values or None, search=search, ownership=ownership,
        rarity=rarity, finish=finish, treatment=treatment,
    )
    total = count_catalog_rows(conn, where_sql, params)
    offset = (page - 1) * page_size
    rows = fetch_catalog_rows(conn, where_sql, params, page_size, offset)
    return CatalogListResponse(
        items=[CatalogItemOut.from_row(row) for row in rows],
        total=total, page=page, page_size=page_size,
    )

"""Read-only catalog browsing for physical Magic LOTR cards."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from ..db import get_db
from ..queries import (
    build_catalog_filters,
    count_catalog_identities,
    count_catalog_rows,
    fetch_catalog_detail,
    fetch_catalog_options,
    fetch_catalog_rows,
)
from ..schemas import (
    CatalogDetailResponse,
    CatalogItemOut,
    CatalogListResponse,
    CatalogOptionsResponse,
)


router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog", response_model=CatalogListResponse)
def list_catalog(
    game: str = "magic",
    language: str | None = None,
    sets: str | None = None,
    search: str | None = None,
    ownership: str | None = Query(None, pattern="^(owned|not_owned|wishlist)$"),
    rarity: str | None = None,
    finish: str | None = Query(None, pattern="^(nonfoil|foil|etched|normal|holo|reverse_holo)$"),
    treatment: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> CatalogListResponse:
    set_values = [value.strip().casefold() for value in (sets or "").split(",") if value.strip()]
    where_sql, params = build_catalog_filters(
        game=game, language=language, sets=set_values or None, search=search, ownership=ownership,
        rarity=rarity, finish=finish, treatment=treatment,
    )
    total = count_catalog_rows(conn, where_sql, params)
    identity_total = count_catalog_identities(conn, where_sql, params)
    offset = (page - 1) * page_size
    rows = fetch_catalog_rows(conn, where_sql, params, page_size, offset)
    return CatalogListResponse(
        items=[CatalogItemOut.from_row(row) for row in rows],
        total=total, identity_total=identity_total, page=page, page_size=page_size,
    )


@router.get("/catalog/options", response_model=CatalogOptionsResponse)
def catalog_options(
    game: str | None = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> CatalogOptionsResponse:
    return CatalogOptionsResponse(**fetch_catalog_options(conn, game))


@router.get("/catalog/{card_id}", response_model=CatalogDetailResponse)
def catalog_detail(
    card_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> CatalogDetailResponse:
    result = fetch_catalog_detail(conn, card_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Printing no encontrado")
    printing, related = result
    return CatalogDetailResponse(
        printing=CatalogItemOut.from_row(printing),
        printings=[CatalogItemOut.from_row(row) for row in related],
    )

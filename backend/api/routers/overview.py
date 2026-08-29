"""GET /api/overview -- ver fase6-dashboard-basico-sprint-contract.md seccion 3."""

import sqlite3

from fastapi import APIRouter, Depends

from ..db import get_db
from ..queries import compute_overview
from ..schemas import CardsWithoutMarketValue, OverviewResponse, TcgBucket, TopCardOut

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview", response_model=OverviewResponse)
def get_overview(conn: sqlite3.Connection = Depends(get_db)) -> OverviewResponse:
    data = compute_overview(conn)
    return OverviewResponse(
        total_cost=data.total_cost,
        cost_basis_row_count=data.cost_basis_row_count,
        rows_without_cost=data.rows_without_cost,
        total_market_value=data.total_market_value,
        market_value_row_count=data.market_value_row_count,
        unrealized_pl=data.unrealized_pl,
        roi=data.roi,
        total_cards=data.total_cards,
        unique_cards=data.unique_cards,
        cards_without_market_value=CardsWithoutMarketValue(
            count=data.cards_without_market_value_count,
            ids=data.cards_without_market_value_ids,
        ),
        value_by_tcg={key: TcgBucket.from_data(bucket) for key, bucket in data.value_by_tcg.items()},
        top_cards=[TopCardOut.from_row(row) for row in data.top_cards],
    )

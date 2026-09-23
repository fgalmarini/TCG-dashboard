"""Reusable event-to-Wishlist association API."""
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from ..db import get_db
from ..queries import fetch_wishlist_rows
from ..schemas import WishlistItemOut

router = APIRouter(prefix="/api/events", tags=["events"])


class EventWishlistLinkIn(BaseModel):
    wishlist_item_id: int


@router.get("/{event_code}/wishlist")
def get_event_wishlist(event_code: str, conn: sqlite3.Connection = Depends(get_db)):
    event = conn.execute("SELECT id FROM events WHERE code=?", (event_code,)).fetchone()
    if event is None:
        raise HTTPException(404, "Event not found")
    rows = fetch_wishlist_rows(conn, status=None, sort="priority")
    linked = {r[0] for r in conn.execute("SELECT wishlist_item_id FROM event_wishlist_items WHERE event_id=?", (event[0],))}
    result=[]
    for row in rows:
        if row.id not in linked: continue
        card=conn.execute("""SELECT c.canonical_card_id,c.set_id,c.language_id,c.treatment,c.set_code,c.card_number
                               FROM cards c WHERE c.id=?""",(row.card_id,)).fetchone()
        prices={r[0]:r[1] for r in conn.execute("""SELECT metric,value FROM market_price_observations
          WHERE card_id=? AND provider='cardmarket_manual' AND market='cardmarket' AND currency='EUR'
            AND snapshot_key='cardmadness-2026-09-23'""",(row.card_id,))}
        alternative=None
        if card and card[3] == "surge_foil" and card[0] is not None and card[1] is not None and card[2] is not None:
            candidates=conn.execute("""SELECT id,card_number FROM cards WHERE canonical_card_id=? AND set_id=?
                AND language_id=? AND treatment='traditional_foil' AND finish='foil' AND lower(set_code) IN ('hob','hoc')""",
                (card[0],card[1],card[2])).fetchall()
            if len(candidates)==1:
                alt=candidates[0]
                value=conn.execute("""SELECT value FROM market_price_observations WHERE card_id=? AND provider='cardmarket_manual'
                    AND market='cardmarket' AND metric='low' AND currency='EUR' AND snapshot_key='cardmadness-2026-09-23'""",(alt[0],)).fetchone()
                alternative={"card_id":alt[0],"card_number":alt[1],"low":value[0] if value else None}
        result.append({"wishlist_item":WishlistItemOut.from_row(row).model_dump(),"target_prices":prices,"traditional_foil":alternative})
    return {"event_code":event_code,"items":result}


@router.post("/{event_code}/wishlist", status_code=status.HTTP_204_NO_CONTENT)
def add_event_wishlist_item(event_code: str, payload: EventWishlistLinkIn, conn: sqlite3.Connection = Depends(get_db)):
    event=conn.execute("SELECT id FROM events WHERE code=?",(event_code,)).fetchone()
    if event is None: raise HTTPException(404,"Event not found")
    if conn.execute("SELECT 1 FROM wishlist_items WHERE id=?",(payload.wishlist_item_id,)).fetchone() is None:
        raise HTTPException(404,"Wishlist item not found")
    conn.execute("INSERT OR IGNORE INTO event_wishlist_items(event_id,wishlist_item_id) VALUES(?,?)",(event[0],payload.wishlist_item_id))
    conn.commit()
    return Response(status_code=204)


@router.delete("/{event_code}/wishlist/{wishlist_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_wishlist_item(event_code: str, wishlist_item_id: int, conn: sqlite3.Connection = Depends(get_db)):
    event=conn.execute("SELECT id FROM events WHERE code=?",(event_code,)).fetchone()
    if event is None: raise HTTPException(404,"Event not found")
    conn.execute("DELETE FROM event_wishlist_items WHERE event_id=? AND wishlist_item_id=?",(event[0],wishlist_item_id))
    conn.commit()
    return Response(status_code=204)

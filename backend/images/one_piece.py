"""Deterministic One Piece display-image fallback matching.

This module never changes card identity or pricing. It only finds an already
stored English image that can safely be displayed for a Japanese printing.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class OnePieceImageCandidate:
    jp_card_id: int
    en_card_id: int
    source: str
    source_card_id: str | None
    source_variant: str | None
    source_collector_number: str | None
    small_url: str | None
    large_url: str | None
    match_method: str


@dataclass(frozen=True)
class OnePieceImageDecision:
    jp_card_id: int
    status: str
    candidate: OnePieceImageCandidate | None = None
    reason: str | None = None


def _image_language(row: sqlite3.Row) -> str | None:
    scope = row["image_language_scope"]
    return scope if scope not in (None, "unknown") else row["image_language"]


def _identity(row: sqlite3.Row) -> tuple | None:
    values = (
        row["canonical_card_id"], row["set_id"], row["card_number"],
        row["release_kind"], row["art_kind"], row["source_variant"],
    )
    if any(value is None or str(value).strip() == "" for value in values):
        return None
    if str(row["source_variant"]).strip().casefold() in {"unknown", "<null>"}:
        return None
    return values


def _printing_rows(conn: sqlite3.Connection, language: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT c.id, c.card_number, c.canonical_card_id, c.set_id,
                      c.release_kind, c.art_kind, c.source_variant,
                      pei.external_id AS blueprint_id
                 FROM cards c
                 JOIN games g ON g.id=c.game_id
                 JOIN languages l ON l.id=c.language_id
                 LEFT JOIN printing_external_ids pei
                        ON pei.card_id=c.id
                       AND pei.source='cardtrader_blueprint'
                       AND pei.language_scope='exact'
                WHERE g.code='one_piece' AND l.code=? AND c.catalog_status='active'
                ORDER BY c.id""",
        (language,),
    ).fetchall()


def _english_images(conn: sqlite3.Connection) -> dict[int, list[sqlite3.Row]]:
    rows = conn.execute(
        """SELECT ci.card_id, ci.source, ci.source_card_id, ci.source_variant,
                      ci.source_collector_number, ci.language AS image_language,
                      ci.image_language_scope, ci.image_url_small, ci.image_url_large,
                      ci.is_language_fallback
                 FROM card_images ci
                WHERE ci.language='en' AND ci.status='resolved'
                  AND ci.match_quality='exact'
                  AND ci.is_language_fallback=0
                  AND (ci.image_url_small IS NOT NULL OR ci.image_url_large IS NOT NULL)
                ORDER BY ci.card_id, ci.source, ci.face_index"""
    ).fetchall()
    by_card: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        if _image_language(row) != "en":
            continue
        by_card.setdefault(row["card_id"], []).append(row)
    return by_card


def find_fallback_decisions(conn: sqlite3.Connection) -> list[OnePieceImageDecision]:
    """Find one safe EN image decision per active JP printing.

    A shared CardTrader Blueprint is strongest, but it is accepted only when the
    catalog identity also agrees whenever that identity is complete. The fallback
    is rejected if either side has multiple possible cards or image rows.
    """
    jp_rows = _printing_rows(conn, "jp")
    en_rows = _printing_rows(conn, "en")
    en_by_blueprint: dict[str, list[sqlite3.Row]] = {}
    en_by_identity: dict[tuple, list[sqlite3.Row]] = {}
    for row in en_rows:
        if row["blueprint_id"] is not None:
            en_by_blueprint.setdefault(str(row["blueprint_id"]), []).append(row)
        identity = _identity(row)
        if identity is not None:
            en_by_identity.setdefault(identity, []).append(row)
    image_by_card = _english_images(conn)

    decisions: list[OnePieceImageDecision] = []
    for jp in jp_rows:
        jp_id = int(jp["id"])
        existing = conn.execute(
            """SELECT status, match_quality, is_language_fallback,
                              image_url_small, image_url_large
                         FROM card_images
                        WHERE card_id=? AND language='jp' AND face_index=0
                        ORDER BY CASE WHEN status='resolved' THEN 0 ELSE 1 END, id
                        LIMIT 1""",
            (jp_id,),
        ).fetchone()
        if existing and existing["status"] == "resolved" and not existing["is_language_fallback"] and existing["match_quality"] == "exact" and (existing["image_url_small"] or existing["image_url_large"]):
            decisions.append(OnePieceImageDecision(jp_id, "exact_exists", reason="exact JP image already exists"))
            continue
        if existing and existing["status"] == "resolved" and existing["is_language_fallback"] and existing["match_quality"] == "exact" and (existing["image_url_small"] or existing["image_url_large"]):
            decisions.append(OnePieceImageDecision(jp_id, "fallback_exists", reason="visual fallback already exists"))
            continue
        if existing and existing["status"] not in {"missing", None}:
            decisions.append(OnePieceImageDecision(jp_id, "ambiguous", reason=f"existing image status={existing['status']}"))
            continue

        matches: list[sqlite3.Row] = []
        method = None
        if jp["blueprint_id"] is not None:
            blueprint_matches = en_by_blueprint.get(str(jp["blueprint_id"]), [])
            if len(blueprint_matches) == 1:
                matches = blueprint_matches
                method = "shared_cardtrader_blueprint"
            elif len(blueprint_matches) > 1:
                decisions.append(OnePieceImageDecision(jp_id, "ambiguous", reason="multiple EN printings share the Blueprint"))
                continue

        if not matches:
            identity = _identity(jp)
            if identity is None:
                decisions.append(OnePieceImageDecision(jp_id, "missing", reason="identity incomplete or source_variant unknown"))
                continue
            identity_matches = en_by_identity.get(identity, [])
            if len(identity_matches) != 1:
                decisions.append(OnePieceImageDecision(jp_id, "ambiguous" if identity_matches else "missing", reason="composite printing identity is not unique"))
                continue
            matches = identity_matches
            method = "unique_composite_printing_identity"

        en = matches[0]
        if _identity(jp) is not None and _identity(en) is not None and _identity(jp) != _identity(en):
            decisions.append(OnePieceImageDecision(jp_id, "ambiguous", reason="Blueprint and printing identity disagree"))
            continue
        images = image_by_card.get(int(en["id"]), [])
        if len(images) != 1:
            decisions.append(OnePieceImageDecision(jp_id, "ambiguous" if images else "missing", reason="English printing has zero or multiple usable images"))
            continue
        image = images[0]
        decisions.append(OnePieceImageDecision(
            jp_id,
            "fallback",
            OnePieceImageCandidate(
                jp_card_id=jp_id,
                en_card_id=int(en["id"]),
                source=image["source"],
                source_card_id=image["source_card_id"],
                source_variant=image["source_variant"] or en["source_variant"],
                source_collector_number=image["source_collector_number"],
                small_url=image["image_url_small"],
                large_url=image["image_url_large"],
                match_method=method or "unknown",
            ),
        ))
    return decisions

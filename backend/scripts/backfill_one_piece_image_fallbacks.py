"""Backfill safe English display fallbacks for missing One Piece JP images."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.images.one_piece import OnePieceImageDecision, find_fallback_decisions

DB_PATH = REPO_ROOT / "backend" / "db" / "tcg_dashboard.db"


def ensure_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(card_images)")}
    if "image_language_scope" not in columns:
        conn.execute("ALTER TABLE card_images ADD COLUMN image_language_scope TEXT NOT NULL DEFAULT 'unknown'")
    if "is_language_fallback" not in columns:
        conn.execute("ALTER TABLE card_images ADD COLUMN is_language_fallback INTEGER NOT NULL DEFAULT 0")


def initialize_existing_exact_scopes(conn: sqlite3.Connection) -> int:
    """Mark already-resolved non-fallback assets with their actual stored language."""
    cursor = conn.execute(
        """UPDATE card_images
              SET image_language_scope=lower(language)
            WHERE status='resolved'
              AND is_language_fallback=0
              AND language IS NOT NULL
              AND lower(language) NOT IN ('', 'unknown')
              AND (image_language_scope IS NULL OR image_language_scope='unknown')"""
    )
    return cursor.rowcount


def upsert_fallback(conn: sqlite3.Connection, decision: OnePieceImageDecision, checked_at: str) -> None:
    assert decision.candidate is not None
    candidate = decision.candidate
    conn.execute(
        """INSERT INTO card_images
               (card_id, source, source_card_id, source_variant, source_collector_number,
                language, face_index, image_url_small, image_url_large,
                image_language_scope, is_language_fallback, match_quality, status,
                last_checked_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'jp', 0, ?, ?, 'en', 1, 'exact', 'resolved', ?, CURRENT_TIMESTAMP)
           ON CONFLICT(card_id, source, language, face_index) DO UPDATE SET
               source_card_id=excluded.source_card_id,
               source_variant=excluded.source_variant,
               source_collector_number=excluded.source_collector_number,
               image_url_small=excluded.image_url_small,
               image_url_large=excluded.image_url_large,
               image_language_scope='en',
               is_language_fallback=1,
               match_quality='exact', status='resolved',
               last_checked_at=excluded.last_checked_at,
               updated_at=CURRENT_TIMESTAMP
             WHERE card_images.status='missing'
                OR card_images.is_language_fallback=1""",
        (candidate.jp_card_id, candidate.source, candidate.source_card_id,
         candidate.source_variant, candidate.source_collector_number,
         candidate.small_url, candidate.large_url, checked_at),
    )


def run(db_path: Path, apply: bool = False, report_path: Path | None = None) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        ensure_columns(conn)
        initialized_exact_scopes = initialize_existing_exact_scopes(conn)
        decisions = find_fallback_decisions(conn)
        counts = Counter(decision.status for decision in decisions)
        checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        applied = 0
        for decision in decisions:
            if decision.status == "fallback" and apply:
                upsert_fallback(conn, decision, checked_at)
                applied += 1
        if apply:
            conn.commit()
        else:
            conn.rollback()
        result = {
            "mode": "apply" if apply else "dry-run",
            "checked_at": checked_at,
            "initialized_exact_scopes": initialized_exact_scopes,
            "decisions": dict(sorted(counts.items())),
            "fallbacks_applied": applied,
            "fallbacks": [
                {
                    "jp_card_id": decision.jp_card_id,
                    "en_card_id": decision.candidate.en_card_id,
                    "source": decision.candidate.source,
                    "source_card_id": decision.candidate.source_card_id,
                    "match_method": decision.candidate.match_method,
                }
                for decision in decisions if decision.status == "fallback" and decision.candidate
            ],
            "unresolved": [
                {"jp_card_id": decision.jp_card_id, "status": decision.status, "reason": decision.reason}
                for decision in decisions if decision.status in {"missing", "ambiguous"}
            ],
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if report_path:
        report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.db, apply=args.apply, report_path=args.report), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

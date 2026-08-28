"""Read-only before/after audit for the One Piece catalog."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def audit(db_path: Path) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    game_id = conn.execute("SELECT id FROM games WHERE code='one_piece'").fetchone()[0]
    base = dict(conn.execute(
        """SELECT COUNT(*) AS total_rows,
                  COUNT(DISTINCT card_number) AS distinct_card_numbers,
                  SUM(language_id IS NOT NULL) AS rows_with_language,
                  SUM(language_id IS NULL) AS rows_without_language,
                  SUM(image_url IS NOT NULL) AS rows_with_legacy_image,
                  SUM(image_url IS NULL) AS rows_without_legacy_image,
                  SUM(printing_variant IN ('other','suggested_parallel')) AS unknown_or_ambiguous_variants
             FROM cards WHERE game_id=?""",
        (game_id,),
    ).fetchone())
    base["duplicate_natural_identity_groups"] = conn.execute(
        """SELECT COUNT(*) FROM (
               SELECT expansion_id, card_number, printing_variant, language_id, COUNT(*) n
                 FROM cards WHERE game_id=?
                GROUP BY expansion_id, card_number, printing_variant, language_id
               HAVING n>1
           )""",
        (game_id,),
    ).fetchone()[0]
    base["variant_counts"] = {
        row[0]: row[1] for row in conn.execute(
            "SELECT printing_variant, COUNT(*) FROM cards WHERE game_id=? GROUP BY printing_variant",
            (game_id,),
        )
    }
    base["mapping_counts"] = {
        row[0]: row[1] for row in conn.execute(
            """SELECT m.status, COUNT(*)
                 FROM cardmarket_product_mappings m
                 JOIN cardmarket_products p ON p.id=m.cardmarket_product_id
                 JOIN cardmarket_categories cc ON cc.cardmarket_id_category=p.cardmarket_id_category
                WHERE cc.game_id=? GROUP BY m.status""",
            (game_id,),
        )
    }
    if has_table(conn, "printing_external_ids"):
        base["distinct_cardtrader_blueprints"] = conn.execute(
            """SELECT COUNT(DISTINCT pei.external_id)
                 FROM printing_external_ids pei JOIN cards c ON c.id=pei.card_id
                WHERE c.game_id=? AND pei.source='cardtrader_blueprint'""",
            (game_id,),
        ).fetchone()[0]
        base["rows_with_external_ids"] = conn.execute(
            """SELECT COUNT(DISTINCT c.id)
                 FROM cards c JOIN printing_external_ids pei ON pei.card_id=c.id
                WHERE c.game_id=?""",
            (game_id,),
        ).fetchone()[0]
        base["duplicate_blueprint_language_groups"] = conn.execute(
            """SELECT COUNT(*) FROM (
                   SELECT pei.external_id, c.language_id, COUNT(*) n
                     FROM printing_external_ids pei JOIN cards c ON c.id=pei.card_id
                    WHERE c.game_id=? AND pei.source='cardtrader_blueprint'
                    GROUP BY pei.external_id, c.language_id HAVING n>1
               )""",
            (game_id,),
        ).fetchone()[0]
    else:
        base.update(
            distinct_cardtrader_blueprints=0,
            rows_with_external_ids=0,
            duplicate_blueprint_language_groups=0,
        )
    if "catalog_status" in {row[1] for row in conn.execute("PRAGMA table_info(cards)")}:
        base["catalog_status_counts"] = {
            row[0]: row[1] for row in conn.execute(
                "SELECT catalog_status, COUNT(*) FROM cards WHERE game_id=? GROUP BY catalog_status",
                (game_id,),
            )
        }
        base["rows_with_exact_images"] = conn.execute(
            """SELECT COUNT(DISTINCT c.id)
                 FROM cards c JOIN card_images ci ON ci.card_id=c.id
                WHERE c.game_id=? AND ci.status='resolved' AND ci.match_quality='exact'""",
            (game_id,),
        ).fetchone()[0]
        base["duplicate_commercial_identity_groups"] = conn.execute(
            """SELECT COUNT(*) FROM (
                   SELECT canonical_card_id, set_id,
                          COALESCE(NULLIF(source_variant, ''), art_kind), language_id,
                          COUNT(*) AS n
                     FROM cards WHERE game_id=? AND catalog_status IN ('active','ambiguous')
                       AND canonical_card_id IS NOT NULL AND set_id IS NOT NULL
                       AND language_id IS NOT NULL
                    GROUP BY canonical_card_id, set_id,
                             COALESCE(NULLIF(source_variant, ''), art_kind), language_id
                   HAVING n>1
               )""",
            (game_id,),
        ).fetchone()[0]
    conn.close()
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.db), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

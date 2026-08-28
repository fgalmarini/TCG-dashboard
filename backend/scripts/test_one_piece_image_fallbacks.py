import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.api.queries import fetch_exact_images
from backend.scripts.audit_one_piece_images import audit
from backend.scripts.backfill_one_piece_image_fallbacks import run
from backend.images.one_piece import find_fallback_decisions


class OnePieceImageFallbackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        conn = sqlite3.connect(self.db_path)
        schema_dir = Path(__file__).resolve().parents[1] / "db"
        conn.executescript((schema_dir / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript((schema_dir / "seed.sql").read_text(encoding="utf-8"))
        game_id = conn.execute("SELECT id FROM games WHERE code='one_piece'").fetchone()[0]
        jp_id = conn.execute("SELECT id FROM languages WHERE code='jp'").fetchone()[0]
        conn.execute("INSERT INTO expansions (game_id, cardmarket_id_expansion, name, set_code) VALUES (?, ?, ?, ?)", (game_id, 9001, "Test Set", "OP01"))
        expansion_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO sets (game_id, code, name) VALUES (?, ?, ?)", (game_id, "OP01", "Test Set"))
        set_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        canonical_counter = 0

        def canonical(number):
            nonlocal canonical_counter
            canonical_counter += 1
            identity = f"one_piece:{number}:{canonical_counter}"
            conn.execute("INSERT INTO canonical_cards (game_id, identity_key, canonical_number, name) VALUES (?, ?, ?, ?)", (game_id, identity, number, number))
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        def card(number, language_id, art, release, variant, name=None):
            cid = canonical(number + ("-" + language_id.__str__() + "-" + variant))
            conn.execute(
                """INSERT INTO cards
                   (game_id, expansion_id, card_number, name, printing_variant, set_code,
                    language_id, canonical_card_id, set_id, release_kind, art_kind,
                    source_variant, catalog_status, catalog_source)
                   VALUES (?, ?, ?, ?, 'normal', 'OP01', ?, ?, ?, ?, ?, ?, 'active', 'cardtrader')""",
                (game_id, expansion_id, number, name or number, language_id, cid, set_id, release, art, variant),
            )
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0], cid

        en = conn.execute("SELECT id FROM languages WHERE code='en'").fetchone()[0]
        self.en_base, base_canonical = card("OP01-001", en, "base", "original", "Base")
        self.jp_base, _ = card("OP01-001", jp_id, "base", "original", "Base")
        # Share the canonical identity for the EN/JP pair.
        conn.execute("UPDATE cards SET canonical_card_id=? WHERE id IN (?, ?)", (base_canonical, self.en_base, self.jp_base))
        self.en_alt, alt_canonical = card("OP01-016", en, "alternate_art", "original", "Alternate Art")
        self.jp_alt, _ = card("OP01-016", jp_id, "alternate_art", "original", "Alternate Art")
        conn.execute("UPDATE cards SET canonical_card_id=? WHERE id IN (?, ?)", (alt_canonical, self.en_alt, self.jp_alt))
        self.jp_exact, exact_canonical = card("OP01-020", jp_id, "base", "original", "Base")
        conn.execute("INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant, set_code, language_id, canonical_card_id, set_id, release_kind, art_kind, source_variant, catalog_status) SELECT game_id, expansion_id, 'OP01-020', 'OP01-020', 'normal', 'OP01', ?, ?, set_id, 'original', 'base', 'Base', 'active' FROM cards WHERE id=?", (en, exact_canonical, self.jp_exact))
        self.en_reprint, reprint_canonical = card("OP01-030", en, "base", "reprint", "Base")
        self.jp_reprint, _ = card("OP01-030", jp_id, "base", "reprint", "Base")
        conn.execute("UPDATE cards SET canonical_card_id=? WHERE id IN (?, ?)", (reprint_canonical, self.en_reprint, self.jp_reprint))
        self.jp_ambiguous, amb_canonical = card("OP01-040", jp_id, "base", "original", "Base")
        self.en_amb1, _ = card("OP01-040", en, "base", "original", "Base")
        self.en_amb2, _ = card("OP01-040", en, "base", "original", "Base")
        conn.execute("UPDATE cards SET canonical_card_id=? WHERE id IN (?, ?, ?)", (amb_canonical, self.jp_ambiguous, self.en_amb1, self.en_amb2))

        def external(card_id, value):
            conn.execute("INSERT INTO printing_external_ids (card_id, source, external_id, language_id, language_scope) VALUES (?, 'cardtrader_blueprint', ?, (SELECT language_id FROM cards WHERE id=?), 'exact')", (card_id, value, card_id))

        external(self.en_base, "bp-base"); external(self.jp_base, "bp-base")
        external(self.en_alt, "bp-alt"); external(self.jp_alt, "bp-alt")
        external(self.en_reprint, "bp-reprint"); external(self.jp_reprint, "bp-reprint")
        external(self.en_amb1, "bp-amb-1"); external(self.en_amb2, "bp-amb-2")

        def image(card_id, url, language="en", fallback=0):
            conn.execute("""INSERT INTO card_images
                (card_id, source, source_card_id, language, face_index, image_url_large,
                 image_language_scope, is_language_fallback, match_quality, status, last_checked_at)
                VALUES (?, 'cardtrader', ?, ?, 0, ?, ?, ?, 'exact', 'resolved', '2026-01-01T00:00:00Z')""", (card_id, f"bp-{card_id}", language, url, language, fallback))

        image(self.en_base, "https://cardtrader.com/base.jpg")
        image(self.en_alt, "https://cardtrader.com/alt.jpg")
        image(self.en_reprint, "https://cardtrader.com/reprint.jpg")
        image(self.jp_exact, "https://cardtrader.com/jp-exact.jpg", "jp")
        conn.execute("INSERT INTO card_images (card_id, source, source_card_id, language, face_index, match_quality, status, last_checked_at) VALUES (?, 'cardtrader', 'bp-base', 'jp', 0, 'exact', 'missing', '2026-01-01T00:00:00Z')", (self.jp_base,))
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_deterministic_decisions_and_exact_priority(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        decisions = {decision.jp_card_id: decision for decision in find_fallback_decisions(conn)}
        self.assertEqual(decisions[self.jp_base].status, "fallback")
        self.assertEqual(decisions[self.jp_alt].candidate.match_method, "shared_cardtrader_blueprint")
        self.assertEqual(decisions[self.jp_ambiguous].status, "ambiguous")
        conn.close()

        result = run(self.db_path, apply=True)
        self.assertEqual(result["fallbacks_applied"], 3)
        result_again = run(self.db_path, apply=True)
        self.assertEqual(result_again["fallbacks_applied"], 0)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        images = fetch_exact_images(conn, [self.jp_base, self.jp_alt, self.jp_exact, self.jp_ambiguous])
        self.assertTrue(images[self.jp_base].is_language_fallback)
        self.assertEqual(images[self.jp_base].actual_image_language, "en")
        self.assertEqual(images[self.jp_base].requested_language, "jp")
        self.assertEqual(images[self.jp_alt].faces[0].large_url, "https://cardtrader.com/alt.jpg")
        self.assertFalse(images[self.jp_exact].is_language_fallback)
        self.assertNotIn(self.jp_ambiguous, images)
        conn.close()

    def test_audit_is_read_only_and_reports_fallback_state(self):
        before = self.db_path.stat().st_size
        result = audit(self.db_path)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["counts_by_language"]["jp"]["total_printings"], 5)
        self.assertGreaterEqual(len(result["validation_examples"]), 5)
        self.assertEqual(self.db_path.stat().st_size, before)


if __name__ == "__main__":
    unittest.main()

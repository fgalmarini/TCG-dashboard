import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.scripts.cardmadness_event_wishlist import apply_targets, resolve_targets


class CardmadnessWishlistTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE languages (id INTEGER PRIMARY KEY, code TEXT);
            CREATE TABLE games (id INTEGER PRIMARY KEY, code TEXT);
            CREATE TABLE cards (
                id INTEGER PRIMARY KEY, canonical_card_id INTEGER, set_id INTEGER,
                card_number TEXT, name TEXT, set_code TEXT, treatment TEXT,
                finish TEXT, language_id INTEGER, catalog_status TEXT, game_id INTEGER
            );
            CREATE TABLE events (id INTEGER PRIMARY KEY, code TEXT UNIQUE);
            CREATE TABLE wishlist_items (id INTEGER PRIMARY KEY, card_id INTEGER, status TEXT);
            CREATE TABLE event_wishlist_items (
                event_id INTEGER, wishlist_item_id INTEGER,
                UNIQUE(event_id, wishlist_item_id)
            );
            INSERT INTO languages VALUES (1, 'en');
            INSERT INTO games VALUES (3, 'magic');
            INSERT INTO events VALUES (1, 'cardmadness-2026');
            INSERT INTO cards VALUES
              (101, 1001, 11, '002', 'Surge Target', 'hob', 'surge_foil', 'foil', 1, 'active', 3),
              (102, 1001, 11, '001', 'Surge Target', 'hob', 'traditional_foil', 'foil', 1, 'active', 3),
              (103, 1001, 11, '001', 'Surge Target', 'hob', 'traditional_foil', 'nonfoil', 1, 'active', 3),
              (104, 1002, 12, '003', 'Traditional Only', 'hoc', 'traditional_foil', 'foil', 1, 'active', 3),
              (105, 1002, 12, '003', 'Traditional Only', 'hoc', NULL, 'nonfoil', 1, 'active', 3);
        """)
        self.temp = tempfile.TemporaryDirectory()
        self.catalog = Path(self.temp.name) / "catalog.csv"
        with self.catalog.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(["Set", "Base #", "Carta", "Surge #"])
            writer.writerow(["HOB", "001", "Surge Target", "002"])
            writer.writerow(["HOC", "003", "Traditional Only", ""])

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_selects_surge_target_and_traditional_only_target_without_nonfoil(self):
        plan = resolve_targets(self.conn, self.catalog)
        self.assertEqual(plan.conflicts, [])
        self.assertEqual(plan.missing, [])
        self.assertEqual(
            [(target.card_id, target.treatment) for target in plan.targets],
            [(101, "surge_foil"), (104, "traditional_foil")],
        )
        self.assertEqual(plan.traditional_alternatives, 1)
        self.assertNotIn(102, {target.card_id for target in plan.targets})
        self.assertNotIn(103, {target.card_id for target in plan.targets})
        self.assertNotIn(105, {target.card_id for target in plan.targets})

    def test_duplicate_exact_catalog_match_is_reported_as_conflict(self):
        self.conn.execute(
            "INSERT INTO cards VALUES (106, 1001, 11, '002', 'Duplicate', 'hob', 'surge_foil', 'foil', 1, 'active', 3)"
        )
        plan = resolve_targets(self.conn, self.catalog)
        self.assertEqual(len(plan.targets), 1)
        self.assertTrue(any("2 exact printings" in conflict for conflict in plan.conflicts))

    def test_apply_is_idempotent_and_preserves_preexisting_wishlist_rows(self):
        plan = resolve_targets(self.conn, self.catalog)
        preexisting = [(1, 9001, "wanted"), (2, 9002, "acquired"), (3, 9003, "removed")]
        self.conn.executemany("INSERT INTO wishlist_items VALUES (?, ?, ?)", preexisting)
        create_calls = []
        link_calls = []

        def create(card_id):
            create_calls.append(card_id)
            cursor = self.conn.execute("INSERT INTO wishlist_items(card_id,status) VALUES (?, 'wanted')", (card_id,))
            self.conn.commit()
            return cursor.lastrowid

        def link(event_code, item_id):
            self.assertEqual(event_code, "cardmadness-2026")
            self.conn.execute("INSERT OR IGNORE INTO event_wishlist_items VALUES (1, ?)", (item_id,))
            self.conn.commit()
            link_calls.append(item_id)

        first = apply_targets(self.conn, plan.targets, create, link)
        second = apply_targets(self.conn, plan.targets, create, link)
        self.assertEqual(first, {"created": 2, "reused": 0, "linked": 2, "already_linked": 0})
        self.assertEqual(second, {"created": 0, "reused": 2, "linked": 0, "already_linked": 2})
        self.assertEqual(len(create_calls), 2)
        self.assertEqual(len(link_calls), 2)
        self.assertEqual(
            [tuple(row) for row in self.conn.execute("SELECT id,card_id,status FROM wishlist_items WHERE id<=3 ORDER BY id")],
            preexisting,
        )
        self.assertEqual(self.conn.execute("SELECT count(*) FROM wishlist_items WHERE card_id IN (101,104)").fetchone()[0], 2)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM event_wishlist_items").fetchone()[0], 2)

    def test_apply_reuses_existing_item_without_changing_its_status(self):
        plan = resolve_targets(self.conn, self.catalog)
        self.conn.execute("INSERT INTO wishlist_items VALUES (20, 101, 'removed')")
        creates = []
        result = apply_targets(
            self.conn, plan.targets,
            lambda card_id: creates.append(card_id) or 30,
            lambda _code, _item_id: None,
        )
        self.assertEqual(result["reused"], 1)
        self.assertEqual(creates, [104])
        self.assertEqual(self.conn.execute("SELECT status FROM wishlist_items WHERE id=20").fetchone()[0], "removed")


if __name__ == "__main__":
    unittest.main()

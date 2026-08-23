import unittest

from card_mapper import get_or_create_card
from test_support import make_test_db


class CardMapperTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_test_db()
        self.conn.execute("INSERT INTO expansions (id, game_id, cardmarket_id_expansion, name) VALUES (1, 2, 9999, NULL)")

    def tearDown(self):
        self.conn.close()

    def test_creates_card_when_no_collision(self):
        card_id, status, notes = get_or_create_card(self.conn, 2, 1, "OP01-001", "Luffy", "normal", None, 111)
        self.assertIsNotNone(card_id)
        self.assertEqual(status, "mapped")
        self.assertIsNone(notes)

    def test_collision_reports_ambiguous_without_raising(self):
        get_or_create_card(self.conn, 2, 1, "OP01-002", "Zoro", "normal", None, 222)
        # mismo expansion_id + card_number + printing_variant -> colisiona con UNIQUE
        card_id, status, notes = get_or_create_card(self.conn, 2, 1, "OP01-002", "Zoro (alt)", "normal", None, 333)
        self.assertIsNone(card_id)
        self.assertEqual(status, "ambiguous")
        self.assertIsNotNone(notes)

    def test_collision_does_not_discard_prior_successful_inserts_in_same_transaction(self):
        # regresion: un conn.rollback() sobre la excepcion tiraria abajo TODO lo insertado
        # antes en la misma transaccion -- no debe pasar.
        first_id, _, _ = get_or_create_card(self.conn, 2, 1, "OP01-003", "Sanji", "normal", None, 444)
        get_or_create_card(self.conn, 2, 1, "OP01-003", "Sanji (dup)", "normal", None, 555)
        row = self.conn.execute("SELECT id FROM cards WHERE id = ?", (first_id,)).fetchone()
        self.assertIsNotNone(row, "el insert exitoso anterior no deberia haberse revertido")

    def test_different_printing_variant_avoids_collision(self):
        get_or_create_card(self.conn, 2, 1, "OP01-004", "Nami", "normal", None, 666)
        card_id, status, _ = get_or_create_card(self.conn, 2, 1, "OP01-004", "Nami (alt art)", "suggested_parallel", "(V.2)", 666)
        self.assertIsNotNone(card_id)
        self.assertEqual(status, "mapped")

    def test_null_card_number_never_collides(self):
        # Magic: card_number siempre NULL -- SQLite no colisiona multiples NULL.
        get_or_create_card(self.conn, 3, 1, None, "Gandalf the Grey", "normal", None, 100)
        card_id, status, _ = get_or_create_card(self.conn, 3, 1, None, "Aragorn", "normal", None, 200)
        self.assertIsNotNone(card_id)
        self.assertEqual(status, "mapped")


if __name__ == "__main__":
    unittest.main()

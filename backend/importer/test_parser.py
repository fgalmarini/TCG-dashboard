import unittest

from parser import extract_variant_label, parse_date_added, parse_one_piece_name


class ParseDateAddedTest(unittest.TestCase):
    def test_valid_date_passthrough(self):
        self.assertEqual(parse_date_added("2023-03-14 09:32:42"), "2023-03-14 09:32:42")

    def test_sentinel_becomes_none(self):
        self.assertIsNone(parse_date_added("0000-00-00 00:00:00"))

    def test_none_stays_none(self):
        self.assertIsNone(parse_date_added(None))


class ParseOnePieceNameTest(unittest.TestCase):
    def test_well_formed_name(self):
        card_number, name = parse_one_piece_name("Monkey.D.Luffy (OP01-001)")
        self.assertEqual(card_number, "OP01-001")
        self.assertEqual(name, "Monkey.D.Luffy")

    def test_don_card_no_parens(self):
        # Cartas DON!! sin card number tradicional -- no matchea, es lo esperado.
        card_number, name = parse_one_piece_name("DON!!")
        self.assertIsNone(card_number)
        self.assertEqual(name, "DON!!")

    def test_lowercase_inside_parens_no_match(self):
        # "Don!! (PRB Kid)" -- contenido de parentesis con espacio/minusculas, no matchea.
        card_number, name = parse_one_piece_name("Don!! (PRB Kid)")
        self.assertIsNone(card_number)
        self.assertEqual(name, "Don!! (PRB Kid)")

    def test_no_parens_at_all(self):
        # Inconsistencia real confirmada en datos de Cardmarket (6 casos, idMetacard 421983).
        card_number, name = parse_one_piece_name("Monkey.D.Luffy")
        self.assertIsNone(card_number)
        self.assertEqual(name, "Monkey.D.Luffy")


class ExtractVariantLabelTest(unittest.TestCase):
    def test_variant_label_present(self):
        label = extract_variant_label("Rhino Warrior Token (G 4/4) // Treasure Token (V.4)")
        self.assertEqual(label, "(V.4)")

    def test_variant_label_absent(self):
        self.assertIsNone(extract_variant_label("Gandalf the Grey"))


if __name__ == "__main__":
    unittest.main()

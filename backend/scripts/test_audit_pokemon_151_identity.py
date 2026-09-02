import hashlib
import json
import unittest
from pathlib import Path

import audit_pokemon_151_identity as audit


class Pokemon151IdentityAuditTests(unittest.TestCase):
    def test_official_reference_is_complete(self):
        pdf = Path("backend/scripts/.pokemon_151_identity_cache/official/mew_web_cardlist_en.pdf")
        self.assertTrue(pdf.exists())
        rows, _ = audit.read_official_pdf(pdf)
        self.assertEqual([row["collector_number"] for row in rows], audit.EXPECTED_NUMBERS)
        self.assertLess(len({row["card_name"] for row in rows}), 207)

    def test_same_name_alternate_numbers_remain_ambiguous_without_direct_id(self):
        official = [
            {"collector_number": "006", "card_name": "Charizard ex", "rarity": "Double Rare"},
            {"collector_number": "183", "card_name": "Charizard ex", "rarity": "Ultra Rare"},
        ]
        tcgdex = {
            "006": {"attacks": [{"name": "Brave Wing"}, {"name": "Explosive Vortex"}]},
            "183": {"attacks": [{"name": "Brave Wing"}, {"name": "Explosive Vortex"}]},
        }
        product = {"idProduct": 719448, "name": "Charizard ex [Brave Wing | Explosive Vortex]"}
        candidates, method, _ = audit.choose_candidates(product, official, tcgdex, {})
        self.assertEqual([row["collector_number"] for row in candidates], ["006", "183"])
        self.assertEqual(method, "exact_name_and_attack_signature")

    def test_energy_alias_maps_basic_psychic_energy_to_official_207(self):
        official = [{"collector_number": "207", "card_name": "Basic Energy", "category": "Energy", "rarity": "Hyper Rare"}]
        candidates, method, _ = audit.choose_candidates({"idProduct": 1, "name": "Basic Psychic Energy"}, official, {}, {})
        self.assertEqual([row["collector_number"] for row in candidates], ["207"])
        self.assertEqual(method, "official_energy_name_alias")

    def test_extras_are_group_surplus_only(self):
        official = [
            {"collector_number": "143", "card_name": "Snorlax"},
            {"collector_number": "150", "card_name": "Mewtwo"},
            {"collector_number": "151", "card_name": "Mew ex"},
            {"collector_number": "193", "card_name": "Mew ex"},
            {"collector_number": "205", "card_name": "Mew ex"},
        ]
        mapping = [
            {"idMetacard": 10, "cardmarket_product_id": 1, "cardmarket_product_name": "Snorlax [Attack]"},
            {"idMetacard": 10, "cardmarket_product_id": 2, "cardmarket_product_name": "Snorlax [Attack]"},
            {"idMetacard": 11, "cardmarket_product_id": 3, "cardmarket_product_name": "Mewtwo [Attack]"},
            {"idMetacard": 11, "cardmarket_product_id": 4, "cardmarket_product_name": "Mewtwo [Attack]"},
            {"idMetacard": 12, "cardmarket_product_id": 5, "cardmarket_product_name": "Mew ex [Attack]"},
            {"idMetacard": 12, "cardmarket_product_id": 6, "cardmarket_product_name": "Mew ex [Attack]"},
            {"idMetacard": 12, "cardmarket_product_id": 7, "cardmarket_product_name": "Mew ex [Attack]"},
            {"idMetacard": 12, "cardmarket_product_id": 8, "cardmarket_product_name": "Mew ex [Attack]"},
        ]
        extras = audit.extras_rows(mapping, official)
        self.assertEqual([row["idProduct"] for row in extras], [2, 4, 8])
        self.assertEqual(len(extras), 3)

    def test_cache_reports_are_deterministic_and_db_is_not_in_scope(self):
        report = Path("reports/pokemon_151/identity_discovery/03_cardmarket_mapping.csv")
        self.assertTrue(report.exists())
        first = hashlib.sha256(report.read_bytes()).hexdigest()
        second = hashlib.sha256(report.read_bytes()).hexdigest()
        self.assertEqual(first, second)
        manifest = json.loads(Path("reports/pokemon_151/identity_discovery/source_manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("database", manifest)


if __name__ == "__main__":
    unittest.main()

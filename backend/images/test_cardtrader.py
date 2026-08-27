import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .cardtrader import (
    CardTraderCatalog,
    CardTraderConfigurationError,
    load_cardtrader_token,
)


def blueprint(blueprint_id=1, product_id=1002, **overrides):
    value = {
        "id": blueprint_id,
        "name": "Art Series: Test",
        "version": "Gold-Stamped",
        "card_market_ids": [product_id],
        "image_url": "https://cardtrader.com/uploads/blueprint/test.jpg",
        "fixed_properties": {"collector_number": "A01g"},
        "editable_properties": [{"name": "mtg_language", "default_value": "en"}],
    }
    value.update(overrides)
    return value


class CardTraderResolverTest(unittest.TestCase):
    def test_exact_match_preserves_gold_variant_and_collector_number(self):
        resolution = CardTraderCatalog.from_blueprints([blueprint()]).resolve_product_id(1002)
        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(resolution.source, "cardtrader")
        self.assertEqual(resolution.source_card_id, "1")
        self.assertEqual(resolution.source_variant, "Gold-Stamped")
        self.assertEqual(resolution.source_collector_number, "A01g")
        self.assertIsNone(resolution.faces[0].small_url)
        self.assertEqual(resolution.faces[0].large_url, "https://cardtrader.com/uploads/blueprint/test.jpg")

    def test_zero_matches_are_missing(self):
        resolution = CardTraderCatalog.from_blueprints([blueprint()]).resolve_product_id(9999)
        self.assertEqual(resolution.status, "missing")

    def test_duplicate_matches_are_ambiguous(self):
        resolution = CardTraderCatalog.from_blueprints([
            blueprint(1), blueprint(2, image_url="https://cardtrader.com/uploads/blueprint/test-2.jpg")
        ]).resolve_product_id(1002)
        self.assertEqual(resolution.status, "ambiguous")

    def test_invalid_url_is_rejected(self):
        resolution = CardTraderCatalog.from_blueprints([
            blueprint(image_url="http://cardtrader.com/uploads/blueprint/test.jpg")
        ]).resolve_product_id(1002)
        self.assertEqual(resolution.status, "error")
        self.assertIn("validation", resolution.reason)

    def test_missing_token_is_clear_and_does_not_print_secret(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CARDTRADER_API_TOKEN": ""}, clear=False):
                with self.assertRaisesRegex(CardTraderConfigurationError, "CARDTRADER_API_TOKEN"):
                    load_cardtrader_token(Path(temp_dir) / ".env")


if __name__ == "__main__":
    unittest.main()

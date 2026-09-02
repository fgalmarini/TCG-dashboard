import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import audit_pokemon_151_finish_pricing_sources as audit


ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "backend/db/tcg_dashboard.db"


class FinishPricingSourceAuditTests(unittest.TestCase):
    def test_identity_validation_keeps_same_name_alternate_numbers_separate(self):
        self.assertEqual(
            audit.validate_identity({"set": {"id": "sv3pt5"}, "number": "006", "name": "Charizard ex"}, "006", "Charizard ex", "sv3pt5")[0],
            "EXACT",
        )
        status, note = audit.validate_identity({"set": {"id": "sv3pt5"}, "number": "199", "name": "Charizard ex"}, "006", "Charizard ex", "sv3pt5")
        self.assertEqual(status, "MISMATCH")
        self.assertIn("number", note)

    def test_tcgplayer_finish_keys_and_reverse_cardmarket_are_distinct(self):
        prices = {
            "normal": {"low": 1.0, "market": 2.0},
            "holofoil": {"low": 3.0, "market": 4.0},
            "reverseHolofoil": {"low": 5.0, "market": 6.0},
        }
        self.assertEqual(audit.extract_tcgplayer(prices, "normal")[2:], (1.0, 2.0, "normal"))
        self.assertEqual(audit.extract_tcgplayer(prices, "holo")[2:], (3.0, 4.0, "holofoil"))
        self.assertEqual(audit.extract_tcgplayer(prices, "reverse_holo")[2:], (5.0, 6.0, "reverseHolofoil"))
        self.assertFalse(audit.positive(0.0))

    def test_blocked_response_is_cached_without_bypass(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = audit.SourceCache(Path(directory), offline=False, refresh=False)
            error = HTTPError("https://example.test", 403, "blocked", {}, None)
            error.read = lambda: b"blocked"
            with patch.object(audit, "urlopen", side_effect=error):
                result = cache.fetch("https://example.test", "cardmarket_public_product_page")
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["http_status"], 403)
            self.assertTrue((Path(directory) / result["cache_file"]).exists())
            self.assertEqual(json.loads((Path(directory) / "manifest.json").read_text())["entries"][0]["status"], "BLOCKED")

    def test_offline_run_writes_reports_but_not_database(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            copied_db = work / "tcg_dashboard.db"
            shutil.copy2(DB, copied_db)
            before = hashlib.sha256(copied_db.read_bytes()).hexdigest()
            result = audit.run(copied_db, work / "reports", work / "cache", "cardmarket", True, False)
            after = hashlib.sha256(copied_db.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual(result["db_writes"], 0)
            self.assertEqual(result["prices_applied"], 0)
            self.assertEqual(result["physical_printings"], 362)
            self.assertEqual(result["numbered_identities"], 207)
            self.assertTrue((work / "reports/08_summary.md").exists())

    def test_real_local_catalog_counts_and_no_currency_conversion(self):
        identities, physical, catalog = audit.read_catalog(DB)
        self.assertEqual(len(identities), 207)
        self.assertEqual(len(physical), 362)
        self.assertEqual(catalog["finish_counts"], {"normal": 128, "holo": 81, "reverse_holo": 153})
        self.assertEqual(audit.positive(0), False)


if __name__ == "__main__":
    unittest.main()

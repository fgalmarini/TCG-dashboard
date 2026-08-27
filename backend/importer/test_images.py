import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from backend.importer import images
from backend.importer.images import resolve_magic_image_url, resolve_one_piece_image_url


class ResolveMagicImageUrlTest(unittest.TestCase):
    @patch("backend.importer.images.urllib.request.urlopen")
    def test_sends_user_agent_and_accept_headers(self, mock_urlopen):
        """Regresion: Scryfall devuelve 400 bad_request si faltan estos headers
        (descubierto al implementar backend/scripts/scryfall_backfill.py)."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"image_uris": {"normal": "https://example.com/n.jpg"}}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        resolve_magic_image_url(701677)

        sent_request = mock_urlopen.call_args[0][0]
        self.assertEqual(sent_request.get_header("User-agent"), "TCGDashboard/1.0 (personal collection tool; images.py)")
        self.assertEqual(sent_request.get_header("Accept"), "application/json")

    @patch("backend.importer.images.urllib.request.urlopen")
    def test_returns_normal_image_from_image_uris(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"image_uris": {"normal": "https://example.com/normal.jpg", "large": "https://example.com/large.jpg"}}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = resolve_magic_image_url(701677)

        self.assertEqual(result, "https://example.com/normal.jpg")

    @patch("backend.importer.images.urllib.request.urlopen")
    def test_falls_back_to_card_faces_for_double_faced_cards(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"card_faces": [{"image_uris": {"normal": "https://example.com/face1.jpg"}}, {}]}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = resolve_magic_image_url(715972)

        self.assertEqual(result, "https://example.com/face1.jpg")

    @patch("backend.importer.images.urllib.request.urlopen")
    def test_returns_none_on_http_error_without_raising(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError("url", 404, "not found", None, None)

        result = resolve_magic_image_url(999999)

        self.assertIsNone(result)

    @patch("backend.importer.images.urllib.request.urlopen")
    def test_returns_none_on_invalid_json(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = resolve_magic_image_url(701677)

        self.assertIsNone(result)


class ResolveOnePieceImageUrlTest(unittest.TestCase):
    def test_builds_official_url_from_card_number(self):
        self.assertEqual(
            resolve_one_piece_image_url("OP01-001"),
            "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-001.png",
        )


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from downloader import download_file


class DownloadFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp_dir.name) / "sub" / "file.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch("downloader.urllib.request.urlopen")
    def test_successful_download_writes_file(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = download_file("https://example.com/data.json", self.dest)

        self.assertTrue(result.ok)
        self.assertEqual(result.size_bytes, len(b'{"ok": true}'))
        self.assertEqual(self.dest.read_bytes(), b'{"ok": true}')
        self.assertFalse(self.dest.with_suffix(self.dest.suffix + ".tmp").exists())

    @patch("downloader.urllib.request.urlopen")
    def test_failed_download_does_not_leave_partial_file(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("boom")

        result = download_file("https://example.com/data.json", self.dest)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "<urlopen error boom>")
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.dest.with_suffix(self.dest.suffix + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()

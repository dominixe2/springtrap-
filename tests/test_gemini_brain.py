import json
from io import BytesIO
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from brain.gemini_brain import GeminiBrain, GeminiBrainError


class GeminiBrainTests(unittest.TestCase):
    def test_missing_key_is_clear_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(GeminiBrainError, "Gemini API klíč"):
                GeminiBrain(api_key=None)

    @patch("brain.gemini_brain.urllib.request.urlopen")
    def test_returns_joined_text_parts(self, mock_urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": "Ahoj "}, {"text": "světe!"}]}
            }]
        }).encode("utf-8")
        mock_urlopen.return_value = response

        brain = GeminiBrain(api_key="test-key", model="test-model")
        self.assertEqual(brain.ask("Zdravíš mě?"), "Ahoj světe!")
        request = mock_urlopen.call_args.args[0]
        self.assertIn("test-model:generateContent", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "test-key")

    @patch("brain.gemini_brain.urllib.request.urlopen")
    def test_screenshot_is_attached_as_base64(self, mock_urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": "Vidím obrázek."}]}}]
        }).encode("utf-8")
        mock_urlopen.return_value = response

        brain = GeminiBrain(api_key="test-key", model="test-model")
        brain.ask("Co je na snímku?", screenshot=b"png-data")
        request = mock_urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["contents"][0]["parts"][1]["inline_data"]["mime_type"], "image/png")
        self.assertEqual(body["contents"][0]["parts"][1]["inline_data"]["data"], "cG5nLWRhdGE=")

    @patch("brain.gemini_brain.urllib.request.urlopen")
    def test_http_error_is_converted_to_clear_error(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            "https://example.test", 403, "Forbidden", {}, BytesIO(b"permission denied")
        )
        brain = GeminiBrain(api_key="test-key", model="test-model")
        with self.assertRaisesRegex(GeminiBrainError, "HTTP 403"):
            brain.ask("Test")


if __name__ == "__main__":
    unittest.main()

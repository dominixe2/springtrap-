"""Security regression tests for the Windows Companion HTTP bridge."""
from __future__ import annotations

import http.client
import importlib.util
import json
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

COMPANION_PATH = Path(__file__).resolve().parents[1] / "companion.py"
SPEC = importlib.util.spec_from_file_location("micro_helper_companion", COMPANION_PATH)
assert SPEC and SPEC.loader
companion = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = companion
SPEC.loader.exec_module(companion)


class CompanionSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = companion.ThreadingHTTPServer(("127.0.0.1", 0), companion.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self) -> None:
        companion.PAIRING_CODE = "test-pairing-code"
        companion.SESSION_TOKEN = ""
        companion.FAILED_PAIRS = 0

    def request(self, path: str, payload: dict | None = None, *, origin: str | None = companion.APP_ORIGIN, token: str = ""):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        body = json.dumps(payload or {}).encode("utf-8")
        headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
        if origin is not None:
            headers["Origin"] = origin
        if token:
            headers["Authorization"] = "Bearer " + token
        connection.request("POST", path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        result = json.loads(raw.decode("utf-8")) if raw else {}
        status = response.status
        connection.close()
        return status, result

    def pair(self) -> str:
        status, result = self.request("/pair", {"code": companion.PAIRING_CODE})
        self.assertEqual(status, 200)
        self.assertTrue(result.get("paired"))
        return result["token"]

    def test_post_rejects_untrusted_origin(self) -> None:
        status, _ = self.request("/pair", {"code": companion.PAIRING_CODE}, origin="https://attacker.example")
        self.assertEqual(status, 403)
        self.assertEqual(companion.FAILED_PAIRS, 0)

    def test_non_object_json_body_is_rejected(self) -> None:
        status, _ = self.request("/pair", ["not", "an", "object"])  # type: ignore[arg-type]
        self.assertEqual(status, 400)

    def test_pairing_code_is_single_use(self) -> None:
        old_code = companion.PAIRING_CODE
        token = self.pair()
        self.assertTrue(token)
        self.assertNotEqual(companion.PAIRING_CODE, old_code)
        status, _ = self.request("/pair", {"code": old_code})
        self.assertEqual(status, 401)

    def test_invalid_pairing_attempts_are_limited(self) -> None:
        for _ in range(8):
            status, _ = self.request("/pair", {"code": "wrong"})
            self.assertEqual(status, 401)
        status, _ = self.request("/pair", {"code": "wrong"})
        self.assertEqual(status, 429)

    def test_allowlisted_command_uses_fixed_executable_without_shell(self) -> None:
        token = self.pair()
        with patch.object(companion.sys, "platform", "win32"), patch.object(companion.subprocess, "Popen") as popen:
            status, result = self.request("/command", {"action": "notepad"}, token=token)
        self.assertEqual(status, 200)
        self.assertTrue(result.get("ok"))
        popen.assert_called_once_with(["notepad.exe"], shell=False, close_fds=True)

    def test_arbitrary_command_is_rejected(self) -> None:
        token = self.pair()
        with patch.object(companion.sys, "platform", "win32"), patch.object(companion.subprocess, "Popen") as popen:
            status, _ = self.request("/command", {"action": "powershell"}, token=token)
        self.assertEqual(status, 403)
        popen.assert_not_called()

    def test_unpair_revokes_session_token(self) -> None:
        token = self.pair()
        status, result = self.request("/unpair", {}, token=token)
        self.assertEqual(status, 200)
        self.assertTrue(result.get("unpaired"))
        status, _ = self.request("/command", {"action": "notepad"}, token=token)
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()

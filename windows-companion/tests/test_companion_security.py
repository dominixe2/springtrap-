"""Unit tests for the safe Windows command allowlist."""
import importlib.util
import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "companion.py"
SPEC = importlib.util.spec_from_file_location("micro_helper_companion", PATH)
assert SPEC and SPEC.loader
companion = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = companion
SPEC.loader.exec_module(companion)


class CompanionSecurityTests(unittest.TestCase):
    def test_only_four_fixed_actions_are_allowed(self):
        self.assertEqual(companion.ALLOWED, {"lock", "explorer", "notepad", "calculator"})

    def test_arbitrary_shell_command_is_rejected(self):
        for action in ("powershell", "cmd", "python", "shutdown", "explorer.exe & whoami"):
            with self.subTest(action=action), self.assertRaises(ValueError):
                companion.execute_action(action)

    def test_allowlisted_application_uses_fixed_executable_without_shell(self):
        with patch.object(companion.sys, "platform", "win32"), patch("subprocess.Popen") as popen:
            message = companion.execute_action("notepad")
        self.assertEqual(message, "Spuštěno: notepad.exe")
        popen.assert_called_once_with(["notepad.exe"], shell=False, close_fds=True)

    def test_explorer_and_calculator_use_fixed_paths(self):
        with patch.object(companion.sys, "platform", "win32"), patch("subprocess.Popen") as popen:
            companion.execute_action("explorer")
            companion.execute_action("calculator")
        self.assertEqual(popen.call_args_list[0].args[0], ["explorer.exe"])
        self.assertEqual(popen.call_args_list[1].args[0], ["calc.exe"])
        self.assertTrue(all(call.kwargs["shell"] is False for call in popen.call_args_list))

    def test_non_windows_platform_refuses_commands(self):
        with patch.object(companion.sys, "platform", "linux"):
            with self.assertRaises(OSError):
                companion.execute_action("notepad")

    def test_pairing_status_server_binds_loopback_and_never_caches_code(self):
        status = companion.PairingStatus()
        status.set_pairing_code("123456", 300)
        server = companion.start_pairing_status_server(status)
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
            url = f"http://127.0.0.1:{server.server_port}/status"
            with urllib.request.urlopen(url, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")
                self.assertNotIn("Access-Control-Allow-Origin", response.headers)
            self.assertEqual(payload["pairing_code"], "123456")
            self.assertGreater(payload["expires_in"], 0)
        finally:
            server.shutdown()
            server.server_close()

    def test_pairing_status_rejects_foreign_host_and_cross_site_fetch(self):
        status = companion.PairingStatus()
        status.set_pairing_code("654321", 300)
        server = companion.start_pairing_status_server(status)
        url = f"http://127.0.0.1:{server.server_port}/status"
        try:
            for headers in (
                {"Host": "attacker.example"},
                {"Sec-Fetch-Site": "cross-site"},
            ):
                request = urllib.request.Request(url, headers=headers)
                with self.subTest(headers=headers), self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(error.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()

    def test_expired_pairing_code_is_not_returned(self):
        status = companion.PairingStatus()
        status.set_pairing_code("999999", 0)
        snapshot = status.snapshot()
        self.assertIsNone(snapshot["pairing_code"])
        self.assertEqual(snapshot["expires_in"], 0)

    def test_pairing_page_uses_text_content_and_no_web_storage(self):
        status = companion.PairingStatus()
        server = companion.start_pairing_status_server(status)
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            with urllib.request.urlopen(url, timeout=3) as response:
                page = response.read().decode("utf-8")
            self.assertIn("textContent", page)
            self.assertIn('fetch("/status"', page)
            self.assertNotIn("localStorage", page)
            self.assertNotIn("sessionStorage", page)
        finally:
            server.shutdown()
            server.server_close()

    def test_pairing_notice_contains_only_the_local_url(self):
        notice = companion.pairing_status_notice("http://127.0.0.1:12345")
        self.assertIn("http://127.0.0.1:12345", notice)
        self.assertNotIn("123456", notice)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the safe Windows command allowlist."""
import importlib.util
import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()

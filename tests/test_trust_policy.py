import unittest

from micro_helper.trust_policy import Action, Decision, PermissionPolicy, evaluate_action


class TrustPolicyTests(unittest.TestCase):
    def test_destructive_actions_require_confirmation(self):
        result = evaluate_action(
            Action("windows.files", "delete", "C:/important.txt", destructive=True),
            PermissionPolicy(),
        )
        self.assertEqual(result.decision, Decision.CONFIRM)

    def test_financial_actions_always_require_confirmation(self):
        key = "bank.transfer:send:recipient-1"
        result = evaluate_action(
            Action("bank.transfer", "send", "recipient-1", financial=True),
            PermissionPolicy(grants=frozenset({key})),
        )
        self.assertEqual(result.decision, Decision.CONFIRM)

    def test_explicit_deny_overrides_grant(self):
        key = "browser.tabs:close:tab-3"
        policy = PermissionPolicy(grants=frozenset({key}), denied=frozenset({key}))
        self.assertEqual(evaluate_action(Action("browser.tabs", "close", "tab-3"), policy).decision, Decision.DENY)

    def test_grant_is_exact_and_does_not_leak_to_other_targets(self):
        policy = PermissionPolicy(grants=frozenset({"files.read:open:documents"}))
        self.assertEqual(evaluate_action(Action("files.read", "open", "documents"), policy).decision, Decision.ALLOW)
        self.assertEqual(evaluate_action(Action("files.read", "open", "secrets"), policy).decision, Decision.DENY)

    def test_only_reject_optional_cookies_is_narrowly_allowed(self):
        allowed = evaluate_action(Action("browser.cookie_consent", "reject_optional"), PermissionPolicy())
        confirm = evaluate_action(Action("browser.cookie_consent", "accept_all", changes_external_state=True), PermissionPolicy())
        self.assertEqual(allowed.decision, Decision.ALLOW)
        self.assertEqual(confirm.decision, Decision.CONFIRM)

    def test_sensitive_data_requires_confirmation_even_with_grant(self):
        key = "files.read:open:private"
        result = evaluate_action(
            Action("files.read", "open", "private", accesses_sensitive_data=True),
            PermissionPolicy(grants=frozenset({key})),
        )
        self.assertEqual(result.decision, Decision.CONFIRM)


if __name__ == "__main__":
    unittest.main()

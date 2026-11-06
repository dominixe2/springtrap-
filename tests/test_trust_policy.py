import unittest

from micro_helper.trust_policy import (
    Action,
    Decision,
    PermissionPolicy,
    evaluate_action,
)


class TrustPolicyTests(unittest.TestCase):
    def test_learning_does_not_grant_permissions(self):
        result = evaluate_action(
            Action("windows.files", "delete", "C:/important.txt", destructive=True),
            PermissionPolicy(),
        )
        self.assertEqual(result.decision, Decision.CONFIRM)

    def test_financial_actions_always_require_confirmation(self):
        policy = PermissionPolicy(grants=frozenset({"bank.transfer:send:recipient-1"}))
        result = evaluate_action(
            Action("bank.transfer", "send", "recipient-1", financial=True),
            policy,
        )
        self.assertEqual(result.decision, Decision.CONFIRM)

    def test_explicit_deny_overrides_grant(self):
        key = "browser.tabs:close:tab-3"
        policy = PermissionPolicy(grants=frozenset({key}), denied=frozenset({key}))
        result = evaluate_action(Action("browser.tabs", "close", "tab-3"), policy)
        self.assertEqual(result.decision, Decision.DENY)

    def test_exact_grant_allows_only_matching_capability(self):
        policy = PermissionPolicy(grants=frozenset({"files.read:open:documents"}))
        allowed = evaluate_action(Action("files.read", "open", "documents"), policy)
        other = evaluate_action(Action("files.read", "open", "secrets"), policy)
        self.assertEqual(allowed.decision, Decision.ALLOW)
        self.assertEqual(other.decision, Decision.DENY)

    def test_reject_optional_cookies_is_narrowly_allowed(self):
        result = evaluate_action(
            Action("browser.cookie_consent", "reject_optional"),
            PermissionPolicy(),
        )
        self.assertEqual(result.decision, Decision.ALLOW)

    def test_accept_all_cookies_is_not_auto_allowed(self):
        result = evaluate_action(
            Action("browser.cookie_consent", "accept_all", changes_external_state=True),
            PermissionPolicy(),
        )
        self.assertEqual(result.decision, Decision.CONFIRM)


if __name__ == "__main__":
    unittest.main()

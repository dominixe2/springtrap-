"""Deterministic permission gate for Micro Helper tool actions.

Learning may suggest preferences, but it never creates grants. Callers must
supply an explicit, revocable grant for the exact capability being requested.
High-impact actions still require fresh confirmation even when a grant exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet


class Decision(str, Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


@dataclass(frozen=True)
class Action:
    capability: str
    operation: str
    target: str = ""
    changes_external_state: bool = False
    accesses_sensitive_data: bool = False
    financial: bool = False
    destructive: bool = False
    sends_external_message: bool = False
    shares_sensitive_data: bool = False
    changes_account_state: bool = False
    changes_security_settings: bool = False
    installs_software: bool = False
    runs_untrusted_code: bool = False


@dataclass(frozen=True)
class PermissionPolicy:
    """Explicit grants for one user/device; never populate from learned habits."""

    grants: FrozenSet[str] = frozenset()
    denied: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str


def permission_key(action: Action) -> str:
    return f"{action.capability}:{action.operation}:{action.target}"


def evaluate_action(action: Action, policy: PermissionPolicy) -> PolicyResult:
    """Return a conservative decision; learned preferences are intentionally absent."""
    key = permission_key(action)

    # Explicit deny always wins, including over a grant or confirmation workflow.
    if key in policy.denied:
        return PolicyResult(Decision.DENY, "This exact action is explicitly denied.")

    # These operations always need a fresh, action-specific confirmation.
    # A saved grant or learned habit must never silently authorize them.
    if action.financial:
        return PolicyResult(Decision.CONFIRM, "Financial actions always require fresh confirmation.")
    if action.destructive:
        return PolicyResult(Decision.CONFIRM, "Destructive actions always require fresh confirmation.")
    if action.accesses_sensitive_data or action.shares_sensitive_data:
        return PolicyResult(Decision.CONFIRM, "Sensitive data access or sharing requires fresh confirmation.")
    if action.sends_external_message:
        return PolicyResult(Decision.CONFIRM, "Sending an external message requires fresh confirmation.")
    if action.changes_account_state:
        return PolicyResult(Decision.CONFIRM, "Account changes always require fresh confirmation.")
    if action.changes_security_settings:
        return PolicyResult(Decision.CONFIRM, "Security changes always require fresh confirmation.")
    if action.installs_software:
        return PolicyResult(Decision.CONFIRM, "Software installation always requires fresh confirmation.")
    if action.runs_untrusted_code:
        return PolicyResult(Decision.CONFIRM, "Running untrusted code always requires fresh confirmation.")

    if key in policy.grants:
        return PolicyResult(Decision.ALLOW, "An explicit grant exists for this exact capability.")

    # A narrow convenience case: reject optional cookies, never accept all.
    if (
        action.capability == "browser.cookie_consent"
        and action.operation == "reject_optional"
        and not action.changes_external_state
    ):
        return PolicyResult(Decision.ALLOW, "Rejecting optional cookies is a narrow low-risk action.")

    if action.changes_external_state:
        return PolicyResult(Decision.CONFIRM, "This action changes state and has no exact grant.")

    return PolicyResult(Decision.DENY, "No explicit permission exists; learned habits cannot grant access.")

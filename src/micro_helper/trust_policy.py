"""Deterministic permission gate for Micro Helper tool actions.

Learning may suggest preferences, but it never creates grants. Callers must
supply an explicit, revocable grant for the exact capability being requested.
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

    if key in policy.denied:
        return PolicyResult(Decision.DENY, "This exact action is explicitly denied.")

    if action.financial:
        return PolicyResult(Decision.CONFIRM, "Financial actions always require fresh confirmation.")
    if action.destructive:
        return PolicyResult(Decision.CONFIRM, "Destructive actions always require fresh confirmation.")
    if action.accesses_sensitive_data:
        return PolicyResult(Decision.CONFIRM, "Sensitive data access requires fresh confirmation.")

    if key in policy.grants:
        return PolicyResult(Decision.ALLOW, "An explicit grant exists for this exact capability.")

    # A narrow convenience case: dismissing a cookie banner is only allowed
    # when the operation means rejecting optional cookies, never accepting all.
    if (
        action.capability == "browser.cookie_consent"
        and action.operation == "reject_optional"
        and not action.changes_external_state
    ):
        return PolicyResult(Decision.ALLOW, "Rejecting optional cookies is a narrow low-risk action.")

    if action.changes_external_state:
        return PolicyResult(Decision.CONFIRM, "This action changes state and has no exact grant.")

    return PolicyResult(Decision.DENY, "No explicit permission exists; learned habits cannot grant access.")

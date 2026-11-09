"""Guard the Adaptive Trust Engine route map against newly added REST mutations.

Every local /v1 state-changing route must either resolve to a deterministic
trust-policy action or be explicitly listed as using a separate gate.
"""
import re

from micro_helper.api import (
    CHAT_ACTION,
    REST_POLICY,
    app,
    _resolve_rest_action,
)
from micro_helper.trust_policy import permission_key


SEPARATE_GATES = {
    # Issues a one-time token only after resolving and validating the requested
    # target action through the same allowlist.
    ("POST", "/v1/actions/confirm"),
    # Uses the dedicated capability/tool confirmation flow instead of REST
    # mutation confirmation.
    ("POST", "/v1/tools/{tool_id}/confirm"),
    ("POST", "/v1/tools/{tool_id}/execute"),
}

PLACEHOLDER_VALUES = {
    "memory_id": "1",
    "preference_id": "1",
    "task_id": "sample-task",
    "plan_id": "sample-plan",
    "tool_id": "memory.list",
}


def sample_path(route_path: str) -> str:
    return re.sub(
        r"\{([^{}]+)\}",
        lambda match: PLACEHOLDER_VALUES[match.group(1)],
        route_path,
    )


def test_every_state_changing_local_rest_route_has_an_explicit_policy_gate():
    uncovered = []

    for route in app.routes:
        route_path = getattr(route, "path", "")
        if not route_path.startswith("/v1/"):
            continue

        methods = getattr(route, "methods", set()) or set()
        for method in sorted(methods & {"POST", "PUT", "PATCH", "DELETE"}):
            if (method, route_path) in SEPARATE_GATES:
                continue

            resolved = _resolve_rest_action(method, sample_path(route_path))
            if resolved is None:
                uncovered.append(f"{method} {route_path}")

    assert not uncovered, (
        "New state-changing REST route(s) lack an explicit Adaptive Trust "
        "Engine mapping or documented separate gate: " + ", ".join(uncovered)
    )


def test_chat_is_the_only_builtin_allow_grant():
    assert REST_POLICY.grants == frozenset({permission_key(CHAT_ACTION)})
    assert CHAT_ACTION.capability == "conversation"
    assert CHAT_ACTION.operation == "append"
    resolved = _resolve_rest_action("POST", "/v1/chat")
    assert resolved is not None
    assert resolved[0] == "rest:POST:/v1/chat"

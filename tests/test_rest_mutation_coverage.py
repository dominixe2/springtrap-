"""Guard every state-changing REST route at both mapping and handler level.

A route is not protected merely because an action exists in the policy map:
its endpoint must actually invoke the shared authorization gate, or implement
one of the narrowly documented separate confirmation gates.
"""
import re

from micro_helper.api import (
    CHAT_ACTION,
    REST_POLICY,
    app,
    _resolve_rest_action,
)
from micro_helper.trust_policy import permission_key


SEPARATE_GATE_CALLS = {
    # First-run setup is one-time, strong-password and exact same-origin only.
    ("POST", "/v1/auth/setup"): {
        "_is_same_origin_auth_request", "_password_digest", "database", "_issue_local_session",
    },
    # Login is same-origin, rate-limited, constant-time verified and issues a short-lived session.
    ("POST", "/v1/auth/login"): {
        "_is_same_origin_auth_request", "_auth_login_blocked", "_password_digest",
        "compare_digest", "_issue_local_session",
    },
    # Logout requires the exact same origin and revokes the server-side session.
    ("POST", "/v1/auth/logout"): {
        "_is_same_origin_auth_request", "database", "delete_cookie",
    },
    # Issues a one-time token only after resolving and evaluating the target action.
    ("POST", "/v1/actions/confirm"): {
        "_resolve_rest_action", "_normalize_rest_arguments", "evaluate_action",
        "REST_POLICY", "_record_tool_audit", "database",
    },
    # Tool confirmation validates the allowlisted tool and policy before issuing.
    ("POST", "/v1/tools/{tool_id}/confirm"): {
        "TOOL_ACTIONS", "_normalize_tool_arguments", "evaluate_action",
        "TOOL_POLICY", "_record_tool_audit", "database",
    },
    # Tool execution re-evaluates policy and consumes a matching one-time token.
    ("POST", "/v1/tools/{tool_id}/execute"): {
        "TOOL_ACTIONS", "_normalize_tool_arguments", "evaluate_action",
        "TOOL_POLICY", "_consume_tool_confirmation",
    },
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


def endpoint_names(endpoint) -> set[str]:
    code = getattr(endpoint, "__code__", None)
    return set(code.co_names) if code is not None else set()


def route_gate_errors(routes) -> list[str]:
    """Return actionable failures for unprotected state-changing local routes."""
    uncovered = []

    for route in routes:
        route_path = getattr(route, "path", "")
        if not route_path.startswith("/v1/"):
            continue

        methods = getattr(route, "methods", set()) or set()
        for method in sorted(methods & {"POST", "PUT", "PATCH", "DELETE"}):
            key = (method, route_path)
            names = endpoint_names(route.endpoint)

            if key in SEPARATE_GATE_CALLS:
                missing = SEPARATE_GATE_CALLS[key] - names
                if missing:
                    uncovered.append(
                        f"{method} {route_path} separate gate missing calls: "
                        + ", ".join(sorted(missing))
                    )
                continue

            resolved = _resolve_rest_action(method, sample_path(route_path))
            if resolved is None:
                uncovered.append(f"{method} {route_path} has no policy action")
            if "_authorize_rest_mutation" not in names:
                uncovered.append(
                    f"{method} {route_path} does not call _authorize_rest_mutation"
                )

    return uncovered


def test_every_state_changing_local_rest_route_has_an_explicit_policy_gate():
    uncovered = route_gate_errors(app.routes)
    assert not uncovered, (
        "State-changing local REST route(s) are not fully protected: "
        + "; ".join(uncovered)
    )


def test_chat_is_the_only_builtin_allow_grant():
    assert REST_POLICY.grants == frozenset({permission_key(CHAT_ACTION)})
    assert CHAT_ACTION.capability == "conversation"
    assert CHAT_ACTION.operation == "append"
    resolved = _resolve_rest_action("POST", "/v1/chat")
    assert resolved is not None
    assert resolved[0] == "rest:POST:/v1/chat"


def test_route_gate_checker_detects_an_unprotected_handler():
    from types import SimpleNamespace

    def unprotected_endpoint():
        return {"ok": True}

    route = SimpleNamespace(
        path="/v1/test-unprotected",
        methods={"POST"},
        endpoint=unprotected_endpoint,
    )

    errors = route_gate_errors([route])
    assert any("has no policy action" in error for error in errors)
    assert any("does not call _authorize_rest_mutation" in error for error in errors)
